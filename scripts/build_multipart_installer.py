#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import gzip
import hashlib
import json
import os
import shutil
import subprocess
import tarfile
from pathlib import Path, PurePosixPath
from typing import Iterable

from ab_contract import COMPONENTS, MAX_PART_BYTES_HARD, canonical_json, key_id, validate_manifest

FIXED_MTIME = 1767225600
FIXED_CREATED_UTC = "2026-08-03T20:00:00Z"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def safe_rel(path: Path, root: Path) -> str:
    relative = path.relative_to(root).as_posix()
    pure = PurePosixPath(relative)
    if relative.startswith("/") or ".." in pure.parts:
        raise ValueError(f"Ungültiger Pfad: {relative}")
    return relative


def file_record(path: Path, root: Path) -> dict[str, object]:
    mode = path.stat().st_mode & 0o777
    if mode not in {0o644, 0o755}:
        mode = 0o755 if mode & 0o111 else 0o644
    return {"path": safe_rel(path, root), "size": path.stat().st_size, "sha256": sha256(path), "mode": oct(mode)}


def tree_records(paths: Iterable[Path], root: Path) -> list[dict[str, object]]:
    files: list[dict[str, object]] = []
    for base in paths:
        if base.is_file() and not base.is_symlink():
            files.append(file_record(base, root))
        elif base.is_dir() and not base.is_symlink():
            files.extend(file_record(path, root) for path in sorted(base.rglob("*")) if path.is_file() and not path.is_symlink())
    unique = {str(item["path"]): item for item in files}
    return [unique[name] for name in sorted(unique)]


def tree_hash(records: list[dict[str, object]]) -> str:
    digest = hashlib.sha256()
    for record in records:
        digest.update(f"{record['path']}\0{record['mode']}\0{record['size']}\0{record['sha256']}\n".encode())
    return digest.hexdigest()


def tar_filter(info: tarfile.TarInfo) -> tarfile.TarInfo:
    info.uid = info.gid = 0
    info.uname = info.gname = ""
    info.mtime = FIXED_MTIME
    info.mode = 0o755 if info.mode & 0o111 else 0o644
    return info


def write_tar(root: Path, files: list[Path], target: Path) -> None:
    with target.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, compresslevel=6, mtime=0) as compressed:
            with tarfile.open(fileobj=compressed, mode="w") as archive:
                for path in sorted(files, key=lambda candidate: safe_rel(candidate, root)):
                    archive.add(path, arcname=safe_rel(path, root), recursive=False, filter=tar_filter)


def archive_stats(path: Path) -> tuple[int, int]:
    with tarfile.open(path, "r:*") as archive:
        members = archive.getmembers()
        return len(members), sum(member.size for member in members if member.isfile())


def expand_files(items: list[Path]) -> list[Path]:
    output: list[Path] = []
    for item in items:
        if item.is_file() and not item.is_symlink():
            output.append(item)
        elif item.is_dir() and not item.is_symlink():
            output.extend(path for path in item.rglob("*") if path.is_file() and not path.is_symlink())
    return sorted(set(output))


def split_to_limit(root: Path, files: list[Path], output: Path, stem: str, limit: int) -> list[Path]:
    queue = [files]
    result: list[Path] = []
    index = 1
    while queue:
        group = queue.pop(0)
        target = output / f"{stem}-{index:02d}.tar.gz"
        write_tar(root, group, target)
        if target.stat().st_size <= limit:
            result.append(target)
            index += 1
            continue
        target.unlink()
        if len(group) < 2:
            raise RuntimeError(f"Einzeldatei überschreitet Teilgrenze: {group[0]}")
        total = sum(path.stat().st_size for path in group)
        accumulated = 0
        cut = 1
        for position, path in enumerate(group, 1):
            accumulated += path.stat().st_size
            if accumulated >= total / 2:
                cut = position
                break
        queue.insert(0, group[cut:])
        queue.insert(0, group[:cut])
    return result


