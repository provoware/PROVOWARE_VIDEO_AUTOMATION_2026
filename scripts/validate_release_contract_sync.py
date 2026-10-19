#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from typing import Any, Mapping

from videobatch_fast.versioning import build_label

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "RELEASE_MANIFEST.json"
PACKAGE_MANIFEST_PATH = ROOT / "config/contracts/manifest.json"
EVIDENCE_PATH = ROOT / "diagnostics/release_readiness/RELEASE_EVIDENCE.json"
HISTORICAL_MANIFEST_PATH = ROOT / "diagnostics/release_readiness/HISTORICAL_RC24_RELEASE_MANIFEST.json"
HISTORICAL_MANIFEST_GIT_BLOB = "c9fd5fe01ce9db899bebf9d7ffd1d7cb8829d6f2"
QUALITY_PATH = ROOT / "config/status/QUALITY_ENVIRONMENT_STATUS.json"
BUILD_REPORT_PATH = ROOT / "docs/archive/rc24" / f"VideoBatch_Fast_{build_label()}_BUILD_REPORT_save_.json"
README_PATH = ROOT / "README.md"
STATUS_PATH = ROOT / "docs/STATUS.md"
TODO_PATH = ROOT / "docs/TODO.md"


class ContractSyncError(RuntimeError):
    pass


def _reject_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ContractSyncError(f"Doppelter JSON-Schlüssel {key!r}")
        result[key] = value
    return result


