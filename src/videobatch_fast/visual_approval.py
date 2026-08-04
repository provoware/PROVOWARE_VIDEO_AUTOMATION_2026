from __future__ import annotations

import base64
import hashlib
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

from .paths import ensure_app_dirs, state_dir
from .registry import PROJECT_ROOT
from .safe_io import atomic_write_bytes, atomic_write_json

APPROVAL_SCHEMA_VERSION = 2


@dataclass(frozen=True, slots=True)
class VisualApprovalCheck:
    valid: bool
    status: str
    message: str
    key_id: str = ""
    reviewer: str = ""
    approved_at: str = ""
    contract_sha256: str = ""


def _canonical_json(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _scenario_artifact(item: dict[str, Any], name: str) -> str:
    artifacts = item.get("artifacts")
    if isinstance(artifacts, dict):
        return str(artifacts.get(name, ""))
    return str(item.get(name, ""))


def normalized_visual_contract(manifest: dict[str, Any]) -> dict[str, Any]:
    """Return the deterministic approval contract.

    Runtime paths, timestamps, comparison metrics, generated messages and current
    screenshot locations are intentionally excluded. The approval remains bound
    to the declared UI contract, pass/fail state and baseline bundle hashes.
    """
    summary = manifest.get("summary", {}) if isinstance(manifest.get("summary"), dict) else {}
    scenarios: list[dict[str, Any]] = []
    for item in sorted(
        (entry for entry in manifest.get("scenarios", []) if isinstance(entry, dict)),
        key=lambda entry: str(entry.get("id", "")),
    ):
        scenarios.append({
            "id": str(item.get("id", "")),
            "group": str(item.get("group", "")),
            "page": str(item.get("page", "")),
            "state": str(item.get("state", "")),
            "width": int(item.get("width", 0) or 0),
            "height": int(item.get("height", 0) or 0),
            "font_scale": int(item.get("font_scale", 100) or 100),
            "required_visible_texts": [str(value) for value in item.get("required_visible_texts", [])],
            "required_semantic_colors": [str(value).lower() for value in item.get("required_semantic_colors", [])],
            "passed": bool(item.get("passed", False)),
        })
    policy = manifest.get("policy", {}) if isinstance(manifest.get("policy"), dict) else {}
    stable_policy = {
        key: policy[key]
        for key in sorted(policy)
        if key not in {"last_capture_at", "generated_at", "absolute_output_path"}
    }
    return {
        "schema_version": int(manifest.get("schema_version", 1) or 1),
        "id": str(manifest.get("id", "")),
        "version": str(manifest.get("version", "")),
        "passed": bool(manifest.get("passed", False)),
        "summary": {
            "scenario_count": int(summary.get("scenario_count", 0) or 0),
            "passed_count": int(summary.get("passed_count", 0) or 0),
            "failed_count": int(summary.get("failed_count", 0) or 0),
            "contract_error_count": int(summary.get("contract_error_count", 0) or 0),
        },
        "contract_errors": [str(value) for value in manifest.get("contract_errors", [])],
        "policy": stable_policy,
        "scenarios": scenarios,
    }


def inspection_manifest_hash(manifest: dict[str, Any]) -> str:
    """Stable contract hash retained under the historical API name."""
    return hashlib.sha256(_canonical_json(normalized_visual_contract(manifest))).hexdigest()


def baseline_bundle_hash(manifest: dict[str, Any], project_root: Path | None = None) -> str:
    root = Path(project_root) if project_root else PROJECT_ROOT
    digest = hashlib.sha256()
    scenarios = sorted(
        (item for item in manifest.get("scenarios", []) if isinstance(item, dict)),
        key=lambda item: str(item.get("id", "")),
    )
    for item in scenarios:
        scenario_id = str(item.get("id", ""))
        baseline = _scenario_artifact(item, "baseline")
        path = root / baseline
        digest.update(scenario_id.encode("utf-8"))
        digest.update(b"\0")
        if path.is_file():
            digest.update(_sha256_file(path).encode("ascii"))
        else:
            digest.update(b"missing")
        digest.update(b"\n")
    return digest.hexdigest()


def normalized_visual_report(report: dict[str, Any]) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    for item in sorted(
        (entry for entry in report.get("results", []) if isinstance(entry, dict)),
        key=lambda entry: str(entry.get("scenario_id", "")),
    ):
        results.append({
            "scenario_id": str(item.get("scenario_id", "")),
            "passed": bool(item.get("passed", False)),
        })
    return {
        "schema_version": int(report.get("schema_version", 1) or 1),
        "passed": bool(report.get("passed", False)),
        "contract_errors": [str(value) for value in report.get("contract_errors", [])],
        "results": results,
    }


def visual_report_contract_hash(manifest: dict[str, Any], project_root: Path | None = None) -> str:
    root = Path(project_root) if project_root else PROJECT_ROOT
    report_rel = str(manifest.get("links", {}).get("visual_report", "diagnostics/visual_regression_latest.json"))
    report_path = root / report_rel
    if not report_path.is_file():
        return ""
    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return ""
    if not isinstance(report, dict):
        return ""
    return hashlib.sha256(_canonical_json(normalized_visual_report(report))).hexdigest()


def visual_report_hash(manifest: dict[str, Any], project_root: Path | None = None) -> str:
    """Compatibility alias now returning the normalized report contract hash."""
    return visual_report_contract_hash(manifest, project_root)


def approval_fingerprint(manifest: dict[str, Any]) -> str:
    approval = manifest.get("manual_approval")
    if not isinstance(approval, dict):
        return ""
    return hashlib.sha256(_canonical_json(approval)).hexdigest()


def approval_key_dir() -> Path:
    ensure_app_dirs()
    path = state_dir() / "visual_approval_keys"
    path.mkdir(parents=True, exist_ok=True)
    return path


def ensure_local_approval_keypair(key_dir: Path | None = None) -> tuple[Path, Path, str]:
    directory = Path(key_dir) if key_dir else approval_key_dir()
    directory.mkdir(parents=True, exist_ok=True)
    private_path = directory / "desktop_approval_ed25519_private.pem"
    public_path = directory / "desktop_approval_ed25519_public.pem"
    if not private_path.is_file() or not public_path.is_file():
        private_key = Ed25519PrivateKey.generate()
        private_bytes = private_key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
        public_bytes = private_key.public_key().public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        _atomic_write_bytes(private_path, private_bytes, 0o600)
        _atomic_write_bytes(public_path, public_bytes, 0o644)
    public_key = serialization.load_pem_public_key(public_path.read_bytes())
    if not isinstance(public_key, Ed25519PublicKey):
        raise ValueError("Lokaler visueller Freigabeschlüssel ist kein Ed25519-Schlüssel.")
    raw = public_key.public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    key_id = "visual-local-" + hashlib.sha256(raw).hexdigest()[:20]
    return private_path, public_path, key_id


def _atomic_write_bytes(path: Path, data: bytes, mode: int) -> None:
    atomic_write_bytes(path, data, mode=mode)


def _atomic_write_json(path: Path, value: dict[str, Any]) -> None:
    atomic_write_json(path, value, mode=0o644)


def sign_visual_approval(
    manifest_path: Path,
    *,
    reviewer: str,
    build_id: str,
    project_root: Path | None = None,
    key_dir: Path | None = None,
    approval_basis: str = "manual_desktop_review",
    source_approval_sha256: str = "",
) -> dict[str, Any]:
    manifest_path = Path(manifest_path)
    root = Path(project_root) if project_root else manifest_path.parent
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict):
        raise ValueError("Visuelles Prüfmanifest ist kein JSON-Objekt.")
    reviewer_name = str(reviewer).strip()
    if not reviewer_name:
        raise ValueError("Prüfername fehlt.")
    if not manifest.get("passed"):
        raise ValueError("Eine visuelle Freigabe ist nur bei vollständig bestandener Prüfung zulässig.")
    summary = manifest.get("summary", {})
    if int(summary.get("failed_count", 1) or 0) or int(summary.get("contract_error_count", 1) or 0):
        raise ValueError("Offene visuelle Befunde oder Vertragsfehler verhindern die Freigabe.")

    private_path, public_path, key_id = ensure_local_approval_keypair(key_dir)
    private_key = serialization.load_pem_private_key(private_path.read_bytes(), password=None)
    public_key = serialization.load_pem_public_key(public_path.read_bytes())
    if not isinstance(private_key, Ed25519PrivateKey) or not isinstance(public_key, Ed25519PublicKey):
        raise ValueError("Visueller Freigabeschlüssel ist ungültig.")
    public_raw = public_key.public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    now = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    contract_hash = inspection_manifest_hash(manifest)
    report_contract_hash = visual_report_contract_hash(manifest, root)
    payload = {
        "schema_version": APPROVAL_SCHEMA_VERSION,
        "status": "approved",
        "manifest_id": str(manifest.get("id", "")),
        "manifest_version": str(manifest.get("version", "")),
        "build_id": str(build_id).strip(),
        "reviewer": reviewer_name,
        "approved_at": now,
        "approval_basis": str(approval_basis).strip() or "manual_desktop_review",
        "source_approval_sha256": str(source_approval_sha256).strip(),
        "visual_contract_sha256": contract_hash,
        "baseline_bundle_sha256": baseline_bundle_hash(manifest, root),
        "visual_report_contract_sha256": report_contract_hash,
        "scenario_count": int(summary.get("scenario_count", 0) or 0),
        "passed_count": int(summary.get("passed_count", 0) or 0),
    }
    signature = private_key.sign(_canonical_json(payload))
    manifest["manual_approval"] = {
        "payload": payload,
        "signature": {
            "algorithm": "ed25519",
            "key_id": key_id,
            "public_key_base64": base64.b64encode(public_raw).decode("ascii"),
            "signature_base64": base64.b64encode(signature).decode("ascii"),
        },
    }
    manifest.setdefault("approval_contract", {})
    manifest["approval_contract"].update({
        "schema_version": 2,
        "volatile_fields_excluded": [
            "generated_at",
            "artifact_paths",
            "mean_difference",
            "dhash_distance",
            "runtime_messages",
        ],
        "visual_contract_sha256": contract_hash,
        "visual_report_contract_sha256": report_contract_hash,
    })
    _atomic_write_json(manifest_path, manifest)
    check = verify_visual_approval(manifest, root)
    if not check.valid:
        raise ValueError(check.message)
    return manifest["manual_approval"]


