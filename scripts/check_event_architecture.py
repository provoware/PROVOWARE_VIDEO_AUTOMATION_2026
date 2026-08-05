#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import os
import re
from dataclasses import asdict, dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE_ROOT = ROOT / "src" / "videobatch_fast"
_EVENT_NAME_RE = re.compile(r"^[a-z][a-z0-9_.-]{1,79}$")
_ALLOWED_LEGACY_FACTORY = "event_buffer.py"


@dataclass(frozen=True, slots=True)
class Finding:
    code: str
    path: str
    line: int
    message: str


def _attribute_chain(node: ast.AST) -> str:
    parts: list[str] = []
    current = node
    while isinstance(current, ast.Attribute):
        parts.append(current.attr)
        current = current.value
    if isinstance(current, ast.Name):
        parts.append(current.id)
    return ".".join(reversed(parts))


def _looks_like_event_name(node: ast.AST) -> bool:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return bool(_EVENT_NAME_RE.fullmatch(node.value))
    return isinstance(node, ast.Name) and node.id in {"event_name", "name"}


def _looks_like_payload(node: ast.AST) -> bool:
    if isinstance(node, ast.Dict):
        return True
    return isinstance(node, ast.Name) and node.id in {"payload", "event_payload"}


def _is_direct_event_tuple(call: ast.Call) -> bool:
    if len(call.args) != 1 or not isinstance(call.args[0], ast.Tuple):
        return False
    pair = call.args[0]
    if len(pair.elts) != 2:
        return False
    chain = _attribute_chain(call.func)
    sink = chain.rsplit(".", 1)[-1]
    if sink not in {"put", "_emit"}:
        return False
    event_name, payload = pair.elts
    if sink == "_emit":
        return _looks_like_event_name(event_name) and _looks_like_payload(payload)
    event_target = any(token in chain.lower() for token in ("event", "events", "buffer"))
    return event_target and _looks_like_event_name(event_name) and _looks_like_payload(payload)


def _selection_preview_wiring(call: ast.Call) -> Finding | None:
    chain = _attribute_chain(call.func)
    if chain.rsplit(".", 1)[-1] != "SelectionPreviewController":
        return None
    if not call.args:
        return Finding(
            "ARCH_SELECTION_PREVIEW_CALLBACK_MISSING",
            "",
            call.lineno,
            "SelectionPreviewController benötigt EventBuffer.put als direkten AppEvent-Empfänger.",
        )
    callback = _attribute_chain(call.args[0])
    if callback.endswith(".put_legacy"):
        return Finding(
            "ARCH_SELECTION_PREVIEW_LEGACY_WIRING",
            "",
            call.lineno,
            "SelectionPreviewController darf nicht mehr mit EventBuffer.put_legacy verdrahtet werden.",
        )
    if not callback.endswith(".put"):
        return Finding(
            "ARCH_SELECTION_PREVIEW_CALLBACK_CONTRACT",
            "",
            call.lineno,
            "SelectionPreviewController muss direkt an EventBuffer.put verdrahtet sein.",
        )
    return None


def inspect_file(path: Path, *, display_path: str | None = None) -> list[Finding]:
    relative = display_path or path.name
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=relative)
    findings: list[Finding] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if _is_direct_event_tuple(node):
            findings.append(
                Finding(
                    "ARCH_LEGACY_EVENT_TUPLE",
                    relative,
                    node.lineno,
                    "Direkte (name, payload)-Ereignisse sind verboten; AppEvent oder EventBuffer.put_legacy verwenden.",
                )
            )
        chain = _attribute_chain(node.func)
        if chain.endswith("AppEvent.from_legacy") and path.name != _ALLOWED_LEGACY_FACTORY:
            findings.append(
                Finding(
                    "ARCH_LEGACY_ADAPTER_BYPASS",
                    relative,
                    node.lineno,
                    "AppEvent.from_legacy darf ausschließlich durch EventBuffer.put_legacy aufgerufen werden.",
                )
            )
        if path.name == "runner.py" and chain == "self.callback" and len(node.args) != 1:
            findings.append(
                Finding(
                    "ARCH_RUNNER_CALLBACK_CONTRACT",
                    relative,
                    node.lineno,
                    "BatchRunner-Callbacks müssen genau ein AppEvent erhalten.",
                )
            )
        if path.name == "selection_preview_controller.py":
            if chain == "self._emit" and len(node.args) != 1:
                findings.append(
                    Finding(
                        "ARCH_SELECTION_PREVIEW_EMIT_CONTRACT",
                        relative,
                        node.lineno,
                        "SelectionPreviewController muss genau ein AppEvent an seinen Callback übergeben.",
                    )
                )
            if chain.endswith("put_legacy"):
                findings.append(
                    Finding(
                        "ARCH_SELECTION_PREVIEW_LEGACY_CALL",
                        relative,
                        node.lineno,
                        "SelectionPreviewController darf put_legacy nicht verwenden.",
                    )
                )
        wiring = _selection_preview_wiring(node)
        if wiring is not None:
            findings.append(
                Finding(wiring.code, relative, wiring.line, wiring.message)
            )
    return findings


def inspect_tree(source_root: Path) -> list[Finding]:
    findings: list[Finding] = []
    for path in sorted(source_root.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        relative = path.relative_to(source_root).as_posix()
        try:
            findings.extend(inspect_file(path, display_path=relative))
        except (OSError, UnicodeError, SyntaxError) as exc:
            findings.append(Finding("ARCH_EVENT_SCAN_FAILED", relative, 0, str(exc)))
    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Block uncontrolled legacy UI event tuples.")
    parser.add_argument("--source-root", type=Path, default=DEFAULT_SOURCE_ROOT)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    source_root = args.source_root.expanduser().resolve()
    findings = inspect_tree(source_root)
    report = {
        "schema_version": 2,
        "status": "pass" if not findings else "fail",
        "source_root": str(source_root),
        "allowed_legacy_adapter": "EventBuffer.put_legacy",
        "migrated_producers": ["BatchRunner", "SelectionPreviewController"],
        "findings": [asdict(item) for item in findings],
    }
    output = args.output
    if output is None:
        diagnostics = Path(os.environ.get("VIDEOBATCH_DIAGNOSTICS_DIR", ROOT / "diagnostics"))
        output = diagnostics / "event_architecture_latest.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"EREIGNISARCHITEKTUR: {len(findings)} Befund(e) · Legacy-Grenze EventBuffer.put_legacy")
    for item in findings:
        print(f"✕ {item.code} · {item.path}:{item.line} · {item.message}")
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
