#!/usr/bin/env python3
"""Fail-closed root layout contract for Git source and extracted ZIP deliverables."""
from __future__ import annotations
import argparse
import subprocess
import zipfile
from pathlib import Path, PurePosixPath

MAX_ROOT_FILES = 8
REQUIRED = {"STARTEN.sh", "README.md"}

def root_files(root: Path) -> set[str]:
    if (root / ".git").exists():
        p = subprocess.run(["git", "-C", str(root), "ls-files", "-z", "--cached"],
                           check=True, stdout=subprocess.PIPE)
        return {raw.decode("utf-8") for raw in p.stdout.split(b"\x00")
                if raw and b"/" not in raw}
    return {path.name for path in root.iterdir() if path.is_file()}

def archive_root_files(archive: Path) -> set[str]:
    with zipfile.ZipFile(archive) as zf:
        names = []
        for item in zf.infolist():
            path = PurePosixPath(item.filename)
            if not item.is_dir() and path.parts:
                if path.is_absolute() or ".." in path.parts:
                    raise ValueError("Unsicherer Paketpfad: " + item.filename)
                names.append(path.parts)
        roots = {parts[0] for parts in names}
        prefix = next(iter(roots)) if len(roots) == 1 else ""
        return {parts[-1] for parts in names if len(parts) == (2 if prefix else 1)}

def validate(files: set[str]) -> None:
    if len(files) > MAX_ROOT_FILES:
        raise ValueError(f"Zu viele Hauptordnerdateien: {len(files)} (maximal {MAX_ROOT_FILES}): {sorted(files)}")
    absent = REQUIRED - files
    if absent:
        raise ValueError("Notwendige Benutzerdateien fehlen: " + ", ".join(sorted(absent)))

def main() -> int:
    p = argparse.ArgumentParser(description="Hauptordner von Repository oder Installations-ZIP prüfen")
    p.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    p.add_argument("--archive", type=Path, default=None)
    args = p.parse_args()
    files = archive_root_files(args.archive) if args.archive else root_files(args.root)
    try:
        validate(files)
    except ValueError as exc:
        print("HAUPTORDNER FEHLER:", exc)
        return 1
    print(f"HAUPTORDNER OK: {len(files)}/{MAX_ROOT_FILES} Dateien")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
