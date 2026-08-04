#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

EXCLUDED = {
    ".git", ".pytest_cache", ".ruff_cache", ".mypy_cache", ".videobatch-venv",
    "dist", "diagnostics", "visual_actual", "actual", "diff", "__pycache__",
}
BINARY_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".zip", ".whl", ".pyc", ".pem"}


def ignore(_directory: str, names: list[str]) -> set[str]:
    return {name for name in names if name in EXCLUDED or name.endswith((".pyc", ".pyo"))}


def replace_text(root: Path, old_build: str, stable: str) -> None:
    old_pep = old_build.replace("-rc", "rc")
    for path in root.rglob("*"):
        if not path.is_file() or path.is_symlink() or path.suffix.lower() in BINARY_SUFFIXES:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            continue
        updated = text.replace(old_build, stable).replace(old_pep, stable)
        if updated != text:
            path.write_text(updated, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Erzeugt eine getrennte Stable-Arbeitskopie.")
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--stable-version", default="2.8.3")
    args = parser.parse_args()
    source = args.source.resolve(strict=True)
    destination = args.destination.resolve(strict=False)
    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(source, destination, symlinks=False, ignore=ignore)
    version_path = destination / "VERSION.json"
    version = json.loads(version_path.read_text(encoding="utf-8"))
    old_build = str(version["build"])
    replace_text(destination, old_build, args.stable_version)
    version = json.loads(version_path.read_text(encoding="utf-8"))
    version.update({
        "version": args.stable_version,
        "build": args.stable_version,
        "channel": "stable",
        "purpose": "Stabile VideoBatch-Freigabe nach vollständig grüner autonomer Releaseprüfung.",
    })
    version_path.write_text(json.dumps(version, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for relative in ("AUTOMATED_DESKTOP_APPROVAL.json", "visual_inspection/live_desktop_approval.png", "RELEASE_MANIFEST.json"):
        (destination / relative).unlink(missing_ok=True)
    for old_name, new_name in (
        (f"IMPLEMENTATION_REPORT_{old_build}.md", f"IMPLEMENTATION_REPORT_{args.stable_version}.md"),
        (f"CODE_QUALITY_REPORT_{old_build}.md", f"CODE_QUALITY_REPORT_{args.stable_version}.md"),
    ):
        old = destination / old_name
        if old.exists():
            old.rename(destination / new_name)
    print(f"STABLE-ARBEITSKOPIE ERZEUGT · {destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