def _load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_reject_duplicate_pairs,
        )
    except (OSError, UnicodeError, json.JSONDecodeError, ContractSyncError) as exc:
        raise ContractSyncError(f"{path.relative_to(ROOT)} ist kein eindeutiges gültiges JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise ContractSyncError(f"{path.relative_to(ROOT)} muss ein JSON-Objekt sein")
    return value


def _mapping(value: object, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ContractSyncError(f"{label} muss ein Objekt sein")
    return value


def _sha256_text(value: object) -> bool:
    text = str(value or "")
    return len(text) == 64 and all(char in "0123456789abcdefABCDEF" for char in text)


def validate(*, phase: str = "integration", acceptance_dir: Path | None = None) -> dict[str, Any]:
    """Integration checks never claim release approval; release checks require real evidence."""
    if phase not in {"integration", "release"}:
        raise ContractSyncError(f"Unbekannte Prüfphase: {phase}")
    manifest = _load(MANIFEST_PATH)
    # The historical release evidence belongs to this pinned RC24 tree, not
    # to the newer integration candidate. Verify the archived Git blob too.
    archived_bytes = HISTORICAL_MANIFEST_PATH.read_bytes()
    object_bytes = b"blob " + str(len(archived_bytes)).encode("ascii") + b"\x00" + archived_bytes
    if hashlib.sha1(object_bytes).hexdigest() != HISTORICAL_MANIFEST_GIT_BLOB:
        raise ContractSyncError("Historisches RC24-Manifest wurde verändert")
    historical_manifest = _load(HISTORICAL_MANIFEST_PATH)
    package_manifest = _load(PACKAGE_MANIFEST_PATH)
    evidence = _load(EVIDENCE_PATH)
    quality = _load(QUALITY_PATH)
    build = _load(BUILD_REPORT_PATH)

    if manifest.get("schema_version") != 3 or manifest.get("representation") != "compact":
        raise ContractSyncError("RELEASE_MANIFEST.json muss Schema 3 in kompakter Darstellung verwenden")
    count = manifest.get("file_count")
    if not isinstance(count, int) or count <= 0:
        raise ContractSyncError("RELEASE_MANIFEST.json enthält keine gültige Dateizahl")
    if not _sha256_text(manifest.get("files_sha256")):
        raise ContractSyncError("RELEASE_MANIFEST.json enthält keinen gültigen files_sha256")

    product = _mapping(evidence.get("product"), "RELEASE_EVIDENCE.product")
    evidence_manifest = _mapping(evidence.get("manifest"), "RELEASE_EVIDENCE.manifest")
    historical_count = historical_manifest.get("file_count")
    if evidence_manifest.get("file_count") != historical_count:
        raise ContractSyncError(
            f"Historischer RC24-Nachweis nennt {evidence_manifest.get('file_count')} statt {historical_count} Dateien"
        )
    if evidence_manifest.get("status") != "passed":
        raise ContractSyncError("RELEASE_EVIDENCE.manifest.status muss passed sein")
    if product.get("version") != manifest.get("version") or product.get("version") != manifest.get("build"):
        raise ContractSyncError("Produktversion und Manifest version/build sind nicht synchron")
    if product.get("channel") != manifest.get("channel"):
        raise ContractSyncError("Release-Kanal in Evidence und Manifest ist nicht synchron")

    if package_manifest.get("schema_version") != 1:
        raise ContractSyncError("config/contracts/manifest.json besitzt eine unbekannte Schema-Version")
    for field in ("name", "version", "channel", "build_date"):
        if package_manifest.get(field) != product.get(field):
            raise ContractSyncError(
                f"config/contracts/manifest.json Feld {field!r} ist nicht mit RELEASE_EVIDENCE.product synchron"
            )
    if package_manifest.get("artifact_policy") != evidence.get("artifact_policy"):
        raise ContractSyncError(
            "config/contracts/manifest.json artifact_policy ist nicht mit RELEASE_EVIDENCE synchron"
        )
    entrypoint = str(package_manifest.get("entrypoint") or "")
    if not entrypoint or not (ROOT / entrypoint).is_file():
        raise ContractSyncError("config/contracts/manifest.json verweist auf keinen gültigen Einstieg")

    internal = _mapping(quality.get("internal_gates"), "QUALITY_ENVIRONMENT_STATUS.internal_gates")
    if internal.get("release_manifest_files") != historical_count:
        raise ContractSyncError("Historischer Qualitätsstatus passt nicht zum RC24-Manifest")
    if build.get("release_manifest_files") != historical_count:
        raise ContractSyncError("Historischer Buildbericht passt nicht zum RC24-Manifest")

    expected_line = f"Release-Manifest: {historical_count} Dateien"
    for path in (README_PATH, STATUS_PATH):
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            raise ContractSyncError(f"{path.name} kann nicht gelesen werden: {exc}") from exc
        if expected_line not in text:
            raise ContractSyncError(f"{path.name} enthält nicht den aktuellen Status: {expected_line}")

    # A development manifest must match the real current file set; historical
    # release results never qualify this new tree for Stable.
    if manifest != historical_manifest:
        try:
            check = subprocess.run(
                [sys.executable, str(ROOT / "scripts/build_release_manifest.py"), "--check"],
                cwd=ROOT, capture_output=True, text=True, timeout=45, check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise ContractSyncError(f"Kanonische Manifestprüfung nicht ausführbar: {exc}") from exc
        if check.returncode != 0:
            raise ContractSyncError(
                "Aktuelles Entwicklungsmanifest stimmt nicht mit dem Dateibaum überein: "
                + (check.stdout + check.stderr)[-800:]
            )
        # PR240 is an immutable *earlier* candidate snapshot. Check its
        # provenance, never require its digest or approval flags for this tree.
        legacy_evidence = _load(ROOT / "diagnostics/release_readiness/CANDIDATE_PR240_CI_EVIDENCE.json")
        legacy_status = _load(ROOT / "diagnostics/release_readiness/CANDIDATE_PR240_QUALITY_STATUS.json")
        if legacy_status.get("manifest") != legacy_evidence.get("source_release_manifest"):
            raise ContractSyncError("Archivierter PR240-Kandidatenbericht passt nicht zu seinem Ursprung")
        if legacy_status.get("candidate_commit") != legacy_evidence.get("source_commit"):
            raise ContractSyncError("Archivierter PR240-Kandidatenbericht hat einen fremden Commit")
        if legacy_status.get("release_approved") is not False:
            raise ContractSyncError("Historische CI darf keine nachträgliche Stable-Freigabe behaupten")

    if phase == "release":
        if acceptance_dir is None:
            raise ContractSyncError("Release-Endabnahme benötigt einen ausdrücklich gewählten Nachweisordner")
        # Only the final, unchanged candidate may pass this manual gate.
        from validate_stable_acceptance import AcceptanceBlocked, manifest_sha256, validate_evidence

        try:
            validate_evidence(
                acceptance_dir,
                str(manifest.get("version")),
                manifest_sha256(MANIFEST_PATH),
            )
        except AcceptanceBlocked as exc:
            raise ContractSyncError(f"Reale Release-Endabnahme fehlt: {exc}") from exc

    todo = TODO_PATH.read_text(encoding="utf-8")
    if "P0 – vor Merge von PR #128" in todo or "P0 - vor Merge von PR #128" in todo:
        raise ContractSyncError("docs/TODO.md enthält noch den überholten Vor-Merge-Abschnitt für PR #128")

    # HEAD comes from the actual checkout: no self-referential commit SHA in
    # tracked release files. CI logs provide an audit trail for this exact tree.
    try:
        revision = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT, capture_output=True, text=True, timeout=10, check=True,
        ).stdout.strip()
    except (OSError, subprocess.TimeoutExpired, subprocess.CalledProcessError):
        revision = None
    return {
        "schema_version": 1,
        "status": "passed",
        "phase": phase,
        "checked_commit": revision,
        "manual_release_acceptance": "verified" if phase == "release" else "not_checked",
        "release_approved": False,
        "version": manifest.get("version"),
        "channel": manifest.get("channel"),
        "manifest_files": count,
        "manifest_files_sha256": manifest.get("files_sha256"),
        "stable_ready": bool(evidence.get("stable_ready")),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Prüft Manifest, Release-Evidence und abgeleitete Statusdateien auf Drift.")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--phase", choices=("integration", "release"), default="integration")
    parser.add_argument("--acceptance-dir", type=Path)
    args = parser.parse_args()
    try:
        result = validate(phase=args.phase, acceptance_dir=args.acceptance_dir)
    except (ContractSyncError, OSError) as exc:
        if args.json:
            print(json.dumps({"schema_version": 1, "status": "failed", "error": str(exc)}, ensure_ascii=False, indent=2, sort_keys=True))
        else:
            print(f"RELEASE-CONTRACT-DRIFT: {exc}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(
            f"RELEASE-CONTRACT BESTANDEN · {result['version']} · "
            f"{result['manifest_files']} Dateien · Stable={result['stable_ready']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
