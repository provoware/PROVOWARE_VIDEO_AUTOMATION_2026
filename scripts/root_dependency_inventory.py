#!/usr/bin/env python3
"""Read-only root migration inventory with concrete file references."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEXT_EXTENSIONS = {".py", ".sh", ".md", ".txt", ".toml", ".json", ".yml", ".yaml", ".desktop"}
FROZEN_HINTS = ("_save_", "_rc24_", "RELEASE_MANIFEST.json", "VERSION.json")
ENTRYPOINTS = {"STARTEN.sh", "start.sh", "videobatch.sh", "test.sh",
               "setup.sh", "verify_release.sh", "autoinstall.sh"}


def classify(path: Path) -> str:
    name = path.name
    if name in ENTRYPOINTS:
        return "entrypoint_keep"
    if any(token.lower() in name.lower() for token in FROZEN_HINTS):
        return "frozen_or_contract"
    if path.suffix in {".json", ".lock", ".toml", ".desktop"}:
        return "contract_review_required"
    if path.suffix in {".sh"}:
        return "script_review_required"
    if path.suffix == ".md":
        return "document_review_required"
    return "manual_review"


def root_report(root: Path = ROOT) -> dict[str, object]:
    top = sorted((p for p in root.iterdir() if p.is_file() and not p.is_symlink()),
                 key=lambda p: p.name.lower())
    # Files and their references form a dependency index; it is never evidence
    # that a move is safe by itself. Humans must review dynamic path creation.
    names = {p.name for p in top}
    refs: dict[str, list[dict[str, object]]] = {p.name: [] for p in top}
    for path in root.rglob("*"):
        if not path.is_file() or path.is_symlink() or path.suffix not in TEXT_EXTENSIONS:
            continue
        if any(part in {".git", ".venv", "__pycache__"} for part in path.parts):
            continue
        rel = path.relative_to(root).as_posix()
        try:
            content = path.read_text(encoding="utf-8")
        except (UnicodeError, OSError):
            continue
        for number, line in enumerate(content.splitlines(), 1):
            present = names.intersection(re.findall(r"[\w.][\w.\-]*\.(?:md|sh|json|toml|lock|txt|desktop)", line))
            for name in present:
                if rel == name:
                    continue
                refs[name].append({"path": rel, "line": number})
    return {"schema_version": 1, "root": str(root.resolve()),
            "file_count": len(top), "items": [
                {"path": p.name, "role": classify(p), "references": refs[p.name][:80],
                 "references_truncated": len(refs[p.name]) > 80}
                for p in top],
            "warning": "Static references are incomplete for dynamically built paths.",
            "release_authorized": False}


def main() -> int:
    parser = argparse.ArgumentParser(description="Root-Dateien mit Pfadverbrauchern inventarisieren")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    report = root_report()
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"Dateien im Hauptordner: {report['file_count']}")
        for item in report["items"]:
            print(f"{item['path']} · {item['role']} · Verweise: {len(item['references'])}")
        print("Keine Freigabe; dynamische Pfade müssen gesondert geprüft werden.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
