#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "RELEASE_MANIFEST.json"
EVIDENCE_PATH = ROOT / "diagnostics/release_readiness/RELEASE_EVIDENCE.json"
QUALITY_PATH = ROOT / "QUALITY_ENVIRONMENT_STATUS.json"
BUILD_REPORT_PATH = ROOT / "VideoBatch_Fast_2.8.3-rc24_BUILD_REPORT_save_.json"
README_PATH = ROOT / "README.md"
STATUS_PATH = ROOT / "STATUS.md"
TODO_PATH = ROOT / "TODO.md"


class ContractSyncError(RuntimeError):
    pass


def _reject_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ContractSyncError(f"Doppelter JSON-Schlüssel {key!r}")
        result[key] = value
    return result


def _load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_reject_duplicate_pairs,
        )
    except (OSError, UnicodeError, json.JSONDecodeError, ContractSyncError) as exc:
        raise ContractSyncError(f"{path.relative_to(ROOT)} ist kein eindeutiges gültiges JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise ContractSyncError(f"{path.relative_to(ROOT)} muss ein JSON-Objekt sein")
    return value


def _mapping(value: object, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ContractSyncError(f"{label} muss ein Objekt sein")
    return value


def _sha256_text(value: object) -> bool:
    text = str(value or "")
    return len(text) == 64 and all(char in "0123456789abcdefABCDEF" for char in text)


def validate() -> dict[str, Any]:
    manifest = _load(MANIFEST_PATH)
    evidence = _load(EVIDENCE_PATH)
    quality = _load(QUALITY_PATH)
    build = _load(BUILD_REPORT_PATH)

    if manifest.get("schema_version") != 3 or manifest.get("representation") != "compact":
        raise ContractSyncError("RELEASE_MANIFEST.json muss Schema 3 in kompakter Darstellung verwenden")
    count = manifest.get("file_count")
    if not isinstance(count, int) or count <= 0:
        raise ContractSyncError("RELEASE_MANIFEST.json enthält keine gültige Dateizahl")
    if not _sha256_text(manifest.get("files_sha256")):
        raise ContractSyncError("RELEASE_MANIFEST.json enthält keinen gültigen files_sha256")

    product = _mapping(evidence.get("product"), "RELEASE_EVIDENCE.product")
    evidence_manifest = _mapping(evidence.get("manifest"), "RELEASE_EVIDENCE.manifest")
    if evidence_manifest.get("file_count") != count:
        raise ContractSyncError(
            f"RELEASE_EVIDENCE nennt {evidence_manifest.get('file_count')} statt {count} Manifestdateien"
        )
    if evidence_manifest.get("status") != "passed":
        raise ContractSyncError("RELEASE_EVIDENCE.manifest.status muss passed sein")
    if product.get("version") != manifest.get("version") or product.get("version") != manifest.get("build"):
        raise ContractSyncError("Produktversion und Manifest version/build sind nicht synchron")
    if product.get("channel") != manifest.get("channel"):
        raise ContractSyncError("Release-Kanal in Evidence und Manifest ist nicht synchron")

    internal = _mapping(quality.get("internal_gates"), "QUALITY_ENVIRONMENT_STATUS.internal_gates")
    if internal.get("release_manifest_files") != count:
        raise ContractSyncError("QUALITY_ENVIRONMENT_STATUS enthält eine veraltete Manifest-Dateizahl")
    if build.get("release_manifest_files") != count:
        raise ContractSyncError("Buildbericht enthält eine veraltete Manifest-Dateizahl")

    expected_line = f"Release-Manifest: {count} Dateien"
    for path in (README_PATH, STATUS_PATH):
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            raise ContractSyncError(f"{path.name} kann nicht gelesen werden: {exc}") from exc
        if expected_line not in text:
            raise ContractSyncError(f"{path.name} enthält nicht den aktuellen Status: {expected_line}")

    todo = TODO_PATH.read_text(encoding="utf-8")
    if "P0 – vor Merge von PR #128" in todo or "P0 - vor Merge von PR #128" in todo:
        raise ContractSyncError("TODO.md enthält noch den überholten Vor-Merge-Abschnitt für PR #128")

    return {
        "schema_version": 1,
        "status": "passed",
        "version": manifest.get("version"),
        "channel": manifest.get("channel"),
        "manifest_files": count,
        "manifest_files_sha256": manifest.get("files_sha256"),
        "stable_ready": bool(evidence.get("stable_ready")),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Prüft Manifest, Release-Evidence und abgeleitete Statusdateien auf Drift.")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        result = validate()
    except (ContractSyncError, OSError) as exc:
        if args.json:
            print(json.dumps({"schema_version": 1, "status": "failed", "error": str(exc)}, ensure_ascii=False, indent=2, sort_keys=True))
        else:
            print(f"RELEASE-CONTRACT-DRIFT: {exc}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(
            f"RELEASE-CONTRACT BESTANDEN · {result['version']} · "
            f"{result['manifest_files']} Dateien · Stable={result['stable_ready']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
