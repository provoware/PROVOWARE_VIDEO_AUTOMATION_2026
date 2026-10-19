#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import sys
import zipfile
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from release_file_contract import selected_release_files  # noqa: E402
FIXED_ZIP_TIME = (2026, 1, 1, 0, 0, 0)


def _write(archive: zipfile.ZipFile, name: str, data: bytes, mode: int) -> None:
    info = zipfile.ZipInfo(name, FIXED_ZIP_TIME)
    info.create_system = 3
    info.external_attr = (stat.S_IFREG | (mode & 0o777)) << 16
    info.compress_type = zipfile.ZIP_DEFLATED
    archive.writestr(info, data, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)



def _records() -> list[dict[str, object]]:
    """Rebuild exactly the canonical records used by the compact manifest."""
    records: list[dict[str, object]] = []
    for path in selected_release_files(ROOT):
        raw = path.read_bytes()
        records.append({
            "path": path.relative_to(ROOT).as_posix(),
            "size": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest(),
            "mode": "0o755" if path.stat().st_mode & 0o111 else "0o644",
        })
    return records


def verified_records(manifest: dict) -> list[dict[str, object]]:
    records = _records()
    if manifest.get("representation") == "compact" and manifest.get("schema_version") == 3:
        encoded = json.dumps(records, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        digest = hashlib.sha256(encoded).hexdigest()
        if manifest.get("file_count") != len(records) or manifest.get("files_sha256") != digest:
            raise ValueError("Kompaktes Release-Manifest stimmt nicht mit den Paketdateien überein.")
    elif manifest.get("schema_version") == 2 and manifest.get("files") == records:
        pass
    else:
        raise ValueError("Unbekanntes oder veraltetes Release-Manifest; Paketbau verweigert.")
    return records



def validate_package_root(records: list[dict[str, object]]) -> None:
    """Check the actual ZIP root independently of the repository layout."""
    roots = {
        str(item["path"])
        for item in records
        if "/" not in str(item["path"])
    }
    roots.add("RELEASE_MANIFEST.json")  # Added separately to the ZIP.
    required = {"STARTEN.sh", "README.md", "VERSION.json", "RELEASE_MANIFEST.json"}
    if len(roots) > 8:
        raise ValueError(f"Entpacktes Benutzerpaket enthält {len(roots)} statt höchstens acht Hauptordnerdateien.")
    missing = required - roots
    if missing:
        raise ValueError("Pflichtdateien im Benutzerpaket fehlen: " + ", ".join(sorted(missing)))


def main() -> int:
    parser = argparse.ArgumentParser(description="Erzeugt ein deterministisches Release-ZIP aus RELEASE_MANIFEST.json.")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    version = json.loads((ROOT / "VERSION.json").read_text(encoding="utf-8"))
    manifest_path = ROOT / "RELEASE_MANIFEST.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    records = verified_records(manifest)
    validate_package_root(records)
    prefix = f"VideoBatch_Fast_{version['build']}"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(args.output, "w") as archive:
        for item in records:
            relative = PurePosixPath(item["path"])
            path = ROOT.joinpath(*relative.parts)
            mode = int(str(item["mode"]), 8)
            _write(archive, f"{prefix}/{relative.as_posix()}", path.read_bytes(), mode)
        _write(archive, f"{prefix}/RELEASE_MANIFEST.json", manifest_path.read_bytes(), 0o644)
    os.chmod(args.output, 0o644)
    print(f"DETERMINISTISCHES RELEASE-ZIP ERZEUGT · {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
