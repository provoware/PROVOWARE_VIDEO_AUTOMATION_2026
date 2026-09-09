#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_NAME = "PROVOWARE_VideoBatch_2.8.3-rc24_Kubuntu-26.04_Wayland_Preview1.zip"
EXCLUDED_DIRS = {
    ".git", ".venv", "venv", "__pycache__", ".pytest_cache", ".ruff_cache",
    ".mypy_cache", ".tox", "node_modules", "dist", "build", "debugging"
}
EXCLUDED_SUFFIXES = {".pyc", ".pyo", ".tmp", ".swp"}
EXCLUDED_FILES = {".DS_Store"}
FIXED_DATE = (2026, 9, 10, 0, 0, 0)


def tracked_files() -> list[Path]:
    try:
        result = subprocess.run(
            ["git", "ls-files", "-z"], cwd=ROOT, stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL, check=True,
        )
        names = [name for name in result.stdout.decode("utf-8").split("\0") if name]
        return [ROOT / name for name in names]
    except (OSError, subprocess.CalledProcessError, UnicodeDecodeError):
        return [p for p in ROOT.rglob("*") if p.is_file()]


def include(path: Path, output: Path) -> bool:
    try:
        relative = path.relative_to(ROOT)
    except ValueError:
        return False
    if path.resolve() == output.resolve():
        return False
    if any(part in EXCLUDED_DIRS for part in relative.parts):
        return False
    if path.name in EXCLUDED_FILES or path.suffix.lower() in EXCLUDED_SUFFIXES:
        return False
    return True


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "dist" / DEFAULT_NAME)
    args = parser.parse_args()
    output = args.output if args.output.is_absolute() else ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)

    files = sorted((p for p in tracked_files() if include(p, output)), key=lambda p: p.as_posix())
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in files:
            relative = path.relative_to(ROOT).as_posix()
            info = zipfile.ZipInfo(relative, FIXED_DATE)
            info.compress_type = zipfile.ZIP_DEFLATED
            mode = path.stat().st_mode & 0o777
            info.external_attr = (mode or 0o644) << 16
            archive.writestr(info, path.read_bytes())

    manifest = {
        "schema_version": 1,
        "archive": output.name,
        "files": len(files),
        "bytes": output.stat().st_size,
        "sha256": sha256(output),
    }
    manifest_path = output.with_suffix(output.suffix + ".sha256.json")
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
