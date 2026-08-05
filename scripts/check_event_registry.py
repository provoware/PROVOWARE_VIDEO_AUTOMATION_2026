#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import importlib
import json
import os
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE_ROOT = ROOT / "src" / "videobatch_fast"
DEFAULT_CONTRACT_TEST = ROOT / "tests" / "test_event_registry.py"


@dataclass(frozen=True, slots=True)
class Finding:
    code: str
    path: str
    line: int
    message: str


@dataclass(frozen=True, slots=True)
class Emission:
    name: str
    mode: str
    payload_type: str
    path: str
    line: int


def _attribute_chain(node: ast.AST) -> str:
    parts: list[str] = []
    current = node
    while isinstance(current, ast.Attribute):
        parts.append(current.attr)
        current = current.value
    if isinstance(current, ast.Name):
        parts.append(current.id)
    return ".".join(reversed(parts))


def _literal_string(node: ast.AST | None) -> str:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return ""


def _keyword(call: ast.Call, name: str) -> ast.AST | None:
    return next((item.value for item in call.keywords if item.arg == name), None)


def _payload_call_name(node: ast.AST | None) -> str:
    if isinstance(node, ast.Call):
        return _attribute_chain(node.func).rsplit(".", 1)[-1]
    return ""


def _event_emission(call: ast.Call, *, path: Path, relative: str) -> Emission | None:
    chain = _attribute_chain(call.func)
    sink = chain.rsplit(".", 1)[-1]
    name_node: ast.AST | None = None
    payload_node: ast.AST | None = None
    mode = ""

    if sink == "AppEvent":
        name_node = _keyword(call, "name") or (call.args[0] if call.args else None)
        payload_node = _keyword(call, "payload") or (call.args[1] if len(call.args) > 1 else None)
        mode = "typed" if _payload_call_name(payload_node).endswith("Payload") else "mapping"
    elif sink == "_publish_typed":
        name_node = call.args[0] if call.args else None
        payload_node = call.args[1] if len(call.args) > 1 else None
        mode = "typed"
    elif sink == "_publish_mapping":
        name_node = call.args[0] if call.args else None
        mode = "mapping"
    elif sink == "put_legacy":
        name_node = call.args[0] if call.args else None
        mode = "legacy"
    elif sink == "emit" and path.name == "runner_process.py":
        name_node = call.args[0] if call.args else None
        mode = "mapping"
    else:
        return None

    name = _literal_string(name_node)
    if not name:
        return None
    payload_type = _payload_call_name(payload_node)
    return Emission(name, mode, payload_type, relative, call.lineno)


def scan_emissions(source_root: Path) -> tuple[list[Emission], list[Finding]]:
    emissions: list[Emission] = []
    findings: list[Finding] = []
    for path in sorted(source_root.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        relative = path.relative_to(source_root).as_posix()
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=relative)
        except (OSError, UnicodeError, SyntaxError) as exc:
            findings.append(Finding("EVENT_REGISTRY_SCAN_FAILED", relative, 0, str(exc)))
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                emission = _event_emission(node, path=path, relative=relative)
                if emission is not None:
                    emissions.append(emission)
    return emissions, findings


