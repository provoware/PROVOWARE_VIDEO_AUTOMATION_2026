#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.metadata
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / "requirements-quality.lock"

COMMANDS = {
    "ruff": ["ruff", "check", "src", "scripts", "tests"],
    "mypy": [
        "mypy",
        "src/videobatch_fast/naming.py",
        "src/videobatch_fast/archive_service.py",
        "src/videobatch_fast/runner.py",
        "src/videobatch_fast/runner_process.py",
        "src/videobatch_fast/plugin_runtime.py",
        "src/videobatch_fast/os_sandbox.py",
        "src/videobatch_fast/sandbox_seccomp.py",
        "src/videobatch_fast/updates.py",
        "src/videobatch_fast/update_validation.py",
        "src/videobatch_fast/project_state.py",
    ],
    "bandit": ["bandit", "-q", "-r", "src/videobatch_fast", "-c", "pyproject.toml"],
    "pip-audit": ["pip-audit", "--no-deps", "--disable-pip", "-r", "requirements.lock"],
}


def _locked_versions() -> dict[str, str]:
    versions: dict[str, str] = {}
    for raw in LOCK.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        requirement = line.split(";", 1)[0].strip()
        name, version = requirement.split("==", 1)
        versions[name.lower().replace("_", "-")] = version
    return versions


def _installed_version(name: str) -> str:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return ""


def _tool_preflight(name: str, expected: dict[str, str]) -> str:
    executable = shutil.which(COMMANDS[name][0])
    if not executable:
        return "Werkzeug ist nicht installiert."
    expected_version = expected.get(name, "")
    actual_version = _installed_version(name)
    if expected_version and actual_version != expected_version:
        return f"Version stimmt nicht: erwartet {expected_version}, installiert {actual_version or 'unbekannt'}."
    return ""


def _run_tool(name: str, command: list[str]) -> dict[str, object]:
    completed = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        capture_output=True,
        errors="replace",
        env={**os.environ, "PYTHONPATH": str(ROOT / "src")},
        check=False,
    )
    return {
        "tool": name,
        "status": "pass" if completed.returncode == 0 else "fail",
        "returncode": completed.returncode,
        "version": _installed_version(name),
        "stdout": completed.stdout[-12_000:],
        "stderr": completed.stderr[-12_000:],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("required", "auto"), default="required")
    args = parser.parse_args()
    expected = _locked_versions()
    results: list[dict[str, object]] = []
    failed = False
    for name, command in COMMANDS.items():
        error = _tool_preflight(name, expected)
        if error:
            failed = failed or args.mode == "required"
            results.append({"tool": name, "status": "blocked", "message": error})
            print(f"{'✕' if args.mode == 'required' else '!'} {name}: {error}")
            continue
        result = _run_tool(name, command)
        failed = failed or result["status"] != "pass"
        results.append(result)
        print(f"{'✓' if result['status'] == 'pass' else '✕'} {name}: {result['status']}")
    output_dir = Path(os.environ.get("VIDEOBATCH_DIAGNOSTICS_DIR", ROOT / "diagnostics"))
    output_dir.mkdir(parents=True, exist_ok=True)
    report = {
        "schema_version": 2,
        "mode": args.mode,
        "python": sys.version,
        "interpreter": sys.executable,
        "results": results,
    }
    (output_dir / "external_quality_latest.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
