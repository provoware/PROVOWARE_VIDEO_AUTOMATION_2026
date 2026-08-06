from __future__ import annotations

import hashlib
import importlib.util
import json
import re
from pathlib import Path
from typing import Any, Mapping

import engine_legacy as _legacy
from engine_legacy import *  # noqa: F403

_LEGACY_VALIDATE_MANIFEST = _legacy.validate_manifest


def _release_file_selector(root: Path):
    module_path = root / "scripts" / "release_file_contract.py"
    spec = importlib.util.spec_from_file_location("release_file_contract", module_path)
    if spec is None or spec.loader is None:
        raise EvidenceError(f"Release-Dateivertrag kann nicht geladen werden: {module_path}")  # noqa: F405
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    selector = getattr(module, "included_release_file", None)
    if not callable(selector):
        raise EvidenceError("Release-Dateivertrag enthält included_release_file nicht")  # noqa: F405
    return selector


def _compact_manifest_snapshot(root: Path) -> tuple[int, str]:
    selector = _release_file_selector(root)
    records = []
    for path in sorted(root.rglob("*")):
        if selector(root, path):
            records.append(
                {
                    "mode": oct(path.stat().st_mode & 0o777),
                    "path": path.relative_to(root).as_posix(),
                    "sha256": sha256_file(path),  # noqa: F405
                    "size": path.stat().st_size,
                }
            )
    encoded = json.dumps(
        records,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return len(records), hashlib.sha256(encoded).hexdigest()


def validate_manifest(root: Path, manifest: Mapping[str, Any], findings: list[Finding]) -> bool:  # noqa: F405
    if manifest.get("representation") != "compact":
        return _LEGACY_VALIDATE_MANIFEST(root, manifest, findings)
    try:
        actual_count, actual_digest = _compact_manifest_snapshot(root)
    except EvidenceError as exc:  # noqa: F405
        findings.append(Finding("error", "MANIFEST_COMPACT_INVALID", str(exc), ("manifest",)))  # noqa: F405
        return False
    valid = True
    if integer(manifest, "file_count") != actual_count:  # noqa: F405
        findings.append(
            Finding(  # noqa: F405
                "error",
                "MANIFEST_SELF_COUNT_MISMATCH",
                f"Kompaktmanifest nennt {integer(manifest, 'file_count')} Dateien, ermittelt wurden {actual_count}.",  # noqa: F405
                ("manifest",),
            )
        )
        valid = False
    if str(manifest.get("files_sha256") or "") != actual_digest:
        findings.append(
            Finding(  # noqa: F405
                "error",
                "MANIFEST_AGGREGATE_HASH_MISMATCH",
                "Kanonischer Gesamt-SHA-256 der Release-Dateien stimmt nicht.",
                ("manifest",),
            )
        )
        valid = False
    return valid


def readme_release_status(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    version_match = re.search(
        r"^# .+? · ([0-9]+\.[0-9]+\.[0-9]+-rc[0-9]+)\s*$",
        text,
        flags=re.IGNORECASE | re.MULTILINE,
    )
    test_match = re.search(r"([0-9]+)/([0-9]+) automatisierte Tests bestanden", text)
    manifest_match = re.search(r"Release-Manifest:\s*([0-9]+)\s+Dateien", text)
    blocker_section = re.search(
        r"### Offene Stable-Gates\s*(.*?)(?:<!-- release-status:end -->|\Z)",
        text,
        flags=re.DOTALL,
    )
    blockers = []
    if blocker_section:
        blockers = [
            match.group(1).strip()
            for match in re.finditer(
                r"^-\s+([^:\n]+):",
                blocker_section.group(1),
                flags=re.MULTILINE,
            )
        ]
    return {
        "version": version_match.group(1) if version_match else None,
        "tests_passed": int(test_match.group(1)) if test_match else None,
        "manifest_files": int(manifest_match.group(1)) if manifest_match else None,
        "blockers": blockers,
    }


def analyze(
    root: Path,
    documents: Mapping[str, Mapping[str, Any]],
    ci: Mapping[str, Any],
) -> tuple[list[Finding], list[Gate]]:  # noqa: F405
    normalized = dict(documents)
    development = dict(documents["development"])
    blockers = development.get("stable_blockers")
    if isinstance(blockers, list):
        development["stable_blockers"] = [
            str(item).split(":", 1)[0].strip() for item in blockers
        ]
    normalized["development"] = development
    _legacy.validate_manifest = validate_manifest
    _legacy.readme_release_status = readme_release_status
    return _legacy.analyze(root, normalized, ci)
