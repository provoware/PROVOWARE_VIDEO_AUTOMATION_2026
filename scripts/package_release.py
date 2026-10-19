#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import stat
import sys
import tempfile
import zipfile
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
from build_release_manifest import build_payload, expected_files  # noqa: E402
FIXED_ZIP_TIME = (2026, 1, 1, 0, 0, 0)


def _write(archive: zipfile.ZipFile, name: str, data: bytes, mode: int) -> None:
    info = zipfile.ZipInfo(name, FIXED_ZIP_TIME)
    info.create_system = 3
    info.external_attr = (stat.S_IFREG | (mode & 0o777)) << 16
    info.compress_type = zipfile.ZIP_DEFLATED
    archive.writestr(info, data, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)


def main() -> int:
    parser = argparse.ArgumentParser(description="Erzeugt ein geprüftes deterministisches Entwicklungs-ZIP.")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    manifest_path = ROOT / "RELEASE_MANIFEST.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected = build_payload(compact=True)
    if manifest != expected:
        raise RuntimeError("Entwicklungsmanifest stimmt nicht mit dem tatsächlichen Quellbaum überein.")

    records = expected_files()
    if len(records) != manifest["file_count"]:
        raise RuntimeError("Manifest-Dateizahl und Dateiauswahl stimmen nicht überein.")

    prefix = f"VideoBatch_Fast_{manifest['build']}"
    root_names = {Path(record["path"]).name for record in records if len(Path(record["path"]).parts) == 1}
    root_names.add("RELEASE_MANIFEST.json")
    if len(root_names) > 8 or not {"STARTEN.sh", "README.md", "VERSION.json", "RELEASE_MANIFEST.json"} <= root_names:
        raise RuntimeError(f"Das Paket verletzt die Acht-Dateien-Regel: {sorted(root_names)}")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{args.output.name}.", suffix=".tmp", dir=args.output.parent)
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        with zipfile.ZipFile(temporary, "w") as archive:
            for record in records:
                relative = PurePosixPath(record["path"])
                if relative.is_absolute() or ".." in relative.parts:
                    raise RuntimeError(f"Unsicherer Paketpfad: {relative}")
                _write(archive, f"{prefix}/{relative.as_posix()}", (ROOT / relative).read_bytes(), int(record["mode"], 8))
            _write(archive, f"{prefix}/RELEASE_MANIFEST.json", manifest_path.read_bytes(), 0o644)
        with zipfile.ZipFile(temporary) as archive:
            bad = archive.testzip()
            if bad:
                raise RuntimeError(f"Beschädigter ZIP-Eintrag: {bad}")
        os.chmod(temporary, 0o644)
        os.replace(temporary, args.output)
    finally:
        temporary.unlink(missing_ok=True)
    print(f"DETERMINISTISCHES ENTWICKLUNGS-ZIP ERZEUGT · {args.output}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
