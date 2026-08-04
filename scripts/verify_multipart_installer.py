#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import stat
import subprocess
import tarfile
from pathlib import Path, PurePosixPath

from ab_contract import ContractError, key_id, validate_manifest


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_signature(file: Path, signature: Path, key: Path) -> None:
    completed = subprocess.run(
        ["openssl", "pkeyutl", "-verify", "-pubin", "-inkey", str(key), "-rawin", "-in", str(file), "-sigfile", str(signature)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if completed.returncode:
        raise SystemExit(f"SIGNATURE_FAILED:{file.name}")


def verify_archive(path: Path, part: dict) -> None:
    with tarfile.open(path, "r:*") as archive:
        members = archive.getmembers()
        if len(members) != int(part["member_count"]):
            raise SystemExit(f"MEMBER_COUNT_FAILED:{path.name}")
        unpacked = 0
        seen: set[str] = set()
        for member in members:
            pure = PurePosixPath(member.name)
            if member.name in seen or member.name.startswith("/") or ".." in pure.parts or "." in pure.parts:
                raise SystemExit("UNSAFE:" + member.name)
            seen.add(member.name)
            if member.issym() or member.islnk() or member.isdev() or member.isfifo() or not (member.isfile() or member.isdir()):
                raise SystemExit("UNSAFE_TYPE:" + member.name)
            if member.mode & (stat.S_ISUID | stat.S_ISGID | stat.S_ISVTX):
                raise SystemExit("UNSAFE_MODE:" + member.name)
            if member.isfile():
                unpacked += member.size
        if unpacked != int(part["unpacked_bytes"]):
            raise SystemExit(f"UNPACKED_SIZE_FAILED:{path.name}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("installer", type=Path)
    options = parser.parse_args()
    root = options.installer.resolve()
    manifest_path = root / "INSTALLER_MANIFEST.json"
    key = root / "VideoBatch_Release_Public_Key.pem"
    verify_signature(manifest_path, root / "INSTALLER_MANIFEST.ed25519", key)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    try:
        validate_manifest(manifest, expected_key_id=key_id(key))
    except ContractError as exc:
        raise SystemExit(f"MANIFEST_CONTRACT_FAILED:{exc}") from exc
    for part in manifest["parts"]:
        file = root / "parts" / part["file"]
        signature = root / "parts" / part["signature_file"]
        verify_signature(file, signature, key)
        if not file.is_file() or file.is_symlink() or file.stat().st_size != part["size"] or sha256(file) != part["sha256"] or file.stat().st_size > manifest["maximum_part_bytes"]:
            raise SystemExit("PART_FAILED:" + part["file"])
        verify_archive(file, part)
    for required in ("autoinstall.sh", "ab_installer.py", "ab_launcher.py", "ab_contract.py"):
        if not (root / required).is_file():
            raise SystemExit("CONTROLLER_MISSING:" + required)
    print(f"INSTALLER_OK version={manifest['version']} sequence={manifest['release_sequence']} release_id={manifest['release_id']} strategy=ab-slots parts={len(manifest['parts'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
