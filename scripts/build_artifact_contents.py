#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from pathlib import Path
from typing import Any, Mapping, Sequence

CHUNK_SIZE = 1024 * 1024
SCHEMA_VERSION = 1


class ArtifactContentsError(RuntimeError):
    """Raised when an archive or content index violates the contract."""


def sha256_member(source: zipfile.ZipFile, info: zipfile.ZipInfo) -> str:
    digest = hashlib.sha256()
    with source.open(info, "r") as handle:
        while chunk := handle.read(CHUNK_SIZE):
            digest.update(chunk)
    return digest.hexdigest()


def build_index(archive: Path, commit: str) -> dict[str, Any]:
    entries: list[dict[str, object]] = []
    seen_paths: set[str] = set()
    try:
        with zipfile.ZipFile(archive, "r") as source:
            bad_member = source.testzip()
            if bad_member is not None:
                raise ArtifactContentsError(f"Beschädigter ZIP-Eintrag: {bad_member}")
            for info in sorted(source.infolist(), key=lambda item: item.filename):
                if info.is_dir():
                    continue
                if info.filename in seen_paths:
                    raise ArtifactContentsError(
                        f"Doppelter ZIP-Pfad ist unzulässig: {info.filename}"
                    )
                seen_paths.add(info.filename)
                entries.append(
                    {
                        "path": info.filename,
                        "size": info.file_size,
                        "sha256": sha256_member(source, info),
                    }
                )
    except (OSError, zipfile.BadZipFile, zipfile.LargeZipFile) as exc:
        raise ArtifactContentsError(f"ZIP-Artefakt ist nicht lesbar: {exc}") from exc
    return {
        "schema_version": SCHEMA_VERSION,
        "archive": archive.name,
        "commit": commit,
        "file_count": len(entries),
        "total_uncompressed_size": sum(int(item["size"]) for item in entries),
        "entries": entries,
    }


