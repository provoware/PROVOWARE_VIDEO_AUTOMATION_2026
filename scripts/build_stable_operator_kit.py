#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path, PurePosixPath
import stat
import tempfile
import zipfile

try:
    from release_identity import ROOT, release_identity
    from validate_release_manifest import main as validate_release_manifest
except ImportError:
    from scripts.release_identity import ROOT, release_identity
    from scripts.validate_release_manifest import main as validate_release_manifest

FIXED = (2026, 1, 1, 0, 0, 0)


def _write(archive: zipfile.ZipFile, name: str, data: bytes, mode: int) -> None:
    info = zipfile.ZipInfo(name, FIXED)
    info.create_system = 3
    info.external_attr = (stat.S_IFREG | (mode & 0o777)) << 16
    info.compress_type = zipfile.ZIP_DEFLATED
    archive.writestr(info, data, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)


def build(output: Path) -> Path:
    if validate_release_manifest() != 0:
        raise RuntimeError("Release-Manifest ist nicht aktuell; Operator-Kit wird nicht gebaut.")
    identity = release_identity()
    manifest = json.loads((ROOT / "RELEASE_MANIFEST.json").read_text(encoding="utf-8"))
    prefix = "PROVOWARE_W18_OPERATOR_KIT"
    wrapper = b'''#!/usr/bin/env bash\nset -Eeuo pipefail\nHERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"\nexec "$HERE/candidate/OPERATOR_WELLE18.sh" "$@"\n'''
    identity_bytes = (json.dumps(identity, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
    readme = (ROOT / "docs/STABLE_OPERATOR_WELLE18.md").read_bytes()
    output.parent.mkdir(parents=True, exist_ok=True)
    fd, raw = tempfile.mkstemp(prefix=f".{output.name}.", suffix=".tmp", dir=output.parent)
    os.close(fd)
    tmp = Path(raw)
    try:
        with zipfile.ZipFile(tmp, "w") as archive:
            _write(archive, f"{prefix}/RUN_OPERATOR.sh", wrapper, 0o755)
            _write(archive, f"{prefix}/README.md", readme, 0o644)
            _write(archive, f"{prefix}/CANDIDATE_IDENTITY.json", identity_bytes, 0o644)
            for item in sorted(manifest["files"], key=lambda value: value["path"]):
                relative = PurePosixPath(str(item["path"]))
                path = ROOT.joinpath(*relative.parts)
                _write(archive, f"{prefix}/candidate/{relative.as_posix()}", path.read_bytes(), int(str(item["mode"]), 8))
            _write(archive, f"{prefix}/candidate/RELEASE_MANIFEST.json", (ROOT / "RELEASE_MANIFEST.json").read_bytes(), 0o644)
        os.replace(tmp, output)
        os.chmod(output, 0o644)
    finally:
        tmp.unlink(missing_ok=True)
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description="Baut das deterministische Welle-18-Operator-Kit.")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(build(args.output.resolve(strict=False)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
