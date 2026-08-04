#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import time
import zipfile
from pathlib import Path

from videobatch_fast.visual_approval import (
    approval_fingerprint,
    baseline_bundle_hash,
    inspection_manifest_hash,
    verify_visual_approval,
)

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED_PARTS = {
    "__pycache__",
    ".pytest_cache",
    ".git",
    ".venv",
    ".quality-venv",
    ".quality-toolchain-backups",
    "build",
    "dist",
    "quarantine",
    "keys",
    "visual_actual",
    "diagnostics",
    "actual",
    "diff",
}
EXCLUDED_SUFFIXES = {".pyc", ".pyo", ".pvak"}
FIXED_ZIP_TIME = (2026, 1, 1, 0, 0, 0)


def _included(path: Path, root: Path) -> bool:
    rel = path.relative_to(root)
    return (
        path.is_file()
        and not path.is_symlink()
        and path.suffix not in EXCLUDED_SUFFIXES
        and not any(part in EXCLUDED_PARTS for part in rel.parts)
    )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _version(root: Path) -> dict:
    value = json.loads((root / "VERSION.json").read_text(encoding="utf-8"))
    if not isinstance(value, dict) or not value.get("version"):
        raise SystemExit(f"VERSION.json ist ungültig: {root}")
    return value


def _zip_write_bytes(archive: zipfile.ZipFile, name: str, data: bytes, mode: int = 0o644) -> None:
    info = zipfile.ZipInfo(name, FIXED_ZIP_TIME)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.create_system = 3
    info.external_attr = (stat.S_IFREG | (mode & 0o777)) << 16
    archive.writestr(info, data, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)


def main() -> int:
    parser = argparse.ArgumentParser(description="Erzeugt ein reproduzierbares Stable-Update mit visueller Bindung.")
    parser.add_argument("--from-root", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--from-version")
    args = parser.parse_args()

    source = args.from_root.resolve()
    target = ROOT.resolve()
    if not source.is_dir():
        raise SystemExit("Ausgangsordner fehlt.")
    target_version = _version(target)
    source_version = _version(source)
    from_version = args.from_version or str(source_version["version"])
    if from_version != str(source_version["version"]):
        raise SystemExit("--from-version stimmt nicht mit VERSION.json des Ausgangsstands überein.")
    if str(target_version.get("channel")) != "stable":
        raise SystemExit("Stable-Update kann nur aus einem als stable markierten Zielstand erzeugt werden.")
    output = args.output or target.parent / (
        f"provoware_videoautomation_{target_version['version']}_update_from_{from_version}.zip"
    )

    visual_path = target / "VISUAL_INSPECTION_MANIFEST.json"
    visual = json.loads(visual_path.read_text(encoding="utf-8"))
    approval = verify_visual_approval(visual, target)
    if not approval.valid:
        raise SystemExit(f"Visuelle Freigabe ist nicht gültig: {approval.message}")

    source_files = {path.relative_to(source).as_posix(): path for path in source.rglob("*") if _included(path, source)}
    target_files = {path.relative_to(target).as_posix(): path for path in target.rglob("*") if _included(path, target)}
    changed: list[tuple[str, Path, str]] = []
    for rel, path in sorted(target_files.items()):
        previous = source_files.get(rel)
        operation = "add" if previous is None else "replace"
        if previous is None or previous.stat().st_size != path.stat().st_size or _sha256(previous) != _sha256(path):
            changed.append((rel, path, operation))
    deleted = sorted(set(source_files) - set(target_files))
    if "VISUAL_INSPECTION_MANIFEST.json" not in {rel for rel, _, _ in changed}:
        changed.append(("VISUAL_INSPECTION_MANIFEST.json", visual_path, "replace" if visual_path.exists() else "add"))
    changed.sort(key=lambda item: item[0])

    release_manifest = target / "RELEASE_MANIFEST.json"
    visual_binding = {
        "build_id": str(target_version.get("build", target_version["version"])),
        "visual_contract_sha256": inspection_manifest_hash(visual),
        "baseline_bundle_sha256": baseline_bundle_hash(visual, target),
        "approval_sha256": approval_fingerprint(visual),
        "approval_key_id": approval.key_id,
        "reviewer": approval.reviewer,
        "approved_at": approval.approved_at,
    }
    files = [
        {
            "path": rel,
            "operation": operation,
            "sha256": _sha256(path),
            "size": path.stat().st_size,
            "mode": oct(path.stat().st_mode & 0o777),
        }
        for rel, path, operation in changed
    ]
    files.extend({"path": rel, "operation": "delete"} for rel in deleted)
    manifest = {
        "schema_version": 3,
        "name": str(target_version.get("name", "provoware - videoautomation - 2026")),
        "version": str(target_version["version"]),
        "build": str(target_version.get("build", target_version["version"])),
        "channel": "stable",
        "compatible_from": [from_version],
        "visual_approval": visual_binding,
        "release_manifest_sha256": _sha256(release_manifest) if release_manifest.is_file() else "",
        "files": files,
    }
    manifest_bytes = (json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w") as archive:
        _zip_write_bytes(archive, "update_manifest.json", manifest_bytes)
        for rel, path, _operation in changed:
            _zip_write_bytes(archive, rel, path.read_bytes(), path.stat().st_mode & 0o777)
    os.chmod(output, 0o644)
    manifest_copy = target / "STABLE_UPDATE_MANIFEST.json"
    manifest_copy.write_bytes(manifest_bytes)
    print(f"STABLE-UPDATE ERZEUGT · {len(changed)} Nutzdateien · {len(deleted)} Löschungen · {output}")
    print(f"VISUELLER VERTRAG · {visual_binding['visual_contract_sha256']}")
    print(f"ABNAHMEHASH · {visual_binding['approval_sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
