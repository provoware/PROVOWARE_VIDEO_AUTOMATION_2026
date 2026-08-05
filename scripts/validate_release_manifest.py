#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from pathlib import Path, PurePosixPath

from release_file_contract import included_release_file

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "RELEASE_MANIFEST.json"


def main() -> int:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    errors: list[str] = []
    listed: set[str] = set()
    for item in manifest.get("files", []):
        rel = str(item.get("path", ""))
        pure = PurePosixPath(rel)
        if pure.is_absolute() or ".." in pure.parts or rel in listed:
            errors.append(f"unsicher/dupliziert: {rel}")
            continue
        listed.add(rel)
        path = ROOT.joinpath(*pure.parts)
        if not path.is_file() or path.is_symlink():
            errors.append(f"fehlt oder Link: {rel}")
            continue
        data = path.read_bytes()
        if len(data) != int(item.get("size", -1)):
            errors.append(f"Größe: {rel}")
        if hashlib.sha256(data).hexdigest() != str(item.get("sha256", "")):
            errors.append(f"Hash: {rel}")
        expected_mode = str(item.get("mode", ""))
        if expected_mode and oct(path.stat().st_mode & 0o777) != expected_mode:
            errors.append(f"Modus: {rel}")
    actual = {
        path.relative_to(ROOT).as_posix()
        for path in ROOT.rglob("*")
        if included_release_file(ROOT, path)
    }
    for rel in sorted(actual - listed):
        errors.append(f"nicht manifestiert: {rel}")
    for rel in sorted(listed - actual):
        errors.append(f"manifestiert aber ausgeschlossen/fehlend: {rel}")
    if len(listed) != int(manifest.get("file_count", -1)):
        errors.append("Dateizahl stimmt nicht")
    if errors:
        print("RELEASE-MANIFEST FEHLGESCHLAGEN")
        for error in errors[:100]:
            print(f"✕ {error}")
        return 1
    print(
        f"RELEASE-MANIFEST BESTANDEN · {len(listed)} Dateien · "
        "keine unregistrierten Nutzdateien"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
