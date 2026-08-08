#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "RELEASE_MANIFEST.json"

SOURCE_PREFIXES = (".github/", "src/", "scripts/", "tests/", "registries/")
SOURCE_ROOT_FILES = {
    "pyproject.toml",
    "requirements.lock",
    "requirements-quality.lock",
    "requirements-toolchain.lock",
    "TOOLCHAIN_CONTRACT.json",
    "VERSION.json",
    "manifest.json",
    "STARTUP_CONTRACT.json",
    "FAULT_LAB_CONTRACT.json",
    "INSTALLER_SYSTEM_CONTRACT.json",
    "PORTABLE_RUNTIME_CONTRACT.json",
    "QUICK_MODES_MANIFEST.json",
    "VISUAL_INSPECTION_MANIFEST.json",
    "STABLE_OPERATOR_CONTRACT.json",
}
SOURCE_ROOT_SUFFIXES = (".sh", ".desktop")


class ReleaseIdentityError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_manifest(root: Path = ROOT) -> dict[str, Any]:
    path = root / "RELEASE_MANIFEST.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ReleaseIdentityError(f"Release-Manifest ist unlesbar: {exc}") from exc
    if not isinstance(data, dict) or not isinstance(data.get("files"), list):
        raise ReleaseIdentityError("Release-Manifest enthält keine vollständige Dateiliste.")
    return data


def is_source_path(relative: str) -> bool:
    if relative in SOURCE_ROOT_FILES or relative.endswith(SOURCE_ROOT_SUFFIXES):
        return True
    return relative.startswith(SOURCE_PREFIXES)


def _source_records(manifest: dict[str, Any], root: Path) -> Iterable[dict[str, Any]]:
    seen: set[str] = set()
    for raw in manifest.get("files", []):
        if not isinstance(raw, dict):
            raise ReleaseIdentityError("Ungültiger Dateieintrag im Release-Manifest.")
        relative = str(raw.get("path", ""))
        if not is_source_path(relative):
            continue
        if not relative or relative in seen or Path(relative).is_absolute() or ".." in Path(relative).parts:
            raise ReleaseIdentityError(f"Unsicherer oder doppelter Quellpfad: {relative!r}")
        seen.add(relative)
        path = root / relative
        if not path.is_file() or path.is_symlink():
            raise ReleaseIdentityError(f"Manifestierte Quelldatei fehlt oder ist Link: {relative}")
        size = path.stat().st_size
        digest = sha256_file(path)
        if size != int(raw.get("size", -1)) or digest != str(raw.get("sha256", "")):
            raise ReleaseIdentityError(f"Release-Manifest ist für Quelldatei veraltet: {relative}")
        yield {"path": relative, "size": size, "sha256": digest, "mode": str(raw.get("mode", ""))}


def source_sha256(root: Path = ROOT) -> tuple[str, int]:
    manifest = _load_manifest(root)
    records = list(_source_records(manifest, root))
    if not records:
        raise ReleaseIdentityError("Keine ausführungsrelevanten Quelldateien im Manifest gefunden.")
    encoded = json.dumps(records, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest(), len(records)


def release_identity(root: Path = ROOT) -> dict[str, Any]:
    manifest = _load_manifest(root)
    source_digest, source_count = source_sha256(root)
    manifest_path = root / "RELEASE_MANIFEST.json"
    candidate = str(manifest.get("build", ""))
    if not candidate:
        raise ReleaseIdentityError("Release-Kandidat fehlt im Manifest.")
    return {
        "schema_version": 1,
        "candidate_id": candidate,
        "manifest_sha256": sha256_file(manifest_path),
        "source_sha256": source_digest,
        "source_file_count": source_count,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Berechnet die unveränderliche Release-/Source-Identität.")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    payload = release_identity()
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"KANDIDAT {payload['candidate_id']}")
        print(f"MANIFEST_SHA256 {payload['manifest_sha256']}")
        print(f"SOURCE_SHA256 {payload['source_sha256']}")
        print(f"SOURCE_FILES {payload['source_file_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
