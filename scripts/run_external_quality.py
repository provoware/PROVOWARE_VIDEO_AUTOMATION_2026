#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.metadata
import json
import os
import shutil
import subprocess
import sys
import tempfile
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
    "bandit": [
        "bandit",
        "-q",
        "-r",
        "src/videobatch_fast",
        "-c",
        "pyproject.toml",
    ],
    "pip-audit": [
        "pip-audit",
        "--no-deps",
        "--disable-pip",
        "--progress-spinner",
        "off",
        "-r",
        "requirements.lock",
    ],
}

_OFFLINE_GUARD = '''from __future__ import annotations

import errno
import socket


def _blocked(*_args, **_kwargs):
    raise OSError(errno.ENETUNREACH, "OFFLINE_QUALITY_NETWORK_BLOCKED")


class _OfflineSocket(socket.socket):
    def connect(self, *_args, **_kwargs):
        return _blocked()

    def connect_ex(self, *_args, **_kwargs):
        return errno.ENETUNREACH


socket.socket = _OfflineSocket
socket.create_connection = _blocked
'''


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


def _command(name: str) -> list[str]:
    command = list(COMMANDS[name])
    if name == "pip-audit":
        cache_dir = os.environ.get("VIDEOBATCH_PIP_AUDIT_CACHE", "").strip()
        if not cache_dir:
            raise RuntimeError(
                "VIDEOBATCH_PIP_AUDIT_CACHE fehlt; ein Offline-Audit ohne "
                "vorbereiteten Advisory-Cache ist nicht zulässig."
            )
        command[1:1] = ["--cache-dir", cache_dir]
    return command


def _tool_preflight(name: str, expected: dict[str, str]) -> str:
    executable = shutil.which(COMMANDS[name][0])
    if not executable:
        return "Werkzeug ist nicht installiert."
    expected_version = expected.get(name, "")
    actual_version = _installed_version(name)
    if expected_version and actual_version != expected_version:
        return (
            f"Version stimmt nicht: erwartet {expected_version}, "
            f"installiert {actual_version or 'unbekannt'}."
        )
    return ""


def _run_tool(
    name: str,
    command: list[str],
    *,
    offline_guard: Path | None,
) -> dict[str, object]:
    python_path = [str(ROOT / "src")]
    if offline_guard is not None:
        python_path.insert(0, str(offline_guard))
    existing_python_path = os.environ.get("PYTHONPATH", "").strip()
    if existing_python_path:
        python_path.append(existing_python_path)
    completed = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        capture_output=True,
        errors="replace",
        env={**os.environ, "PYTHONPATH": os.pathsep.join(python_path)},
        check=False,
    )
    return {
        "tool": name,
        "status": "pass" if completed.returncode == 0 else "fail",
        "returncode": completed.returncode,
        "version": _installed_version(name),
        "command": command,
        "offline_guard": offline_guard is not None,
        "stdout": completed.stdout[-12_000:],
        "stderr": completed.stderr[-12_000:],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("required", "auto"), default="required")
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args()
    expected = _locked_versions()
    results: list[dict[str, object]] = []
    failed = False
    with tempfile.TemporaryDirectory(prefix="videobatch-quality-offline-") as guard:
        offline_guard = Path(guard) if args.offline else None
        if offline_guard is not None:
            (offline_guard / "sitecustomize.py").write_text(
                _OFFLINE_GUARD,
                encoding="utf-8",
            )
        for name in COMMANDS:
            error = _tool_preflight(name, expected)
            if error:
                failed = failed or args.mode == "required"
                results.append({"tool": name, "status": "blocked", "message": error})
                print(f"{'✕' if args.mode == 'required' else '!'} {name}: {error}")
                continue
            try:
                command = _command(name)
            except RuntimeError as exc:
                failed = failed or args.mode == "required"
                results.append(
                    {"tool": name, "status": "blocked", "message": str(exc)}
                )
                print(f"{'✕' if args.mode == 'required' else '!'} {name}: {exc}")
                continue
            result = _run_tool(name, command, offline_guard=offline_guard)
            failed = failed or result["status"] != "pass"
            results.append(result)
            print(f"{'✓' if result['status'] == 'pass' else '✕'} {name}: {result['status']}")
    output_dir = Path(
        os.environ.get("VIDEOBATCH_DIAGNOSTICS_DIR", ROOT / "diagnostics")
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    report = {
        "schema_version": 3,
        "mode": args.mode,
        "offline": args.offline,
        "python": sys.version,
        "interpreter": sys.executable,
        "results": results,
    }
    (output_dir / "external_quality_latest.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
