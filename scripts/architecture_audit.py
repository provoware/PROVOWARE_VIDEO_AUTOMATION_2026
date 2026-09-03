#!/usr/bin/env python3
from __future__ import annotations

import ast
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src" / "videobatch_fast"
MAX_LINES = 700


def audit_source_tree(src: Path) -> dict[str, object]:
    findings: list[str] = []
    modules = 0
    functions = 0
    classes = 0
    max_file = ("", 0)

    try:
        paths = sorted(src.glob("*.py"))
    except OSError as exc:
        return {
            "schema_version": 2,
            "modules": 0,
            "functions": 0,
            "classes": 0,
            "max_file": {"name": "", "lines": 0},
            "line_limit": MAX_LINES,
            "findings": [f"Quellordner nicht lesbar: {type(exc).__name__}: {exc}"],
        }

    for path in paths:
        modules += 1
        try:
            source = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            findings.append(f"{path.name}: nicht lesbar: {type(exc).__name__}: {exc}")
            continue

        lines = len(source.splitlines())
        if lines > max_file[1]:
            max_file = (path.name, lines)
        if lines > MAX_LINES:
            findings.append(f"{path.name}: {lines} Zeilen > {MAX_LINES}")

        try:
            tree = ast.parse(source, filename=str(path))
        except SyntaxError as exc:
            location = f"Zeile {exc.lineno or '?'}"
            findings.append(f"{path.name}: Syntaxfehler · {location}: {exc.msg}")
            continue

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                functions += 1
            elif isinstance(node, ast.ClassDef):
                classes += 1
            elif isinstance(node, ast.Call):
                for keyword in node.keywords:
                    if (
                        keyword.arg == "shell"
                        and isinstance(keyword.value, ast.Constant)
                        and keyword.value.value is True
                    ):
                        findings.append(f"{path.name}:{node.lineno}: shell=True")

    return {
        "schema_version": 2,
        "modules": modules,
        "functions": functions,
        "classes": classes,
        "max_file": {"name": max_file[0], "lines": max_file[1]},
        "line_limit": MAX_LINES,
        "findings": findings,
    }


def _write_report(payload: dict[str, object]) -> None:
    diagnostics = Path(os.environ.get("VIDEOBATCH_DIAGNOSTICS_DIR", ROOT / "diagnostics"))
    try:
        diagnostics.mkdir(parents=True, exist_ok=True)
        (diagnostics / "architecture_audit_latest.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    except OSError as exc:
        print(
            f"WARNUNG: Architekturbericht konnte nicht gespeichert werden: {type(exc).__name__}: {exc}",
            file=sys.stderr,
        )


def main() -> int:
    payload = audit_source_tree(SRC)
    _write_report(payload)
    findings = list(payload["findings"])
    max_file = payload["max_file"]
    print(
        "ARCHITEKTURPRÜFUNG: "
        f"{payload['modules']} Module · {payload['functions']} Funktionen · {payload['classes']} Klassen"
    )
    print(f"Größte Datei: {max_file['name']} · {max_file['lines']} Zeilen")
    print(f"Befunde: {len(findings)}")
    for item in findings:
        print(f"✕ {item}")
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