def scan_handler_methods(source_root: Path) -> set[str]:
    methods: set[str] = set()
    for path in sorted(source_root.glob("ui*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=path.name)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                methods.add(node.name)
    return methods


def contract_event_names(path: Path) -> frozenset[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in tree.body:
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        if not any(isinstance(target, ast.Name) and target.id == "CONTRACT_EVENT_NAMES" for target in targets):
            continue
        value = node.value
        if isinstance(value, ast.Call) and _attribute_chain(value.func).endswith("frozenset") and value.args:
            value = value.args[0]
        if isinstance(value, (ast.Set, ast.List, ast.Tuple)):
            names = {_literal_string(item) for item in value.elts}
            if "" not in names:
                return frozenset(names)
    raise ValueError("CONTRACT_EVENT_NAMES muss als ausdrückliche Literalmenge definiert sein.")


def _type_path(payload_type: type[object]) -> str:
    return f"{payload_type.__module__}.{payload_type.__qualname__}"


def inspect_contract(source_root: Path, contract_test: Path) -> tuple[list[Finding], list[Emission]]:
    source_parent = source_root.parent
    if str(source_parent) not in sys.path:
        sys.path.insert(0, str(source_parent))

    from videobatch_fast.app_events import NOISY_EVENT_NAMES, TERMINAL_EVENT_NAMES, TypedEventPayload
    from videobatch_fast.event_registry import EVENT_REGISTRY, noisy_event_names, terminal_event_names

    emissions, findings = scan_emissions(source_root)
    registered = frozenset(EVENT_REGISTRY)

    for emission in emissions:
        spec = EVENT_REGISTRY.get(emission.name)
        if spec is None:
            findings.append(
                Finding(
                    "EVENT_UNREGISTERED",
                    emission.path,
                    emission.line,
                    f"Erzeugtes Ereignis {emission.name!r} fehlt im zentralen Register.",
                )
            )
            continue
        if emission.mode not in spec.modes:
            findings.append(
                Finding(
                    "EVENT_PRODUCER_MODE_MISMATCH",
                    emission.path,
                    emission.line,
                    f"{emission.name!r} wird als {emission.mode} erzeugt; registriert: {sorted(spec.modes)}.",
                )
            )
        if emission.mode == "typed":
            expected = spec.payload_type.rsplit(".", 1)[-1]
            if emission.payload_type != expected:
                findings.append(
                    Finding(
                        "EVENT_TYPED_PAYLOAD_MISMATCH",
                        emission.path,
                        emission.line,
                        f"{emission.name!r} verwendet {emission.payload_type or '-'} statt {expected}.",
                    )
                )

    handlers = scan_handler_methods(source_root)
    for spec in EVENT_REGISTRY.values():
        if spec.handler not in handlers:
            findings.append(
                Finding(
                    "EVENT_HANDLER_MISSING",
                    "event_registry.py",
                    0,
                    f"Handler {spec.handler!r} für {spec.name!r} ist nicht definiert.",
                )
            )
        try:
            module_name, _, attribute = spec.payload_type.rpartition(".")
            payload_type = getattr(importlib.import_module(module_name), attribute)
        except (ImportError, AttributeError) as exc:
            findings.append(
                Finding(
                    "EVENT_PAYLOAD_TYPE_UNRESOLVED",
                    "event_registry.py",
                    0,
                    f"Payloadtyp {spec.payload_type!r} für {spec.name!r} ist nicht auflösbar: {exc}",
                )
            )
            continue
        if not isinstance(payload_type, type):
            findings.append(
                Finding(
                    "EVENT_PAYLOAD_TYPE_INVALID",
                    "event_registry.py",
                    0,
                    f"Payloadtyp {spec.payload_type!r} ist keine Klasse.",
                )
            )
            continue
        if "typed" in spec.modes:
            if not issubclass(payload_type, TypedEventPayload):
                findings.append(
                    Finding(
                        "EVENT_TYPED_PAYLOAD_BASE",
                        "event_registry.py",
                        0,
                        f"{spec.payload_type!r} erbt nicht von TypedEventPayload.",
                    )
                )
            field_names = tuple(getattr(payload_type, "_field_names", ()))
            if field_names != spec.required_fields:
                findings.append(
                    Finding(
                        "EVENT_TYPED_FIELDS_MISMATCH",
                        "event_registry.py",
                        0,
                        f"Pflichtfelder für {spec.name!r} weichen ab: {field_names!r} != {spec.required_fields!r}.",
                    )
                )
        elif _type_path(payload_type) != "builtins.dict":
            findings.append(
                Finding(
                    "EVENT_MAPPING_PAYLOAD_TYPE",
                    "event_registry.py",
                    0,
                    f"Nicht typisiertes Ereignis {spec.name!r} muss builtins.dict verwenden.",
                )
            )

    if NOISY_EVENT_NAMES != noisy_event_names():
        findings.append(
            Finding("EVENT_NOISY_CLASSIFICATION", "app_events.py", 0, "Noisy-Klassifizierung weicht vom Register ab.")
        )
    if TERMINAL_EVENT_NAMES != terminal_event_names():
        findings.append(
            Finding("EVENT_TERMINAL_CLASSIFICATION", "app_events.py", 0, "Terminalklassifizierung weicht vom Register ab.")
        )

    try:
        tested = contract_event_names(contract_test)
    except (OSError, UnicodeError, SyntaxError, ValueError) as exc:
        findings.append(Finding("EVENT_CONTRACT_TEST_INVALID", str(contract_test), 0, str(exc)))
    else:
        missing_tests = registered - tested
        extra_tests = tested - registered
        if missing_tests:
            findings.append(
                Finding(
                    "EVENT_CONTRACT_TEST_MISSING",
                    str(contract_test),
                    0,
                    f"Vertragstests fehlen für: {', '.join(sorted(missing_tests))}.",
                )
            )
        if extra_tests:
            findings.append(
                Finding(
                    "EVENT_CONTRACT_TEST_UNKNOWN",
                    str(contract_test),
                    0,
                    f"Vertragstests nennen unbekannte Ereignisse: {', '.join(sorted(extra_tests))}.",
                )
            )

    return findings, emissions


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify event registry, producers, handlers and contract tests.")
    parser.add_argument("--source-root", type=Path, default=DEFAULT_SOURCE_ROOT)
    parser.add_argument("--contract-test", type=Path, default=DEFAULT_CONTRACT_TEST)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    source_root = args.source_root.expanduser().resolve()
    contract_test = args.contract_test.expanduser().resolve()
    findings, emissions = inspect_contract(source_root, contract_test)
    report = {
        "schema_version": 1,
        "status": "pass" if not findings else "fail",
        "source_root": str(source_root),
        "contract_test": str(contract_test),
        "emissions": [asdict(item) for item in emissions],
        "findings": [asdict(item) for item in findings],
    }
    output = args.output
    if output is None:
        diagnostics = Path(os.environ.get("VIDEOBATCH_DIAGNOSTICS_DIR", ROOT / "diagnostics"))
        output = diagnostics / "event_registry_latest.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"EREIGNISREGISTER: {len(findings)} Befund(e) · "
        f"{len({item.name for item in emissions})} erzeugte Kennung(en) geprüft"
    )
    for item in findings:
        print(f"✕ {item.code} · {item.path}:{item.line} · {item.message}")
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
