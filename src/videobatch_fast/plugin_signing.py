from __future__ import annotations

import base64
import hashlib
import json
import shutil
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

from .registry import PROJECT_ROOT, load_json
from .safe_io import atomic_write_bytes, atomic_write_json, atomic_write_text

SIGNATURE_FILE = "plugin.sig.json"


@dataclass(frozen=True, slots=True)
class PluginSignatureCheck:
    valid: bool
    plugin_id: str
    key_id: str
    message: str
    payload_sha256: str = ""


def _included_files(plugin_dir: Path) -> list[Path]:
    policy = load_json("registries/PLUGIN_TRUST_REGISTRY.json").get("policy", {})
    maximum_files = int(policy.get("maximum_files", 128))
    maximum_total_size = int(policy.get("maximum_total_size", 5 * 1024 * 1024))
    files: list[Path] = []
    total = 0
    for path in sorted(plugin_dir.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(plugin_dir)
        if SIGNATURE_FILE == rel.as_posix() or "__pycache__" in rel.parts or path.suffix in {".pyc", ".pyo"}:
            continue
        if rel.is_absolute() or ".." in rel.parts:
            raise ValueError("Plugin-Dateipfad ist unsicher.")
        total += path.stat().st_size
        files.append(path)
    if len(files) > maximum_files:
        raise ValueError(f"Plugin enthält zu viele Dateien: {len(files)} > {maximum_files}.")
    if total > maximum_total_size:
        raise ValueError(f"Plugin ist zu groß: {total} > {maximum_total_size} Bytes.")
    return files


def build_signature_payload(plugin_dir: Path) -> tuple[bytes, dict[str, str]]:
    plugin_dir = Path(plugin_dir).resolve()
    manifest_path = plugin_dir / "plugin.json"
    if not manifest_path.is_file():
        raise ValueError("plugin.json fehlt.")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict):
        raise ValueError("plugin.json muss ein Objekt enthalten.")
    file_hashes: dict[str, str] = {}
    for path in _included_files(plugin_dir):
        rel = path.relative_to(plugin_dir).as_posix()
        file_hashes[rel] = hashlib.sha256(path.read_bytes()).hexdigest()
    payload = {
        "schema_version": 1,
        "plugin_id": str(manifest.get("id", "")),
        "api_version": int(manifest.get("api_version", 0) or 0),
        "capability": str(manifest.get("capability", "")),
        "files": file_hashes,
    }
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return encoded, file_hashes


def sign_plugin_directory(plugin_dir: Path, private_key: Ed25519PrivateKey, key_id: str) -> Path:
    payload, file_hashes = build_signature_payload(plugin_dir)
    signature = private_key.sign(payload)
    signature_doc = {
        "schema_version": 1,
        "algorithm": "ed25519",
        "key_id": key_id,
        "payload_sha256": hashlib.sha256(payload).hexdigest(),
        "signature_base64": base64.b64encode(signature).decode("ascii"),
        "files": file_hashes,
        "signed_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }
    target = Path(plugin_dir) / SIGNATURE_FILE
    atomic_write_json(target, signature_doc)
    return target


def verify_plugin_signature(plugin_dir: Path, trust_registry: dict[str, Any] | None = None) -> PluginSignatureCheck:
    plugin_dir = Path(plugin_dir).resolve()
    try:
        manifest = json.loads((plugin_dir / "plugin.json").read_text(encoding="utf-8"))
        plugin_id = str(manifest.get("id", "unknown")) if isinstance(manifest, dict) else "unknown"
    except Exception:
        plugin_id = "unknown"
    signature_path = plugin_dir / SIGNATURE_FILE
    if not signature_path.is_file():
        return PluginSignatureCheck(False, plugin_id, "", "Plugin-Signatur fehlt.")
    try:
        signature_doc = json.loads(signature_path.read_text(encoding="utf-8"))
        if not isinstance(signature_doc, dict):
            raise ValueError("Signaturdatei ist kein Objekt.")
        key_id = str(signature_doc.get("key_id", ""))
        algorithm = str(signature_doc.get("algorithm", ""))
        registry = trust_registry or load_json("registries/PLUGIN_TRUST_REGISTRY.json")
        policy = registry.get("policy", {})
        if algorithm != "ed25519" or algorithm != str(policy.get("algorithm", "ed25519")):
            return PluginSignatureCheck(False, plugin_id, key_id, "Nicht unterstützter Signaturalgorithmus.")
        if key_id in set(registry.get("revoked_keys", [])):
            return PluginSignatureCheck(False, plugin_id, key_id, "Signaturschlüssel wurde widerrufen.")
        key_info = registry.get("trusted_keys", {}).get(key_id)
        if not isinstance(key_info, dict) or key_info.get("status") != "active":
            return PluginSignatureCheck(False, plugin_id, key_id, "Signaturschlüssel ist nicht vertrauenswürdig.")
        payload, file_hashes = build_signature_payload(plugin_dir)
        payload_hash = hashlib.sha256(payload).hexdigest()
        if payload_hash != str(signature_doc.get("payload_sha256", "")):
            return PluginSignatureCheck(False, plugin_id, key_id, "Plugin-Inhalt wurde nach der Signierung verändert.", payload_hash)
        if file_hashes != signature_doc.get("files"):
            return PluginSignatureCheck(False, plugin_id, key_id, "Dateiliste oder Hashwerte stimmen nicht mit der Signatur überein.", payload_hash)
        public_raw = base64.b64decode(str(key_info.get("public_key_base64", "")), validate=True)
        signature = base64.b64decode(str(signature_doc.get("signature_base64", "")), validate=True)
        Ed25519PublicKey.from_public_bytes(public_raw).verify(signature, payload)
        return PluginSignatureCheck(True, plugin_id, key_id, "Plugin-Signatur ist gültig und vertrauenswürdig.", payload_hash)
    except InvalidSignature:
        return PluginSignatureCheck(False, plugin_id, str(signature_doc.get("key_id", "")), "Kryptografische Signatur ist ungültig.")
    except Exception as exc:
        return PluginSignatureCheck(False, plugin_id, "", f"Plugin-Signatur konnte nicht geprüft werden: {exc}")


def quarantine_plugin(plugin_dir: Path, reason: str, quarantine_root: Path | None = None) -> Path:
    plugin_dir = Path(plugin_dir).resolve()
    target_root = Path(quarantine_root) if quarantine_root else PROJECT_ROOT / "plugins" / "quarantine"
    target_root.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    target = target_root / f"{plugin_dir.name}__quarantine__{stamp}"
    counter = 1
    while target.exists():
        target = target_root / f"{plugin_dir.name}__quarantine__{stamp}_{counter}"
        counter += 1
    shutil.move(str(plugin_dir), str(target))
    atomic_write_text(target / "QUARANTINE_REASON.txt", reason + "\n")
    return target


def generate_keypair(private_path: Path, public_path: Path) -> tuple[Path, Path]:
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
    private_path.parent.mkdir(parents=True, exist_ok=True)
    public_path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_bytes(private_path, private_bytes, mode=0o600)
    atomic_write_bytes(public_path, public_bytes, mode=0o644)
    return private_path, public_path


def load_private_key(path: Path) -> Ed25519PrivateKey:
    value = serialization.load_pem_private_key(Path(path).read_bytes(), password=None)
    if not isinstance(value, Ed25519PrivateKey):
        raise ValueError("Privater Schlüssel ist kein Ed25519-Schlüssel.")
    return value
