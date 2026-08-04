from __future__ import annotations

import hashlib
import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .paths import ensure_app_dirs, state_dir
from .plugin_permissions import PluginPermissionSummary
from .safe_io import atomic_write_json, quarantine_file

APPROVAL_SCHEMA_VERSION = 1


@dataclass(frozen=True, slots=True)
class PluginApprovalIdentity:
    plugin_id: str
    version: str
    payload_sha256: str
    key_id: str
    capability: str
    permission_sha256: str


@dataclass(frozen=True, slots=True)
class PluginApprovalStatus:
    valid: bool
    status: str
    message: str
    approval: dict[str, Any] | None = None


def approvals_file() -> Path:
    ensure_app_dirs()
    return state_dir() / "plugin_approvals.json"


def _permission_payload(summary: PluginPermissionSummary) -> dict[str, Any]:
    return {
        "capability": summary.capability,
        "title": summary.title,
        "purpose": summary.purpose,
        "file_access": list(summary.file_access),
        "actions": list(summary.actions),
        "prohibited": list(summary.prohibited),
        "risk_level": summary.risk_level,
        "publisher": summary.publisher,
    }


def permission_fingerprint(summary: PluginPermissionSummary) -> str:
    encoded = json.dumps(_permission_payload(summary), ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def build_identity(
    *,
    plugin_id: str,
    version: str,
    payload_sha256: str,
    key_id: str,
    capability: str,
    permissions: PluginPermissionSummary,
) -> PluginApprovalIdentity:
    return PluginApprovalIdentity(
        plugin_id=str(plugin_id),
        version=str(version or "0.0.0"),
        payload_sha256=str(payload_sha256),
        key_id=str(key_id),
        capability=str(capability),
        permission_sha256=permission_fingerprint(permissions),
    )


def _empty_store() -> dict[str, Any]:
    return {"schema_version": APPROVAL_SCHEMA_VERSION, "updated_at": "", "approvals": {}}


def _normalize_store(raw: Any) -> dict[str, Any]:
    source = raw if isinstance(raw, dict) else {}
    approvals = source.get("approvals", {})
    result = _empty_store()
    if not isinstance(approvals, dict):
        return result
    for plugin_id, item in approvals.items():
        if not isinstance(item, dict):
            continue
        status = str(item.get("status", "revoked"))
        if status not in {"active", "revoked", "expired"}:
            status = "expired"
        result["approvals"][str(plugin_id)] = {
            "plugin_id": str(plugin_id),
            "version": str(item.get("version", "0.0.0")),
            "payload_sha256": str(item.get("payload_sha256", "")),
            "key_id": str(item.get("key_id", "")),
            "capability": str(item.get("capability", "")),
            "permission_sha256": str(item.get("permission_sha256", "")),
            "permissions": item.get("permissions", {}) if isinstance(item.get("permissions"), dict) else {},
            "approved_at": str(item.get("approved_at", "")),
            "updated_at": str(item.get("updated_at", "")),
            "status": status,
            "reason": str(item.get("reason", "")),
        }
    result["updated_at"] = str(source.get("updated_at", ""))
    return result


def load_approvals(path: Path | None = None) -> dict[str, Any]:
    target = Path(path) if path else approvals_file()
    if not target.is_file():
        return _empty_store()
    try:
        return _normalize_store(json.loads(target.read_text(encoding="utf-8")))
    except (OSError, UnicodeError, json.JSONDecodeError, TypeError, ValueError):
        quarantine_file(target, label="corrupt")
        store = _empty_store()
        save_approvals(store, target)
        return store


def save_approvals(store: dict[str, Any], path: Path | None = None) -> Path:
    target = Path(path) if path else approvals_file()
    target.parent.mkdir(parents=True, exist_ok=True)
    normalized = _normalize_store(store)
    normalized["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    atomic_write_json(target, normalized)
    return target


def grant_approval(identity: PluginApprovalIdentity, permissions: PluginPermissionSummary, path: Path | None = None) -> dict[str, Any]:
    store = load_approvals(path)
    now = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    record = {
        **asdict(identity),
        "permissions": _permission_payload(permissions),
        "approved_at": now,
        "updated_at": now,
        "status": "active",
        "reason": "Vom Nutzer nach sichtbarer Berechtigungsprüfung freigegeben.",
    }
    store["approvals"][identity.plugin_id] = record
    save_approvals(store, path)
    return record


def revoke_approval(plugin_id: str, reason: str = "Vom Nutzer widerrufen.", path: Path | None = None) -> PluginApprovalStatus:
    store = load_approvals(path)
    record = store["approvals"].get(plugin_id)
    if not isinstance(record, dict):
        return PluginApprovalStatus(False, "missing", "Für dieses Plugin ist keine Freigabe gespeichert.")
    record["status"] = "revoked"
    record["reason"] = reason
    record["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    save_approvals(store, path)
    return PluginApprovalStatus(False, "revoked", "Plugin-Freigabe wurde widerrufen.", dict(record))


def validate_approval(identity: PluginApprovalIdentity, path: Path | None = None, *, persist_expiry: bool = True) -> PluginApprovalStatus:
    store = load_approvals(path)
    record = store["approvals"].get(identity.plugin_id)
    if not isinstance(record, dict):
        return PluginApprovalStatus(False, "missing", "Noch keine Freigabe gespeichert.")
    if record.get("status") == "revoked":
        return PluginApprovalStatus(False, "revoked", "Die Plugin-Freigabe wurde widerrufen.", dict(record))
    expected = asdict(identity)
    changed = [key for key, value in expected.items() if str(record.get(key, "")) != str(value)]
    if changed:
        reason_map = {
            "version": "Plugin-Version wurde geändert.",
            "payload_sha256": "Plugin-Dateien oder Manifest wurden geändert.",
            "key_id": "Signaturschlüssel wurde geändert.",
            "capability": "Plugin-Fähigkeit wurde geändert.",
            "permission_sha256": "Berechtigungsprofil wurde geändert.",
        }
        reasons = [reason_map.get(key, f"Vertrag geändert: {key}") for key in changed]
        if persist_expiry:
            record["status"] = "expired"
            record["reason"] = " ".join(reasons)
            record["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
            save_approvals(store, path)
        return PluginApprovalStatus(False, "expired", "Freigabe automatisch abgelaufen: " + " ".join(reasons), dict(record))
    if record.get("status") != "active":
        return PluginApprovalStatus(False, str(record.get("status", "expired")), str(record.get("reason", "Freigabe ist nicht aktiv.")), dict(record))
    return PluginApprovalStatus(True, "active", "Gespeicherte Plugin-Freigabe ist unverändert und gültig.", dict(record))


def list_approvals(path: Path | None = None) -> list[dict[str, Any]]:
    store = load_approvals(path)
    return [dict(value) for _, value in sorted(store["approvals"].items()) if isinstance(value, dict)]