def load_index(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ArtifactContentsError(f"Inhaltsindex ist nicht lesbar: {exc}") from exc
    if not isinstance(value, dict):
        raise ArtifactContentsError("Inhaltsindex-Wurzel muss ein JSON-Objekt sein")
    validate_index(value)
    return value


def validate_entry(value: object, position: int) -> dict[str, object]:
    if not isinstance(value, Mapping):
        raise ArtifactContentsError(f"Eintrag {position} muss ein Objekt sein")
    path = value.get("path")
    size = value.get("size")
    sha256 = value.get("sha256")
    if not isinstance(path, str) or not path or path.endswith("/"):
        raise ArtifactContentsError(f"Eintrag {position} enthält ungültigen Pfad")
    if not isinstance(size, int) or isinstance(size, bool) or size < 0:
        raise ArtifactContentsError(f"Eintrag {path} enthält ungültige Größe")
    if (
        not isinstance(sha256, str)
        or len(sha256) != 64
        or any(character not in "0123456789abcdef" for character in sha256)
    ):
        raise ArtifactContentsError(f"Eintrag {path} enthält ungültigen SHA-256")
    return {"path": path, "size": size, "sha256": sha256}


def validate_index(value: Mapping[str, Any]) -> None:
    if value.get("schema_version") != SCHEMA_VERSION:
        raise ArtifactContentsError(f"schema_version muss {SCHEMA_VERSION} sein")
    if not isinstance(value.get("archive"), str) or not value["archive"]:
        raise ArtifactContentsError("Archivname fehlt")
    if not isinstance(value.get("commit"), str) or not value["commit"]:
        raise ArtifactContentsError("Commit-SHA fehlt")
    raw_entries = value.get("entries")
    if not isinstance(raw_entries, list):
        raise ArtifactContentsError("entries muss eine Liste sein")
    entries = [validate_entry(item, index) for index, item in enumerate(raw_entries)]
    paths = [str(item["path"]) for item in entries]
    if len(paths) != len(set(paths)):
        raise ArtifactContentsError("Inhaltsindex enthält doppelte Pfade")
    if paths != sorted(paths):
        raise ArtifactContentsError("Inhaltsindex ist nicht deterministisch sortiert")
    if value.get("file_count") != len(entries):
        raise ArtifactContentsError("file_count widerspricht der Eintragszahl")
    expected_size = sum(int(item["size"]) for item in entries)
    if value.get("total_uncompressed_size") != expected_size:
        raise ArtifactContentsError(
            "total_uncompressed_size widerspricht den Eintragsgrößen"
        )


def compare_indexes(
    expected: Mapping[str, Any], actual: Mapping[str, Any]
) -> dict[str, Any]:
    expected_entries = {str(item["path"]): item for item in expected["entries"]}
    actual_entries = {str(item["path"]): item for item in actual["entries"]}
    findings: list[dict[str, Any]] = []

    for path in sorted(expected_entries.keys() - actual_entries.keys()):
        findings.append(
            {"kind": "missing", "path": path, "expected": expected_entries[path]}
        )
    for path in sorted(actual_entries.keys() - expected_entries.keys()):
        findings.append(
            {"kind": "unexpected", "path": path, "actual": actual_entries[path]}
        )
    for path in sorted(expected_entries.keys() & actual_entries.keys()):
        expected_entry = expected_entries[path]
        actual_entry = actual_entries[path]
        if expected_entry["size"] != actual_entry["size"]:
            findings.append(
                {
                    "kind": "size_changed",
                    "path": path,
                    "expected": expected_entry["size"],
                    "actual": actual_entry["size"],
                }
            )
        if expected_entry["sha256"] != actual_entry["sha256"]:
            findings.append(
                {
                    "kind": "sha256_changed",
                    "path": path,
                    "expected": expected_entry["sha256"],
                    "actual": actual_entry["sha256"],
                }
            )

    metadata_findings: list[dict[str, Any]] = []
    for field in (
        "archive",
        "commit",
        "file_count",
        "total_uncompressed_size",
    ):
        if expected.get(field) != actual.get(field):
            metadata_findings.append(
                {
                    "kind": "metadata_changed",
                    "field": field,
                    "expected": expected.get(field),
                    "actual": actual.get(field),
                }
            )

    return {
        "schema_version": 1,
        "status": "passed" if not findings and not metadata_findings else "failed",
        "archive": actual["archive"],
        "commit": actual["commit"],
        "finding_count": len(findings) + len(metadata_findings),
        "metadata_findings": metadata_findings,
        "entry_findings": findings,
    }


def write_index(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    verified = json.loads(path.read_text(encoding="utf-8"))
    if verified != payload:
        raise ArtifactContentsError("ARTIFACT_CONTENTS-Roundtrip fehlgeschlagen")


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        description=(
            "Erzeugt oder prüft eine deterministische SHA-256-Inhaltsliste "
            "für ein ZIP-Artefakt."
        )
    )
    result.add_argument("archive", type=Path)
    mode = result.add_mutually_exclusive_group(required=True)
    mode.add_argument("--output", type=Path, help="ARTIFACT_CONTENTS.json erzeugen")
    mode.add_argument("--check", type=Path, metavar="INDEX", help="ZIP gegen Index prüfen")
    result.add_argument("--commit", help="Erwarteter Commit-SHA; im Schreibmodus Pflicht")
    result.add_argument("--json", action="store_true", help="Prüfergebnis als JSON ausgeben")
    return result


def main(argv: Sequence[str] | None = None) -> int:
    args = parser().parse_args(argv)
    archive = args.archive.resolve()
    if not archive.is_file():
        raise SystemExit(f"ZIP-Artefakt fehlt: {archive}")

    try:
        if args.output is not None:
            if not args.commit:
                raise ArtifactContentsError("--commit ist im Schreibmodus erforderlich")
            payload = build_index(archive, str(args.commit))
            write_index(args.output, payload)
            print(
                "ARTIFACT-CONTENTS ERZEUGT · "
                f"{payload['file_count']} Dateien · "
                f"{payload['total_uncompressed_size']} Bytes"
            )
            return 0

        expected = load_index(args.check)
        commit = str(args.commit) if args.commit else str(expected["commit"])
        actual = build_index(archive, commit)
        result = compare_indexes(expected, actual)
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        elif result["status"] == "passed":
            print(
                "ARTIFACT-CONTENTS BESTANDEN · "
                f"{actual['file_count']} Dateien · "
                f"{actual['total_uncompressed_size']} Bytes"
            )
        else:
            print(f"ARTIFACT-CONTENTS FEHLGESCHLAGEN · {result['finding_count']} Abweichungen")
            for finding in result["metadata_findings"]:
                print(f"✕ Metadatum {finding['field']}: {finding['actual']!r}")
            for finding in result["entry_findings"]:
                print(f"✕ {finding['kind']}: {finding['path']}")
        return 0 if result["status"] == "passed" else 1
    except ArtifactContentsError as exc:
        if args.json:
            print(
                json.dumps(
                    {
                        "schema_version": 1,
                        "status": "error",
                        "finding_count": 1,
                        "error": str(exc),
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
        else:
            print(f"ARTIFACT-CONTENTS FEHLER · {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
