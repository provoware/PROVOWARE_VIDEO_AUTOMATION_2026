#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import stat
import zipfile
from pathlib import PurePosixPath
from typing import Any


def _unique_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Doppelter Manifestschlüssel: {key}")
        result[key] = value
    return result


def _archive_root(infos: list[zipfile.ZipInfo]) -> str:
    names = [item.filename for item in infos]
    if len(names) != len(set(names)):
        raise ValueError("ZIP enthält doppelte Namen.")
    roots: set[str] = set()
    for info in infos:
        path = PurePosixPath(info.filename)
        if path.is_absolute() or ".." in path.parts or len(path.parts) < 2:
            raise ValueError(f"Unsicherer ZIP-Pfad: {info.filename}")
        if info.filename != path.as_posix() or info.is_dir():
            raise ValueError(f"Nicht kanonischer ZIP-Pfad: {info.filename}")
        kind = stat.S_IFMT(info.external_attr >> 16)
        if kind not in (0, stat.S_IFREG):
            raise ValueError(f"ZIP enthält einen Link oder eine Spezialdatei: {info.filename}")
        roots.add(path.parts[0])
    if len(roots) != 1:
        raise ValueError("ZIP besitzt keine eindeutige Projektwurzel.")
    return roots.pop()


def verify_archive(archive: zipfile.ZipFile) -> int:
    infos = archive.infolist()
    root = _archive_root(infos)
    manifest_name = f"{root}/RELEASE_MANIFEST.json"
    manifest = json.loads(archive.read(manifest_name), object_pairs_hook=_unique_pairs)
    if not isinstance(manifest, dict):
        raise ValueError("ZIP-Manifest muss ein Objekt sein.")
    records = []
    for info in sorted(infos, key=lambda item: item.filename):
        if info.filename == manifest_name:
            continue
        mode = (info.external_attr >> 16) & 0o777
        if mode not in (0o644, 0o755):
            raise ValueError(f"Nicht kanonischer ZIP-Modus: {info.filename}")
        digest = hashlib.sha256()
        size = 0
        with archive.open(info) as source:
            for block in iter(lambda: source.read(1024 * 1024), b""):
                digest.update(block)
                size += len(block)
        records.append({
            "path": info.filename[len(root) + 1:], "size": size,
            "sha256": digest.hexdigest(), "mode": oct(mode),
        })
    if manifest.get("file_count", len(records)) != len(records):
        raise ValueError("ZIP-Dateizahl stimmt nicht mit Release-Manifest überein.")
    if manifest.get("schema_version") == 3 and manifest.get("representation") == "compact":
        encoded = json.dumps(records, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        if hashlib.sha256(encoded).hexdigest() != manifest.get("files_sha256"):
            raise ValueError("ZIP-Inhalt stimmt nicht mit kompaktem Release-Manifest überein.")
    elif manifest.get("schema_version") == 2:
        expected = manifest.get("files")
        if not isinstance(expected, list) or records != sorted(expected, key=lambda item: item["path"]):
            raise ValueError("ZIP-Inhalt stimmt nicht mit Release-Manifest überein.")
    else:
        raise ValueError("Unbekanntes ZIP-Manifestschema.")
    return len(records)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("zip_path")
    args = parser.parse_args()
    try:
        with zipfile.ZipFile(args.zip_path) as archive:
            count = verify_archive(archive)
    except (OSError, ValueError, KeyError, TypeError, zipfile.BadZipFile) as exc:
        print(f"RELEASE-ZIP BLOCKIERT: {exc}")
        return 1
    print(f"RELEASE-ZIP BESTANDEN · {count} Dateien + Manifest")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
