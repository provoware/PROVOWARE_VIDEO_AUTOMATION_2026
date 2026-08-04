#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXCLUDES = {".git", ".venv", ".quality-venv", ".quality-toolchain-backups", "build", "dist", ".pytest_cache", "__pycache__", "diagnostics", "visual_actual"}


def _ignore(_directory: str, names: list[str]) -> set[str]:
    return {name for name in names if name in EXCLUDES or name.endswith((".pyc", ".pyo"))}


def main() -> int:
    parser = argparse.ArgumentParser(description="Führt die visuelle Regression ausschließlich in einer temporären Projektkopie aus.")
    parser.add_argument("--xvfb", default="xvfb-run")
    args = parser.parse_args()
    use_xvfb = bool(shutil.which(args.xvfb))
    if not use_xvfb and not (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")):
        print("VISUELLE REGRESSION BLOCKIERT · weder xvfb-run noch Desktop-Sitzung verfügbar")
        return 2
    with tempfile.TemporaryDirectory(prefix="videobatch_visual_verify_") as tmp:
        workspace = Path(tmp) / "project"
        shutil.copytree(ROOT, workspace, symlinks=True, ignore=_ignore)
        xdg = Path(tmp) / "xdg"
        env = {
            **os.environ,
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONPATH": str(workspace / "src"),
            "XDG_CONFIG_HOME": str(xdg / "config"),
            "XDG_STATE_HOME": str(xdg / "state"),
            "XDG_CACHE_HOME": str(xdg / "cache"),
            "VIDEOBATCH_DIAGNOSTICS_DIR": str(Path(tmp) / "diagnostics"),
        }
        command = (
            [args.xvfb, "-a", "-s", "-screen 0 2560x1440x24", sys.executable, str(workspace / "scripts" / "capture_visual_scenarios.py")]
            if use_xvfb
            else [sys.executable, str(workspace / "scripts" / "capture_visual_scenarios.py")]
        )
        completed = subprocess.run(command, cwd=workspace, env=env, text=True, capture_output=True, errors="replace")
        if completed.stdout:
            print(completed.stdout, end="")
        if completed.stderr:
            print(completed.stderr, end="")
        if completed.returncode:
            return completed.returncode
        subprocess.run([sys.executable, str(workspace / "scripts" / "build_visual_inspection.py")], cwd=workspace, env=env, check=True)
        subprocess.run([sys.executable, str(workspace / "scripts" / "check_visual_approval.py")], cwd=workspace, env=env, check=True)
    print("ISOLIERTE VISUELLE REGRESSION BESTANDEN")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
