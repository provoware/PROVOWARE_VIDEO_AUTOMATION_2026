#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from toolchain_common import ROOT, load_contract, verify_wheelhouse
from toolchain import environment_path, environment_ready


def marker(ok: bool) -> str:
    return "✓" if ok else "✕"


def executable(path: Path) -> bool:
    return path.is_file() and not path.is_symlink() and os.access(path, os.X_OK)


def command_version(command: str) -> tuple[bool, str]:
    path = shutil.which(command)
    if not path:
        return False, "nicht gefunden"
    completed = subprocess.run([path, "-version"], text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
    first = completed.stdout.splitlines()[0] if completed.stdout else path
    return completed.returncode == 0, first


def environment_versions(python: Path, names: list[str]) -> tuple[bool, dict[str, str] | str]:
    if not executable(python):
        return False, "Umgebung fehlt"
    code = (
        "import importlib.metadata,json;"
        f"names={names!r};"
        "print(json.dumps({n:importlib.metadata.version(n) for n in names},sort_keys=True))"
    )
    completed = subprocess.run([str(python), "-c", code], text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
    if completed.returncode:
        return False, completed.stdout[-1000:]
    try:
        return True, json.loads(completed.stdout.splitlines()[-1])
    except (json.JSONDecodeError, IndexError):
        return False, "Versionsausgabe ungültig"


def collect() -> dict[str, Any]:
    contract = load_contract()
    paths = contract["paths"]
    wheelhouse = ROOT / paths["wheelhouse"]
    errors = verify_wheelhouse(wheelhouse, contract, scope="runtime")
    python = environment_path(contract, "runtime") / "bin" / "python"
    expected = sorted(contract["packages"]["runtime"])
    try:
        environment_ready(contract, "runtime")
        env_ok, versions = environment_versions(python, expected)
    except RuntimeError as exc:
        env_ok, versions = False, str(exc)
    ffmpeg_ok, ffmpeg = command_version("ffmpeg")
    ffprobe_ok, ffprobe = command_version("ffprobe")
    disk = shutil.disk_usage(ROOT)
    scripts = {name: executable(ROOT / name) for name in ("videobatch.sh", "start.sh", "setup.sh", "test.sh", "quality.sh", "verify_release.sh")}
    root_writable = os.access(ROOT, os.W_OK | os.X_OK)
    return {
        "build": contract["release_target"],
        "project": {
            "path": str(ROOT),
            "complete": all((ROOT / name).is_file() for name in ("VERSION.json", "TOOLCHAIN_CONTRACT.json", "requirements-toolchain.lock")),
            "writable": root_writable,
            "launchers": scripts,
        },
        "system": {
            "python": sys.version.split()[0],
            "ffmpeg": {"ok": ffmpeg_ok, "value": ffmpeg},
            "ffprobe": {"ok": ffprobe_ok, "value": ffprobe},
            "free_gib": round(disk.free / 1024**3, 2),
        },
        "wheelhouse": {
            "ok": not errors,
            "wheel_count": len(list(wheelhouse.glob("*.whl"))) if wheelhouse.is_dir() else 0,
            "errors": errors,
        },
        "environment": {"ok": env_ok, "python": str(python), "versions": versions},
    }


def print_human(report: dict[str, Any], *, brief: bool) -> int:
    project = report["project"]
    system = report["system"]
    wheelhouse = report["wheelhouse"]
    environment = report["environment"]
    launchers_ok = all(project["launchers"].values())
    rows = [
        (project["complete"], "Projektstruktur", "vollständig" if project["complete"] else "Pflichtdateien fehlen"),
        (project["writable"], "Projektordner", "beschreibbar" if project["writable"] else "nicht beschreibbar"),
        (launchers_ok, "Startdateien", "ausführbar" if launchers_ok else "mindestens eine Datei fehlt oder ist nicht ausführbar"),
        (system["ffmpeg"]["ok"], "FFmpeg", system["ffmpeg"]["value"]),
        (system["ffprobe"]["ok"], "FFprobe", system["ffprobe"]["value"]),
        (system["free_gib"] >= 2, "Freier Speicher", f"{system['free_gib']} GiB"),
        (wheelhouse["ok"], "Offline-Paketbasis", f"{wheelhouse['wheel_count']} Wheels" if wheelhouse["ok"] else "automatisch reparierbar"),
        (environment["ok"], "Laufzeitumgebung", "startbereit" if environment["ok"] else "wird beim Start automatisch aufgebaut"),
    ]
    print(f"\nVIDEOBATCH-DIAGNOSE · {report['build']}")
    print(f"Projekt: {project['path']}\n")
    for ok, title, detail in rows:
        print(f"{marker(ok)} {title:<24} {detail}")
    if not brief and wheelhouse["errors"]:
        print("\nErkannte Paketbasis-Konflikte:")
        for error in wheelhouse["errors"][:8]:
            print(f"  • {error}")
    ready = all(ok for ok, _, _ in rows)
    print("\n" + ("✓ System ist startbereit." if ready else "⟳ Nichtkritische Konflikte werden beim nächsten Start automatisch repariert."))
    if not ready:
        print("  Vollautomatischer Start: ./videobatch.sh")
        print("  Reiner Offlineversuch:  ./videobatch.sh setup --offline-only")
    return 0 if ready else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Verständliche VideoBatch-Systemdiagnose")
    parser.add_argument("--brief", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    report = collect()
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    return print_human(report, brief=args.brief)


if __name__ == "__main__":
    raise SystemExit(main())