def _verify_signature(payload: dict[str, Any], signature_info: dict[str, Any]) -> None:
    if str(signature_info.get("algorithm", "")) != "ed25519":
        raise ValueError("Nicht unterstützter Signaturalgorithmus.")
    public_raw = base64.b64decode(str(signature_info.get("public_key_base64", "")), validate=True)
    signature = base64.b64decode(str(signature_info.get("signature_base64", "")), validate=True)
    Ed25519PublicKey.from_public_bytes(public_raw).verify(signature, _canonical_json(payload))


def verify_visual_approval(manifest: dict[str, Any], project_root: Path | None = None) -> VisualApprovalCheck:
    approval = manifest.get("manual_approval")
    if not isinstance(approval, dict):
        return VisualApprovalCheck(False, "missing", "Noch keine manuelle Desktop-Freigabe signiert.")
    payload = approval.get("payload")
    signature_info = approval.get("signature")
    if not isinstance(payload, dict) or not isinstance(signature_info, dict):
        return VisualApprovalCheck(False, "invalid", "Manueller Freigabevermerk ist unvollständig.")
    reviewer = str(payload.get("reviewer", ""))
    approved_at = str(payload.get("approved_at", ""))
    key_id = str(signature_info.get("key_id", ""))
    try:
        _verify_signature(payload, signature_info)
        schema_version = int(payload.get("schema_version", 1) or 1)
        mismatches: list[str] = []
        if schema_version >= 2:
            expected_contract = inspection_manifest_hash(manifest)
            expected_report = visual_report_contract_hash(manifest, project_root)
            contract_value = str(payload.get("visual_contract_sha256", ""))
            report_value = str(payload.get("visual_report_contract_sha256", ""))
            if contract_value != expected_contract:
                mismatches.append("deterministischer visueller Vertrag wurde nach der Freigabe geändert")
            if report_value != expected_report:
                mismatches.append("normalisierter visueller Prüfbericht wurde nach der Freigabe geändert")
        else:
            # Compatibility with 2.8.0 approvals.
            expected_contract = inspection_manifest_hash(manifest)
            contract_value = str(payload.get("inspection_manifest_sha256", ""))
            expected_report = visual_report_contract_hash(manifest, project_root)
            report_value = str(payload.get("visual_report_sha256", ""))
            if contract_value != expected_contract:
                mismatches.append("Prüfmanifest wurde nach der Freigabe geändert")
            if report_value != expected_report:
                mismatches.append("visueller Prüfbericht wurde nach der Freigabe geändert")
        expected_baselines = baseline_bundle_hash(manifest, project_root)
        if str(payload.get("baseline_bundle_sha256", "")) != expected_baselines:
            mismatches.append("Referenzbilder wurden nach der Freigabe geändert")
        summary = manifest.get("summary", {}) if isinstance(manifest.get("summary"), dict) else {}
        if int(payload.get("scenario_count", -1)) != int(summary.get("scenario_count", 0) or 0):
            mismatches.append("Szenarioanzahl wurde geändert")
        if int(payload.get("passed_count", -1)) != int(summary.get("passed_count", 0) or 0):
            mismatches.append("Anzahl bestandener Szenarien wurde geändert")
        if mismatches:
            return VisualApprovalCheck(False, "expired", "; ".join(mismatches) + ".", key_id, reviewer, approved_at, expected_contract)
        return VisualApprovalCheck(True, "approved", "Visuelle Desktop-Freigabe ist gültig; volatile Messwerte sind vom Freigabehash getrennt.", key_id, reviewer, approved_at, expected_contract)
    except InvalidSignature:
        return VisualApprovalCheck(False, "invalid", "Kryptografische Freigabesignatur ist ungültig.", key_id, reviewer, approved_at)
    except Exception as exc:
        return VisualApprovalCheck(False, "invalid", f"Freigabesignatur konnte nicht geprüft werden: {exc}", key_id, reviewer, approved_at)
