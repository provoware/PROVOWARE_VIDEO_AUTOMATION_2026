#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

from ab_contract import key_id, validate_channel_index

FIXED_CREATED_UTC = "2026-08-03T20:00:00Z"
FIXED_EXPIRES_UTC = "2026-11-01T20:45:00Z"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def raw_sign(path: Path, private_key: Path, target: Path) -> None:
    completed = subprocess.run(
        ["openssl", "pkeyutl", "-sign", "-rawin", "-inkey", str(private_key), "-in", str(path), "-out", str(target)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if completed.returncode:
        raise RuntimeError(completed.stderr.strip() or "Ed25519-Signierung fehlgeschlagen.")


def verify_signature(path: Path, signature: Path, public_key: Path) -> None:
    completed = subprocess.run(
        ["openssl", "pkeyutl", "-verify", "-pubin", "-inkey", str(public_key), "-rawin", "-in", str(path), "-sigfile", str(signature)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode:
        raise RuntimeError(f"Basiskanal besitzt eine ungültige Signatur: {path.name}")


def load_base(base: Path | None, public_key: Path) -> tuple[dict, int]:
    channels = {"stable": {"available": False}, "rc": {"available": False}}
    generation = 0
    if base is None:
        return channels, generation
    index_path = base / "channel-index.json"
    signature = base / "channel-index.ed25519"
    verify_signature(index_path, signature, public_key)
    payload = json.loads(index_path.read_text(encoding="utf-8"))
    validate_channel_index(payload, expected_key_id=key_id(public_key))
    channels = payload["channels"]
    generation = int(payload["generation"])
    return channels, generation


def main() -> int:
    parser = argparse.ArgumentParser(description="Baut ein statisch hostbares, signiertes VideoBatch-Channel-Verzeichnis.")
    parser.add_argument("--installer-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--private-key", type=Path, required=True)
    parser.add_argument("--public-key", type=Path, required=True)
    parser.add_argument("--channel", choices=("stable", "rc"), required=True)
    parser.add_argument("--minimum-version", default="0.0.0")
    parser.add_argument("--base-repository", type=Path)
    parser.add_argument("--generation", type=int)
    options = parser.parse_args()

    installer = options.installer_dir.resolve()
    output = options.output_dir.resolve()
    base = options.base_repository.resolve() if options.base_repository else None
    manifest_path = installer / "INSTALLER_MANIFEST.json"
    signature_path = installer / "INSTALLER_MANIFEST.ed25519"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    version = str(manifest["version"])
    sequence = int(manifest["release_sequence"])
    signing_key_id = key_id(options.public_key)
    channels, old_generation = load_base(base, options.public_key)
    generation = options.generation if options.generation is not None else old_generation + 1
    if generation <= old_generation:
        raise RuntimeError("Neue Channel-Generation muss größer als die Basiskanal-Generation sein.")

    temporary = output.with_name(f".{output.name}.stage")
    if temporary.exists():
        shutil.rmtree(temporary)
    if base:
        links = [path for path in base.rglob("*") if path.is_symlink()]
        if links:
            raise RuntimeError(f"Basiskanal enthält einen nicht zugelassenen Symlink: {links[0]}")
        private_material = [path for path in base.rglob("*") if path.is_file() and "private" in path.name.lower() and "key" in path.name.lower()]
        if private_material:
            raise RuntimeError(f"Basiskanal enthält mögliches privates Schlüsselmaterial: {private_material[0].name}")
        shutil.copytree(base, temporary, symlinks=False)
    else:
        temporary.mkdir(parents=True)
    release_root = temporary / "releases" / version
    if release_root.exists():
        shutil.rmtree(release_root)
    parts_out = release_root / "parts"
    parts_out.mkdir(parents=True)
    shutil.copy2(manifest_path, release_root / manifest_path.name)
    shutil.copy2(signature_path, release_root / signature_path.name)
    shutil.copy2(options.public_key, temporary / "VideoBatch_Release_Public_Key.pem")

    component_bytes: dict[str, int] = {name: 0 for name in manifest["components"]}
    for part in manifest["parts"]:
        for name in (part["file"], part["signature_file"]):
            shutil.copy2(installer / "parts" / name, parts_out / name)
        component_bytes[str(part["component"])] += int(part["size"])

    release_entry = {
        "available": True,
        "version": version,
        "release_sequence": sequence,
        "release_id": manifest["release_id"],
        "minimum_installed_version": options.minimum_version,
        "minimum_installer_schema": 2,
        "manifest_url": f"releases/{version}/INSTALLER_MANIFEST.json",
        "manifest_signature_url": f"releases/{version}/INSTALLER_MANIFEST.ed25519",
        "manifest_size": manifest_path.stat().st_size,
        "manifest_sha256": sha256(manifest_path),
        "update_order": manifest["update_order"],
        "components": {
            component_id: {
                "version": component["version"],
                "tree_sha256": component["tree_sha256"],
                "download_bytes": component_bytes[component_id],
                "included": bool(component["included"]),
                "requires": manifest["update_order"][: manifest["update_order"].index(component_id)],
            }
            for component_id, component in manifest["components"].items()
        },
    }
    channels[options.channel] = release_entry
    index = {
        "schema_version": 1,
        "product": "VideoBatch Fast",
        "generation": generation,
        "created_utc": FIXED_CREATED_UTC,
        "expires_utc": FIXED_EXPIRES_UTC,
        "signature_algorithm": "ed25519",
        "signing_key_id": signing_key_id,
        "relative_urls": True,
        "channels": channels,
        "policy": {
            "https_required_for_remote_sources": True,
            "same_origin_redirects_only": True,
            "file_urls_allowed_for_offline_testing": True,
            "index_expiry_required": True,
            "index_generation_must_increase": True,
            "manifest_signature_required": True,
            "component_part_signatures_required": True,
            "monotonic_release_sequence_required": True,
            "immutable_release_identity_required": True,
            "download_only_changed_components": True,
            "required_update_order_enforced": True,
        },
    }
    validate_channel_index(index, expected_key_id=signing_key_id)
    index_path = temporary / "channel-index.json"
    index_path.write_text(json.dumps(index, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    raw_sign(index_path, options.private_key, temporary / "channel-index.ed25519")
    report = {
        "status": "passed",
        "channel": options.channel,
        "version": version,
        "release_sequence": sequence,
        "release_id": manifest["release_id"],
        "generation": generation,
        "expires_utc": FIXED_EXPIRES_UTC,
        "index_sha256": sha256(index_path),
        "release_directory": f"releases/{version}",
        "part_count": len(manifest["parts"]),
    }
    (temporary / "CHANNEL_BUILD_REPORT.json").write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if output.exists():
        shutil.rmtree(output)
    temporary.replace(output)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
