#!/usr/bin/env python3
from __future__ import annotations

import ast
import json
import math
import os
import re
from dataclasses import dataclass, asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIRS = (ROOT / "src", ROOT / "scripts", ROOT / "tests")
REGISTRY = ROOT / "registries" / "CODE_QUALITY_REGISTRY.json"


@dataclass(frozen=True, slots=True)
class Finding:
    severity: str
    code: str
    path: str
    line: int
    message: str


def _complexity(node: ast.AST) -> int:
    score = 1
    for item in ast.walk(node):
        if isinstance(item, (ast.If, ast.For, ast.AsyncFor, ast.While, ast.ExceptHandler, ast.With, ast.AsyncWith, ast.IfExp, ast.Assert, ast.comprehension)):
            score += 1
        elif isinstance(item, ast.BoolOp):
            score += max(1, len(item.values) - 1)
        elif isinstance(item, ast.Match):
            score += len(item.cases)
    return score


def _exact_lock(path: Path) -> list[Finding]:
    findings: list[Finding] = []
    if not path.is_file():
        return [Finding("error", "LOCK_MISSING", path.name, 0, "Versionsgesperrte Abhängigkeitsdatei fehlt.")]
    for line_no, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        requirement = line.split(";", 1)[0].strip()
        if "==" not in requirement or any(token in requirement for token in (">=", "<=", "~=", "!=", "<", ">")):
            findings.append(Finding("error", "LOCK_NOT_EXACT", path.name, line_no, "Abhängigkeit ist nicht mit == exakt gesperrt."))
    return findings


def _source_files() -> list[Path]:
    files: list[Path] = []
    for directory in SOURCE_DIRS:
        if directory.exists():
            files.extend(path for path in directory.rglob("*.py") if "__pycache__" not in path.parts)
    return sorted(files)


def main() -> int:
    policy = json.loads(REGISTRY.read_text(encoding="utf-8"))
    py_policy = policy["python"]
    line_limit = int(py_policy["source_line_limit"])
    complexity_limit = int(py_policy["function_complexity_limit"])
    findings: list[Finding] = []
    metrics = {"files": 0, "functions": 0, "classes": 0, "max_lines": 0, "max_complexity": 0}
    forbidden_calls = {"os.system": "SEC_OS_SYSTEM", "tempfile.mktemp": "SEC_MKTEMP"}

    for path in _source_files():
        relative = path.relative_to(ROOT).as_posix()
        source = path.read_text(encoding="utf-8")
        metrics["files"] += 1
        lines = len(source.splitlines())
        metrics["max_lines"] = max(metrics["max_lines"], lines)
        if relative.startswith("src/") and lines > line_limit:
            findings.append(Finding("error", "FILE_TOO_LONG", relative, 1, f"{lines} Zeilen überschreiten das Limit {line_limit}."))
        try:
            tree = ast.parse(source, filename=relative)
        except SyntaxError as exc:
            findings.append(Finding("error", "SYNTAX", relative, exc.lineno or 0, str(exc)))
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                metrics["classes"] += 1
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                metrics["functions"] += 1
                value = _complexity(node)
                metrics["max_complexity"] = max(metrics["max_complexity"], value)
                if value > complexity_limit:
                    findings.append(Finding("error", "COMPLEXITY", relative, node.lineno, f"{node.name} besitzt Komplexität {value}; erlaubt sind {complexity_limit}."))
            if isinstance(node, ast.Call):
                for keyword in node.keywords:
                    if keyword.arg == "shell" and isinstance(keyword.value, ast.Constant) and keyword.value.value is True:
                        findings.append(Finding("error", "SEC_SHELL_TRUE", relative, node.lineno, "shell=True ist verboten."))
                name = ""
                if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
                    name = f"{node.func.value.id}.{node.func.attr}"
                if name in forbidden_calls:
                    findings.append(Finding("error", forbidden_calls[name], relative, node.lineno, f"{name} ist verboten."))
                if isinstance(node.func, ast.Name) and node.func.id in {"eval", "exec"}:
                    allowed_exec = relative == "src/videobatch_fast/plugin_host.py" and node.func.id == "exec"
                    if not allowed_exec:
                        findings.append(Finding("error", "SEC_DYNAMIC_CODE", relative, node.lineno, f"{node.func.id} ist außerhalb des isolierten Plugin-Hosts verboten."))
        if re.search(r"-----BEGIN (?:OPENSSH |EC |RSA )?PRIVATE KEY-----", source):
            findings.append(Finding("error", "PRIVATE_KEY", relative, 1, "Privates Schlüsselmaterial im Quelltext erkannt."))

    findings.extend(_exact_lock(ROOT / "requirements.lock"))
    findings.extend(_exact_lock(ROOT / "requirements-quality.lock"))
    errors = [item for item in findings if item.severity == "error"]
    report = {
        "schema_version": 1,
        "contract_version": policy["contract_version"],
        "status": "pass" if not errors else "fail",
        "metrics": metrics,
        "findings": [asdict(item) for item in findings],
    }
    output_dir = Path(os.environ.get("VIDEOBATCH_DIAGNOSTICS_DIR", ROOT / "diagnostics"))
    output_dir.mkdir(parents=True, exist_ok=True)
    output = output_dir / "internal_quality_latest.json"
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"INTERNE CODEQUALITÄT: {metrics['files']} Dateien · {metrics['functions']} Funktionen · max. Komplexität {metrics['max_complexity']} · Befunde {len(errors)}")
    for item in errors:
        print(f"✕ {item.code} · {item.path}:{item.line} · {item.message}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
