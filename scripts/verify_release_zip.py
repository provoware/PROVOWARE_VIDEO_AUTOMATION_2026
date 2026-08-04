#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import stat
import zipfile
from pathlib import PurePosixPath


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("zip_path")
    args = parser.parse_args()
    with zipfile.ZipFile(args.zip_path) as archive:
        infos = archive.infolist()
        names = [item.filename for item in infos]
        if len(names) != len(set(names)):
            raise SystemExit("ZIP enthält doppelte Namen.")
        roots = {PurePosixPath(name).parts[0] for name in names if PurePosixPath(name).parts}
        if len(roots) != 1:
            raise SystemExit("ZIP besitzt keine eindeutige Projektwurzel.")
        root = next(iter(roots))
        manifest_name = f"{root}/RELEASE_MANIFEST.json"
        manifest = json.loads(archive.read(manifest_name).decode("utf-8"))
        expected = {f"{root}/{item['path']}": item for item in manifest["files"]}
        actual = set(names) - {manifest_name}
        if actual != set(expected):
            raise SystemExit("ZIP-Dateiliste stimmt nicht mit Release-Manifest überein.")
        for name, item in expected.items():
            info = archive.getinfo(name)
            mode = (info.external_attr >> 16) & 0o777
            data = archive.read(name)
            if len(data) != int(item["size"]):
                raise SystemExit(f"ZIP-Größe stimmt nicht: {name}")
            if hashlib.sha256(data).hexdigest() != item["sha256"]:
                raise SystemExit(f"ZIP-Hash stimmt nicht: {name}")
            if mode != int(str(item["mode"]), 8):
                raise SystemExit(f"ZIP-Modus stimmt nicht: {name}")
    print(f"RELEASE-ZIP BESTANDEN · {len(expected)} Dateien + Manifest")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
