#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

from ab_contract import ContractError, key_id, validate_channel_index, validate_manifest


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify(file: Path, signature: Path, key: Path) -> None:
    result = subprocess.run(
        ["openssl", "pkeyutl", "-verify", "-pubin", "-inkey", str(key), "-rawin", "-in", str(file), "-sigfile", str(signature)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if result.returncode:
        raise SystemExit(f"SIGNATURE_FAILED:{file.name}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("repository", type=Path)
    options = parser.parse_args()
    root = options.repository.resolve()
    for path in root.rglob("*"):
        if path.is_symlink():
            raise SystemExit(f"UNSAFE_SYMLINK:{path.relative_to(root)}")
        if path.is_file() and "private" in path.name.lower() and "key" in path.name.lower():
            raise SystemExit(f"PRIVATE_KEY_MATERIAL:{path.name}")
    key = root / "VideoBatch_Release_Public_Key.pem"
    index_path = root / "channel-index.json"
    verify(index_path, root / "channel-index.ed25519", key)
    index = json.loads(index_path.read_text(encoding="utf-8"))
    try:
        validate_channel_index(index, expected_key_id=key_id(key))
    except ContractError as exc:
        raise SystemExit(f"CHANNEL_CONTRACT_FAILED:{exc}") from exc
    checked = 0
    for channel, entry in index["channels"].items():
        if not entry.get("available"):
            continue
        manifest = root / entry["manifest_url"]
        signature = root / entry["manifest_signature_url"]
        verify(manifest, signature, key)
        if manifest.stat().st_size != entry["manifest_size"] or sha256(manifest) != entry["manifest_sha256"]:
            raise SystemExit(f"MANIFEST_HASH_FAILED:{channel}")
        payload = json.loads(manifest.read_text(encoding="utf-8"))
        try:
            validate_manifest(payload, expected_key_id=key_id(key))
        except ContractError as exc:
            raise SystemExit(f"MANIFEST_CONTRACT_FAILED:{channel}:{exc}") from exc
        if payload["version"] != entry["version"] or payload["release_sequence"] != entry["release_sequence"] or payload["release_id"] != entry["release_id"]:
            raise SystemExit(f"CHANNEL_MISMATCH:{channel}")
        for part in payload["parts"]:
            file = manifest.parent / part["url"]
            signature = manifest.parent / part["signature_url"]
            verify(file, signature, key)
            if file.stat().st_size != part["size"] or sha256(file) != part["sha256"]:
                raise SystemExit(f"PART_FAILED:{part['file']}")
            checked += 1
    print(f"CHANNEL_REPOSITORY_OK generation={index['generation']} parts={checked}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
