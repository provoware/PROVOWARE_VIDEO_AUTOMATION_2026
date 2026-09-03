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


def main() -> int:
    findings = []
    modules = 0
    functions = 0
    classes = 0
    max_file = ("", 0)
    for path in sorted(SRC.glob("*.py")):
        modules += 1
        source = path.read_text(encoding="utf-8")
        lines = len(source.splitlines())
        if lines > max_file[1]:
            max_file = (path.name, lines)
        if lines > MAX_LINES:
            findings.append(f"{path.name}: {lines} Zeilen > {MAX_LINES}")
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                functions += 1
            elif isinstance(node, ast.ClassDef):
                classes += 1
            elif isinstance(node, ast.Call):
                for keyword in node.keywords:
                    if keyword.arg == "shell" and isinstance(keyword.value, ast.Constant) and keyword.value.value is True:
                        findings.append(f"{path.name}:{node.lineno}: shell=True")
    payload = {"schema_version":1,"modules":modules,"functions":functions,"classes":classes,"max_file":{"name":max_file[0],"lines":max_file[1]},"line_limit":MAX_LINES,"findings":findings}
    diagnostics = Path(os.environ.get("VIDEOBATCH_DIAGNOSTICS_DIR", ROOT / "diagnostics"))
    diagnostics.mkdir(parents=True, exist_ok=True)
    (diagnostics / "architecture_audit_latest.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print(f"ARCHITEKTURPRÜFUNG: {modules} Module · {functions} Funktionen · {classes} Klassen")
    print(f"Größte Datei: {max_file[0]} · {max_file[1]} Zeilen")
    print(f"Befunde: {len(findings)}")
    for item in findings:
        print(f"✕ {item}")
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
