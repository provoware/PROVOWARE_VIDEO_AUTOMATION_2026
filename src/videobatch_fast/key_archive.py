from __future__ import annotations

import base64
import hashlib
import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

from .safe_io import atomic_write_bytes

ARCHIVE_SCHEMA_VERSION = 1
AAD = b"provoware-visual-approval-key-archive-v1"


@dataclass(frozen=True, slots=True)
class KeyArchiveResult:
    valid: bool
    message: str
    key_id: str = ""
    created_at: str = ""


def _derive_key(passphrase: str, salt: bytes, *, n: int = 2**15, r: int = 8, p: int = 1) -> bytes:
    if len(passphrase) < 16:
        raise ValueError("Das Archivkennwort muss mindestens 16 Zeichen lang sein.")
    return Scrypt(salt=salt, length=32, n=n, r=r, p=p).derive(passphrase.encode("utf-8"))


def _atomic_write(path: Path, data: bytes, mode: int = 0o600) -> None:
    atomic_write_bytes(path, data, mode=mode)


def _public_key_id(public_key: Ed25519PublicKey) -> str:
    raw = public_key.public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    return "visual-local-" + hashlib.sha256(raw).hexdigest()[:20]


def create_encrypted_key_archive(
    private_key_path: Path,
    public_key_path: Path,
    target: Path,
    passphrase: str,
    *,
    label: str = "provoware visual approval key",
) -> Path:
    private_path = Path(private_key_path)
    public_path = Path(public_key_path)
    private_key = serialization.load_pem_private_key(private_path.read_bytes(), password=None)
    public_key = serialization.load_pem_public_key(public_path.read_bytes())
    if not isinstance(private_key, Ed25519PrivateKey) or not isinstance(public_key, Ed25519PublicKey):
        raise ValueError("Nur ein zusammengehöriges Ed25519-Schlüsselpaar kann archiviert werden.")
    derived_public = private_key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    supplied_public = public_key.public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    if derived_public != supplied_public:
        raise ValueError("Privater und öffentlicher Schlüssel gehören nicht zusammen.")
    key_id = _public_key_id(public_key)
    plaintext = json.dumps({
        "schema_version": ARCHIVE_SCHEMA_VERSION,
        "label": str(label),
        "key_id": key_id,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "private_key_pem_base64": base64.b64encode(private_path.read_bytes()).decode("ascii"),
        "public_key_pem_base64": base64.b64encode(public_path.read_bytes()).decode("ascii"),
    }, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    salt = os.urandom(16)
    nonce = os.urandom(12)
    n, r, p = 2**15, 8, 1
    key = _derive_key(passphrase, salt, n=n, r=r, p=p)
    ciphertext = AESGCM(key).encrypt(nonce, plaintext, AAD)
    envelope: dict[str, Any] = {
        "schema_version": ARCHIVE_SCHEMA_VERSION,
        "format": "provoware-key-archive",
        "cipher": "AES-256-GCM",
        "kdf": {"name": "scrypt", "n": n, "r": r, "p": p, "salt_base64": base64.b64encode(salt).decode("ascii")},
        "nonce_base64": base64.b64encode(nonce).decode("ascii"),
        "aad": AAD.decode("ascii"),
        "ciphertext_base64": base64.b64encode(ciphertext).decode("ascii"),
        "key_id": key_id,
    }
    _atomic_write(Path(target), json.dumps(envelope, ensure_ascii=False, indent=2).encode("utf-8") + b"\n")
    return Path(target)


def decrypt_key_archive(archive_path: Path, passphrase: str) -> dict[str, Any]:
    envelope = json.loads(Path(archive_path).read_text(encoding="utf-8"))
    if envelope.get("format") != "provoware-key-archive" or int(envelope.get("schema_version", 0) or 0) != ARCHIVE_SCHEMA_VERSION:
        raise ValueError("Unbekanntes Schlüsselarchivformat.")
    kdf = envelope.get("kdf", {})
    salt = base64.b64decode(str(kdf.get("salt_base64", "")), validate=True)
    nonce = base64.b64decode(str(envelope.get("nonce_base64", "")), validate=True)
    ciphertext = base64.b64decode(str(envelope.get("ciphertext_base64", "")), validate=True)
    key = _derive_key(
        passphrase,
        salt,
        n=int(kdf.get("n", 2**15)),
        r=int(kdf.get("r", 8)),
        p=int(kdf.get("p", 1)),
    )
    plaintext = AESGCM(key).decrypt(nonce, ciphertext, AAD)
    payload = json.loads(plaintext.decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Entschlüsseltes Schlüsselarchiv ist ungültig.")
    return payload


def verify_key_archive(archive_path: Path, passphrase: str) -> KeyArchiveResult:
    try:
        payload = decrypt_key_archive(archive_path, passphrase)
        private_key = serialization.load_pem_private_key(base64.b64decode(payload["private_key_pem_base64"]), password=None)
        public_key = serialization.load_pem_public_key(base64.b64decode(payload["public_key_pem_base64"]))
        if not isinstance(private_key, Ed25519PrivateKey) or not isinstance(public_key, Ed25519PublicKey):
            raise ValueError("Archiv enthält kein Ed25519-Schlüsselpaar.")
        if private_key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw) != public_key.public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw):
            raise ValueError("Archiviertes Schlüsselpaar ist inkonsistent.")
        key_id = _public_key_id(public_key)
        if key_id != str(payload.get("key_id", "")):
            raise ValueError("Archivierte Schlüssel-ID stimmt nicht.")
        return KeyArchiveResult(True, "Verschlüsseltes Schlüsselarchiv wurde erfolgreich entschlüsselt und geprüft.", key_id, str(payload.get("created_at", "")))
    except Exception as exc:
        return KeyArchiveResult(False, f"Schlüsselarchiv konnte nicht verifiziert werden: {exc}")
