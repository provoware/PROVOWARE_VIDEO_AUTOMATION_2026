#!/usr/bin/env python3
"""Canonical SHA-256 primitives for development files and test dependency sets."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path, PurePosixPath


def digest_json(value: object) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True,
                         separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def file_sha256(path: Path) -> str:
    """Stream file; reject a file that changes while being hashed."""
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"Unsichere oder fehlende Datei: {path}")
    before = path.stat()
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    after = path.stat()
    if (before.st_size, before.st_mtime_ns, before.st_ctime_ns,
        before.st_ino, before.st_dev) != (
        after.st_size, after.st_mtime_ns, after.st_ctime_ns,
        after.st_ino, after.st_dev
    ):
        raise ValueError(f"Datei während der Prüfung verändert: {path}")
    return digest.hexdigest()


def dependency_digest(files: dict, paths: list[str]) -> str:
    """Fail closed for missing inputs; names are part of identity."""
    if not paths or len(paths) != len(set(paths)):
        raise ValueError("Abhängigkeiten fehlen oder sind doppelt")
    entries = []
    for name in sorted(paths):
        pure = PurePosixPath(name)
        if (pure.is_absolute() or ".." in pure.parts or
                not name or name.startswith("./") or "\\" in name):
            raise ValueError(f"Ungültiger Projektpfad: {name}")
        item = files.get(name)
        if not isinstance(item, dict):
            raise ValueError(f"Abhängigkeit fehlt: {name}")
        digest = item.get("sha256")
        if not isinstance(digest, str) or len(digest) != 64 or any(
                c not in "0123456789abcdef" for c in digest):
            raise ValueError(f"SHA-256 fehlt oder ist ungültig: {name}")
        entries.append([name, digest])
    return digest_json({"schema_version": 1, "inputs": entries})
