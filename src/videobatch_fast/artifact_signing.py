from __future__ import annotations

import base64
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def public_key_id(key: Ed25519PublicKey) -> str:
    raw = key.public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    return hashlib.sha256(raw).hexdigest()[:24]


def load_private_key(path: Path) -> Ed25519PrivateKey:
    key = serialization.load_pem_private_key(Path(path).read_bytes(), password=None)
    if not isinstance(key, Ed25519PrivateKey):
        raise ValueError("Nur Ed25519-Schlüssel werden unterstützt.")
    return key


def load_public_key(path: Path) -> Ed25519PublicKey:
    key = serialization.load_pem_public_key(Path(path).read_bytes())
    if not isinstance(key, Ed25519PublicKey):
        raise ValueError("Nur Ed25519-Schlüssel werden unterstützt.")
    return key


def create_keypair(private_path: Path, public_path: Path) -> str:
    private = Ed25519PrivateKey.generate()
    private_path.parent.mkdir(parents=True, exist_ok=True)
    public_path.parent.mkdir(parents=True, exist_ok=True)
    private_path.write_bytes(private.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
    private_path.chmod(0o600)
    public = private.public_key()
    public_path.write_bytes(public.public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo))
    public_path.chmod(0o644)
    return public_key_id(public)


def sign_file(path: Path, private_key_path: Path, signature_path: Path | None = None, *, role: str = "artifact") -> Path:
    path = Path(path)
    key = load_private_key(private_key_path)
    digest = sha256_file(path)
    payload = {
        "schema_version": 1,
        "algorithm": "ed25519",
        "role": role,
        "file_name": path.name,
        "size": path.stat().st_size,
        "sha256": digest,
        "key_id": public_key_id(key.public_key()),
    }
    signature = key.sign(canonical_json(payload))
    document = {"payload": payload, "signature_base64": base64.b64encode(signature).decode("ascii")}
    target = signature_path or path.with_name(path.name + ".sig.json")
    target.write_text(json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return target


@dataclass(frozen=True, slots=True)
class SignatureCheck:
    valid: bool
    message: str
    key_id: str = ""


def verify_file(path: Path, signature_path: Path, public_key_path: Path) -> SignatureCheck:
    try:
        document = json.loads(Path(signature_path).read_text(encoding="utf-8"))
        payload = document["payload"]
        key = load_public_key(public_key_path)
        expected_key_id = public_key_id(key)
        if payload.get("key_id") != expected_key_id:
            return SignatureCheck(False, "Signaturschlüssel stimmt nicht.", str(payload.get("key_id", "")))
        if payload.get("file_name") != Path(path).name or int(payload.get("size", -1)) != Path(path).stat().st_size:
            return SignatureCheck(False, "Signatur gehört zu einer anderen Datei.", expected_key_id)
        if payload.get("sha256") != sha256_file(Path(path)):
            return SignatureCheck(False, "Datei wurde nach der Signierung verändert.", expected_key_id)
        signature = base64.b64decode(document["signature_base64"], validate=True)
        key.verify(signature, canonical_json(payload))
        return SignatureCheck(True, "Ed25519-Signatur und SHA-256 stimmen.", expected_key_id)
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError, InvalidSignature) as exc:
        return SignatureCheck(False, f"Signaturprüfung fehlgeschlagen: {exc}")


def verify_signed_update_manifest(manifest_bytes: bytes, signature_bytes: bytes, public_key_path: Path) -> SignatureCheck:
    try:
        signature_doc = json.loads(signature_bytes.decode("utf-8"))
        payload = signature_doc["payload"]
        digest = hashlib.sha256(manifest_bytes).hexdigest()
        if payload.get("sha256") != digest or payload.get("role") != "update-manifest":
            return SignatureCheck(False, "Update-Manifest und Signatur stimmen nicht überein.")
        key = load_public_key(public_key_path)
        if payload.get("key_id") != public_key_id(key):
            return SignatureCheck(False, "Update wurde mit einem unbekannten Schlüssel signiert.")
        key.verify(base64.b64decode(signature_doc["signature_base64"], validate=True), canonical_json(payload))
        return SignatureCheck(True, "Update-Signatur ist gültig.", str(payload.get("key_id", "")))
    except (OSError, ValueError, KeyError, TypeError, UnicodeError, json.JSONDecodeError, InvalidSignature) as exc:
        return SignatureCheck(False, f"Update-Signatur ist ungültig: {exc}")
