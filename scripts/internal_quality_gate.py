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


def _source_line_ceiling(relative: str, py_policy: dict[str, object]) -> tuple[int, bool]:
    default_limit = int(py_policy["source_line_limit"])
    raw = py_policy.get("legacy_source_line_ceilings", {})
    legacy = raw if isinstance(raw, dict) else {}
    if relative not in legacy:
        return default_limit, False
    return int(legacy[relative]), True


def main() -> int:
    policy = json.loads(REGISTRY.read_text(encoding="utf-8"))
    py_policy = policy["python"]
    line_limit = int(py_policy["source_line_limit"])
    complexity_limit = int(py_policy["function_complexity_limit"])
    function_line_target = int(py_policy.get("function_line_target", 30))
    class_method_target = int(py_policy.get("class_method_target", 24))
    raw_ceilings = py_policy.get("legacy_source_line_ceilings", {})
    legacy_line_ceilings = raw_ceilings if isinstance(raw_ceilings, dict) else {}
    findings: list[Finding] = []
    metrics = {
        "files": 0,
        "functions": 0,
        "classes": 0,
        "max_lines": 0,
        "max_complexity": 0,
        "architecture_debt_files": 0,
        "long_functions": 0,
        "large_classes": 0,
        "max_function_lines": 0,
        "max_class_methods": 0,
    }
    forbidden_calls = {"os.system": "SEC_OS_SYSTEM", "tempfile.mktemp": "SEC_MKTEMP"}

    for path in _source_files():
        relative = path.relative_to(ROOT).as_posix()
        source = path.read_text(encoding="utf-8")
        metrics["files"] += 1
        lines = len(source.splitlines())
        metrics["max_lines"] = max(metrics["max_lines"], lines)
        if relative.startswith("src/"):
            allowed_lines, is_legacy = _source_line_ceiling(relative, py_policy)
            if lines > allowed_lines:
                code = "FILE_DEBT_GREW" if is_legacy else "FILE_TOO_LONG"
                findings.append(
                    Finding(
                        "error",
                        code,
                        relative,
                        1,
                        f"{lines} Zeilen überschreiten das erlaubte Ceiling {allowed_lines}.",
                    )
                )
            elif is_legacy and lines < allowed_lines:
                findings.append(
                    Finding(
                        "error",
                        "DEBT_BASELINE_STALE",
                        relative,
                        1,
                        (
                            f"Datei ist auf {lines} Zeilen geschrumpft, "
                            f"Legacy-Ceiling steht noch auf {allowed_lines}; Ceiling absenken."
                        ),
                    )
                )
            elif lines > line_limit:
                metrics["architecture_debt_files"] += 1
        try:
            tree = ast.parse(source, filename=relative)
        except SyntaxError as exc:
            findings.append(Finding("error", "SYNTAX", relative, exc.lineno or 0, str(exc)))
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                metrics["classes"] += 1
                method_count = sum(
                    isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))
                    for child in node.body
                )
                metrics["max_class_methods"] = max(metrics["max_class_methods"], method_count)
                if method_count > class_method_target:
                    metrics["large_classes"] += 1
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                metrics["functions"] += 1
                function_lines = max(
                    1,
                    int(getattr(node, "end_lineno", node.lineno) or node.lineno) - node.lineno + 1,
                )
                metrics["max_function_lines"] = max(metrics["max_function_lines"], function_lines)
                if function_lines > function_line_target:
                    metrics["long_functions"] += 1
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

    for relative, raw_ceiling in sorted(legacy_line_ceilings.items()):
        ceiling = int(raw_ceiling)
        target = ROOT / relative
        if ceiling <= line_limit:
            findings.append(
                Finding(
                    "error",
                    "DEBT_BASELINE_REDUNDANT",
                    relative,
                    0,
                    f"Legacy-Ceiling {ceiling} liegt nicht über dem Standardlimit {line_limit}.",
                )
            )
        if not target.is_file():
            findings.append(
                Finding(
                    "error",
                    "DEBT_BASELINE_ORPHAN",
                    relative,
                    0,
                    "Legacy-Ceiling verweist auf eine nicht vorhandene Datei.",
                )
            )

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
    print(
        "INTERNE CODEQUALITÄT: "
        f"{metrics['files']} Dateien · "
        f"{metrics['functions']} Funktionen · "
        f"Architektur-Altlasten {metrics['architecture_debt_files']} · "
        f"Funktionen >{function_line_target} Zeilen {metrics['long_functions']} · "
        f"Klassen >{class_method_target} Methoden {metrics['large_classes']} · "
        f"max. Komplexität {metrics['max_complexity']} · "
        f"Befunde {len(errors)}"
    )
    for item in errors:
        print(f"✕ {item.code} · {item.path}:{item.line} · {item.message}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