def raw_sign(path: Path, private_key: Path, target: Path) -> None:
    completed = subprocess.run(
        ["openssl", "pkeyutl", "-sign", "-rawin", "-inkey", str(private_key), "-in", str(path), "-out", str(target)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if completed.returncode:
        raise RuntimeError(completed.stderr.strip() or "OpenSSL-Signierung fehlgeschlagen.")


def json_sign(path: Path, private_key: Path, target: Path) -> None:
    from cryptography.hazmat.primitives import serialization

    private = serialization.load_pem_private_key(private_key.read_bytes(), password=None)
    public = private.public_key()
    raw = public.public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    payload = {
        "schema_version": 1,
        "algorithm": "ed25519",
        "role": "installer-artifact",
        "file_name": path.name,
        "size": path.stat().st_size,
        "sha256": sha256(path),
        "key_id": hashlib.sha256(raw).hexdigest()[:24],
    }
    canonical = canonical_json(payload)
    target.write_text(
        json.dumps({"payload": payload, "signature_base64": base64.b64encode(private.sign(canonical)).decode()}, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Baut signierte, nummerierte VideoBatch-Teilpakete.")
    parser.add_argument("--appdir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--private-key", type=Path, required=True)
    parser.add_argument("--public-key", type=Path, required=True)
    parser.add_argument("--max-part-mb", type=int, default=30)
    parser.add_argument("--mode", choices=("full", "partial"), default="full")
    parser.add_argument("--release-sequence", type=int, required=True)
    parser.add_argument("--components", default="bootstrap,application,runtime,media,desktop")
    options = parser.parse_args()

    root = options.appdir.resolve()
    output = options.output_dir.resolve()
    limit = options.max_part_mb * 1024 * 1024
    if limit > MAX_PART_BYTES_HARD:
        raise RuntimeError("Die harte Teilpaketgrenze von 30 MB darf nicht überschritten werden.")
    if output.exists():
        shutil.rmtree(output)
    parts_dir = output / "parts"
    parts_dir.mkdir(parents=True)
    shutil.copy2(options.public_key, output / "VideoBatch_Release_Public_Key.pem")
    signing_key_id = key_id(options.public_key)

    selected = {item.strip() for item in options.components.split(",") if item.strip()}
    if not selected <= set(COMPONENTS):
        raise RuntimeError("Unbekannte Komponente wurde angefordert.")
    selected.add("bootstrap")
    groups = {
        "bootstrap": [root / "AppRun", root / ".DirIcon", root / "PORTABLE_RUNTIME_MANIFEST.json", root / "videobatch-fast.desktop", root / "videobatch-fast.svg"],
        "application": [root / "usr/app"],
        "runtime-core": [root / "usr/runtime/bin", root / "usr/runtime/share"],
        "runtime-native": [path for path in (root / "usr/runtime/lib").iterdir() if path.is_file()],
        "runtime-python": [root / "usr/runtime/lib/python3.13"],
        "media": [root / "usr/media"],
        "desktop": [root / "usr/share"],
    }
    component_groups = {
        "bootstrap": ["bootstrap"],
        "application": ["application"],
        "runtime": ["runtime-core", "runtime-native", "runtime-python"],
        "media": ["media"],
        "desktop": ["desktop"],
    }
    all_paths = {
        "bootstrap": groups["bootstrap"],
        "application": [root / "usr/app"],
        "runtime": [root / "usr/runtime"],
        "media": [root / "usr/media"],
        "desktop": [root / "usr/share"],
    }
    install_paths = {"bootstrap": ".", "application": "usr/app", "runtime": "usr/runtime", "media": "usr/media", "desktop": "usr/share"}
    components: dict[str, dict[str, object]] = {}
    total_file_count = 0
    total_unpacked_bytes = 0
    for component_id in COMPONENTS:
        records = tree_records(all_paths[component_id], root)
        components[component_id] = {
            "version": options.version,
            "tree_sha256": tree_hash(records),
            "file_count": len(records),
            "files": records,
            "install_path": install_paths[component_id],
            "included": component_id in selected,
        }
        total_file_count += len(records)
        total_unpacked_bytes += sum(int(record["size"]) for record in records)

    entries: list[dict[str, object]] = []
    sequence = 1
    for component_id in COMPONENTS:
        if component_id not in selected:
            continue
        for group_name in component_groups[component_id]:
            files = expand_files(groups[group_name])
            archives = split_to_limit(root, files, parts_dir, f"part-{sequence:03d}-{group_name}", limit)
            for archive in archives:
                final = parts_dir / f"VideoBatchFast-Part-{sequence:03d}-{group_name.title().replace('-', '')}.tar.gz"
                archive.rename(final)
                member_count, unpacked_bytes = archive_stats(final)
                entry = {
                    "number": sequence,
                    "component": component_id,
                    "group": group_name,
                    "file": final.name,
                    "size": final.stat().st_size,
                    "unpacked_bytes": unpacked_bytes,
                    "member_count": member_count,
                    "sha256": sha256(final),
                    "required": True,
                    "signature_file": final.name + ".ed25519",
                    "url": "parts/" + final.name,
                    "signature_url": "parts/" + final.name + ".ed25519",
                }
                entries.append(entry)
                json_sign(final, options.private_key, final.with_name(final.name + ".sig.json"))
                raw_sign(final, options.private_key, final.with_name(final.name + ".ed25519"))
                sequence += 1

    release_identity = {
        "product": "VideoBatch Fast",
        "version": options.version,
        "release_sequence": options.release_sequence,
        "signing_key_id": signing_key_id,
        "components": {component_id: components[component_id]["tree_sha256"] for component_id in COMPONENTS},
        "parts": [{"number": entry["number"], "sha256": entry["sha256"]} for entry in entries],
    }
    release_id = hashlib.sha256(canonical_json(release_identity)).hexdigest()
    manifest = {
        "schema_version": 2,
        "product": "VideoBatch Fast",
        "version": options.version,
        "build": options.version,
        "release_sequence": options.release_sequence,
        "release_id": release_id,
        "signing_key_id": signing_key_id,
        "mode": options.mode,
        "created_utc": FIXED_CREATED_UTC,
        "default_install_root": "~/.local/share/VideoBatchFast",
        "maximum_part_bytes": limit,
        "part_count": len(entries),
        "total_file_count": total_file_count,
        "total_unpacked_bytes": total_unpacked_bytes,
        "installation_layout": {"strategy": "ab-slots", "slots": ["A", "B"], "active_link": "current", "controller": "controller", "slot_manifests": "slot_manifests"},
        "update_order": list(COMPONENTS),
        "parts": entries,
        "components": components,
        "user_data_paths": ["~/.config/VideoBatchFast", "~/.local/state/VideoBatchFast", "~/.cache/VideoBatchFast", "~/Videos"],
        "policy": {
            "active_slot_is_immutable": True,
            "build_in_inactive_slot": True,
            "atomic_symlink_switch": True,
            "boot_confirmation_required": True,
            "automatic_boot_rollback": True,
            "keep_two_complete_slots": True,
            "monotonic_release_sequence": True,
            "immutable_release_identity": True,
            "full_slot_manifest_required": True,
            "archive_expansion_limits_required": True,
            "disk_preflight_required": True,
            "unchanged_components_must_match": True,
            "allow_downgrade_by_default": False,
            "launch_after_success": True,
        },
    }
    validate_manifest(manifest, expected_key_id=signing_key_id)
    manifest_path = output / "INSTALLER_MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    raw_sign(manifest_path, options.private_key, output / "INSTALLER_MANIFEST.ed25519")
    json_sign(manifest_path, options.private_key, output / "INSTALLER_MANIFEST.json.sig.json")

    source_root = Path(__file__).resolve().parents[1]
    for name in ("autoinstall.sh",):
        shutil.copy2(source_root / name, output / name)
        os.chmod(output / name, 0o755)
    for name in ("ab_installer.py", "ab_launcher.py", "ab_contract.py"):
        shutil.copy2(source_root / "scripts" / name, output / name)
        os.chmod(output / name, 0o755)
    shutil.copy2(source_root / "AUTOINSTALLATION_save_.md", output / "LIES_MICH_INSTALLATION.md")
    report = {
        "status": "passed",
        "version": options.version,
        "release_sequence": options.release_sequence,
        "release_id": release_id,
        "signing_key_id": signing_key_id,
        "strategy": "ab-slots",
        "part_count": len(entries),
        "largest_part_bytes": max(int(entry["size"]) for entry in entries),
        "max_part_bytes": limit,
        "total_file_count": total_file_count,
        "total_unpacked_bytes": total_unpacked_bytes,
        "manifest_sha256": sha256(manifest_path),
        "output": "VideoBatch_Fast_Installer",
    }
    (output / "INSTALLER_BUILD_REPORT.json").write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
