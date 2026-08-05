#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from pathlib import Path
from typing import Any, Sequence

CHUNK_SIZE = 1024 * 1024


def sha256_member(source: zipfile.ZipFile, info: zipfile.ZipInfo) -> str:
    digest = hashlib.sha256()
    with source.open(info, "r") as handle:
        while chunk := handle.read(CHUNK_SIZE):
            digest.update(chunk)
    return digest.hexdigest()


def build_index(archive: Path, commit: str) -> dict[str, Any]:
    entries: list[dict[str, object]] = []
    with zipfile.ZipFile(archive, "r") as source:
        bad_member = source.testzip()
        if bad_member is not None:
            raise ValueError(f"Beschädigter ZIP-Eintrag: {bad_member}")
        for info in sorted(source.infolist(), key=lambda item: item.filename):
            if info.is_dir():
                continue
            entries.append(
                {
                    "path": info.filename,
                    "size": info.file_size,
                    "sha256": sha256_member(source, info),
                }
            )
    return {
        "schema_version": 1,
        "archive": archive.name,
        "commit": commit,
        "file_count": len(entries),
        "total_uncompressed_size": sum(int(item["size"]) for item in entries),
        "entries": entries,
    }


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        description="Erzeugt eine deterministische SHA-256-Inhaltsliste für ein ZIP-Artefakt."
    )
    result.add_argument("archive", type=Path)
    result.add_argument("--commit", required=True)
    result.add_argument("--output", type=Path, required=True)
    return result


def main(argv: Sequence[str] | None = None) -> int:
    args = parser().parse_args(argv)
    archive = args.archive.resolve()
    if not archive.is_file():
        raise SystemExit(f"ZIP-Artefakt fehlt: {archive}")
    payload = build_index(archive, str(args.commit))
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    verified = json.loads(args.output.read_text(encoding="utf-8"))
    if verified != payload:
        raise SystemExit("ARTIFACT_CONTENTS-Roundtrip fehlgeschlagen")
    print(
        "ARTIFACT-CONTENTS BESTANDEN · "
        f"{payload['file_count']} Dateien · "
        f"{payload['total_uncompressed_size']} Bytes"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
