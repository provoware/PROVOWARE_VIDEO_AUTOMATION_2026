#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from release_file_contract import selected_release_files
from videobatch_fast.versioning import version_info
from videobatch_fast.visual_approval import (
    approval_fingerprint,
    inspection_manifest_hash,
    verify_visual_approval,
)

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "RELEASE_MANIFEST.json"


class ManifestContractError(RuntimeError):
    pass


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_record(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    return {
        "path": path.relative_to(ROOT).as_posix(),
        "size": len(data),
        "sha256": sha256_bytes(data),
        "mode": oct(path.stat().st_mode & 0o777),
    }


def expected_files() -> list[dict[str, Any]]:
    return [file_record(path) for path in selected_release_files(ROOT)]


def files_digest(files: Sequence[Mapping[str, Any]]) -> str:
    encoded = json.dumps(
        list(files),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return sha256_bytes(encoded)


def build_payload(*, compact: bool = False) -> dict[str, Any]:
    files = expected_files()
    visual_path = ROOT / "VISUAL_INSPECTION_MANIFEST.json"
    visual = (
        json.loads(visual_path.read_text(encoding="utf-8"))
        if visual_path.is_file()
        else {}
    )
    approval = verify_visual_approval(visual, ROOT) if visual else None
    version = version_info()
    payload: dict[str, Any] = {
        "schema_version": 3 if compact else 2,
        "name": str(version.get("name", "provoware - videoautomation - 2026")),
        "version": str(version.get("version", "0.0.0")),
        "build": str(version.get("build", version.get("version", "0.0.0"))),
        "channel": str(version.get("channel", "development")),
        "visual_approval": {
            "valid": bool(approval and approval.valid),
            "visual_contract_sha256": (
                inspection_manifest_hash(visual) if visual else ""
            ),
            "approval_sha256": approval_fingerprint(visual) if visual else "",
            "key_id": approval.key_id if approval else "",
        },
        "file_count": len(files),
    }
    if compact:
        payload.update(
            {
                "representation": "compact",
                "files_sha256": files_digest(files),
            }
        )
    else:
        payload["files"] = files
    return payload


def load_manifest() -> dict[str, Any]:
    try:
        value = json.loads(MANIFEST.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ManifestContractError(f"Manifest kann nicht gelesen werden: {exc}") from exc
    if not isinstance(value, dict):
        raise ManifestContractError("Manifest-Wurzel muss ein JSON-Objekt sein")
    return value


def records_by_path(value: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    records = value.get("files")
    if not isinstance(records, list):
        raise ManifestContractError("Manifestfeld 'files' muss eine Liste sein")
    result: dict[str, dict[str, Any]] = {}
    for record in records:
        if not isinstance(record, dict):
            raise ManifestContractError("Jeder Manifestdateieintrag muss ein Objekt sein")
        path = str(record.get("path") or "")
        if not path or path in result:
            raise ManifestContractError(f"Ungültiger oder doppelter Manifestpfad: {path!r}")
        result[path] = record
    return result


def manifest_is_compact(value: Mapping[str, Any]) -> bool:
    return value.get("representation") == "compact"


def drift_report(current: Mapping[str, Any], expected: Mapping[str, Any]) -> dict[str, Any]:
    changes: list[dict[str, Any]] = []
    current_compact = manifest_is_compact(current)
    expected_compact = manifest_is_compact(expected)
    if not current_compact and not expected_compact:
        current_records = records_by_path(current)
        expected_records = records_by_path(expected)
        for path in sorted(set(current_records) | set(expected_records)):
            actual = current_records.get(path)
            wanted = expected_records.get(path)
            if actual == wanted:
                continue
            if actual is None:
                kind = "missing"
            elif wanted is None:
                kind = "unexpected"
            else:
                kind = "changed"
            changes.append(
                {
                    "kind": kind,
                    "path": path,
                    "actual": actual,
                    "expected": wanted,
                }
            )

    metadata_fields = (
        "schema_version",
        "representation",
        "name",
        "version",
        "build",
        "channel",
        "visual_approval",
        "file_count",
        "files_sha256",
    )
    metadata = [
        {
            "field": field,
            "actual": current.get(field),
            "expected": expected.get(field),
        }
        for field in metadata_fields
        if current.get(field) != expected.get(field)
    ]
    return {
        "schema_version": 1,
        "status": "passed" if not changes and not metadata else "drift",
        "manifest": MANIFEST.relative_to(ROOT).as_posix(),
        "representation": "compact" if expected_compact else "full",
        "file_changes": changes,
        "metadata_changes": metadata,
    }


def write_manifest(payload: Mapping[str, Any]) -> int:
    MANIFEST.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        f"RELEASE-MANIFEST ERZEUGT · {payload['file_count']} Dateien · "
        f"{payload['channel']} · visuelle Freigabe "
        f"{payload['visual_approval']['valid']}"
    )
    return 0


def check_manifest(payload: Mapping[str, Any], json_output: bool) -> int:
    try:
        report = drift_report(load_manifest(), payload)
    except ManifestContractError as exc:
        report = {
            "schema_version": 1,
            "status": "invalid",
            "manifest": MANIFEST.relative_to(ROOT).as_posix(),
            "error": str(exc),
            "file_changes": [],
            "metadata_changes": [],
        }

    if json_output:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    elif report["status"] == "passed":
        print(f"RELEASE-MANIFEST BESTANDEN · {payload['file_count']} Dateien")
    else:
        print("RELEASE-MANIFEST DRIFT")
        if report.get("error"):
            print(f"✕ {report['error']}")
        for change in report["file_changes"]:
            print(json.dumps(change, ensure_ascii=False, sort_keys=True))
        for change in report["metadata_changes"]:
            print(json.dumps(change, ensure_ascii=False, sort_keys=True))
    return 0 if report["status"] == "passed" else 1


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        description="Erzeugt das Release-Manifest oder prüft es vollständig lesend auf Drift."
    )
    result.add_argument(
        "--check",
        action="store_true",
        help="Manifest nicht schreiben, sondern Drift und erwartete Datensätze ausgeben.",
    )
    result.add_argument(
        "--json",
        action="store_true",
        help="Prüfergebnis als deterministisches JSON auf stdout ausgeben.",
    )
    result.add_argument(
        "--compact",
        action="store_true",
        help="Kompaktes Manifest mit kanonischem Gesamt-SHA-256 erzeugen oder prüfen.",
    )
    return result


def main(argv: Sequence[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if args.json and not args.check:
        parser().error("--json erfordert --check")
    compact = bool(args.compact)
    if args.check and not compact:
        try:
            compact = manifest_is_compact(load_manifest())
        except ManifestContractError:
            compact = False
    payload = build_payload(compact=compact)
    return (
        check_manifest(payload, json_output=bool(args.json))
        if args.check
        else write_manifest(payload)
    )


if __name__ == "__main__":
    raise SystemExit(main())
