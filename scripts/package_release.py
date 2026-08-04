#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import stat
import zipfile
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
FIXED_ZIP_TIME = (2026, 1, 1, 0, 0, 0)


def _write(archive: zipfile.ZipFile, name: str, data: bytes, mode: int) -> None:
    info = zipfile.ZipInfo(name, FIXED_ZIP_TIME)
    info.create_system = 3
    info.external_attr = (stat.S_IFREG | (mode & 0o777)) << 16
    info.compress_type = zipfile.ZIP_DEFLATED
    archive.writestr(info, data, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)


def main() -> int:
    parser = argparse.ArgumentParser(description="Erzeugt ein deterministisches Release-ZIP aus RELEASE_MANIFEST.json.")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    version = json.loads((ROOT / "VERSION.json").read_text(encoding="utf-8"))
    manifest_path = ROOT / "RELEASE_MANIFEST.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    prefix = f"VideoBatch_Fast_{version['build']}"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(args.output, "w") as archive:
        for item in sorted(manifest["files"], key=lambda value: value["path"]):
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
