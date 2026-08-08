from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from pathlib import Path
from typing import Any, Mapping

from .safe_io import atomic_write_json

TRUST_SCHEMA_VERSION = 1
AUTH_VERSION = 1
KEY_BYTES = 32
ENV_KEY = "VIDEOBATCH_CHECKPOINT_HMAC_KEY"

class CheckpointTrustError(RuntimeError):
    pass

def _control_dir(root: Path) -> Path:
    return root / ".videobatch-checkpoints"

def _keyring_path(root: Path) -> Path:
    return _control_dir(root) / "trust-keys.json"

def _canonical(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")

def _decode_env_key(value: str) -> bytes:
    raw = value.strip()
    if not raw:
        raise CheckpointTrustError("Externer HMAC-Schlüssel ist leer.")
    try:
        key = bytes.fromhex(raw)
    except ValueError:
        try:
            key = base64.b64decode(raw, validate=True)
        except Exception as exc:
            raise CheckpointTrustError("Externer HMAC-Schlüssel ist weder Hex noch Base64.") from exc
    if len(key) < KEY_BYTES:
        raise CheckpointTrustError("Externer HMAC-Schlüssel ist zu kurz; mindestens 256 Bit erforderlich.")
    return key

def _new_key_id() -> str:
    return f"hmac-{time.time_ns()}-{secrets.token_hex(4)}"

def _load_keyring(root: Path, *, create: bool = True) -> dict[str, Any]:
    root = root.expanduser().resolve()
    path = _keyring_path(root)
    env = os.environ.get(ENV_KEY)
    if env:
        key = _decode_env_key(env)
        kid = "external-env"
        return {"schema_version": TRUST_SCHEMA_VERSION, "active_key_id": kid, "keys": {kid: base64.b64encode(key).decode("ascii")}, "external": True}
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise CheckpointTrustError("Checkpoint-Keyring ist nicht lesbar.") from exc
        if not isinstance(data, dict) or data.get("schema_version") != TRUST_SCHEMA_VERSION or not isinstance(data.get("keys"), dict):
            raise CheckpointTrustError("Checkpoint-Keyring besitzt ein ungültiges Schema.")
        return data
    if not create:
        raise CheckpointTrustError("Kein Checkpoint-Keyring vorhanden.")
    key_id = _new_key_id()
    data = {
        "schema_version": TRUST_SCHEMA_VERSION,
        "active_key_id": key_id,
        "created_at_unix_ns": time.time_ns(),
        "keys": {key_id: base64.b64encode(secrets.token_bytes(KEY_BYTES)).decode("ascii")},
        "retired_key_ids": [],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_json(path, data)
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass
    return data

def _key_bytes(ring: Mapping[str, Any], key_id: str) -> bytes:
    keys = ring.get("keys")
    if not isinstance(keys, Mapping) or key_id not in keys:
        raise CheckpointTrustError(f"Unbekannte Checkpoint-Schlüssel-ID: {key_id}")
    try:
        key = base64.b64decode(str(keys[key_id]), validate=True)
    except Exception as exc:
        raise CheckpointTrustError("Checkpoint-Schlüsselmaterial ist beschädigt.") from exc
    if len(key) < KEY_BYTES:
        raise CheckpointTrustError("Checkpoint-Schlüsselmaterial ist zu kurz.")
    return key

def active_key_id(root: Path | str) -> str:
    ring = _load_keyring(Path(root))
    key_id = ring.get("active_key_id")
    if not isinstance(key_id, str) or not key_id:
        raise CheckpointTrustError("Checkpoint-Keyring besitzt keinen aktiven Schlüssel.")
    return key_id

def sign_payload(root: Path | str, payload: Mapping[str, Any], *, key_id: str | None = None) -> dict[str, Any]:
    base = Path(root).expanduser().resolve()
    ring = _load_keyring(base)
    kid = key_id or str(ring.get("active_key_id") or "")
    key = _key_bytes(ring, kid)
    digest = hmac.new(key, _canonical(payload), hashlib.sha256).hexdigest()
    return {"version": AUTH_VERSION, "algorithm": "HMAC-SHA256", "key_id": kid, "mac_sha256": digest}

def verify_payload(root: Path | str, payload: Mapping[str, Any], auth: Mapping[str, Any]) -> bool:
    if auth.get("version") != AUTH_VERSION or auth.get("algorithm") != "HMAC-SHA256":
        return False
    kid = auth.get("key_id")
    mac = auth.get("mac_sha256")
    if not isinstance(kid, str) or not isinstance(mac, str) or len(mac) != 64:
        return False
    try:
        expected = sign_payload(root, payload, key_id=kid)["mac_sha256"]
    except CheckpointTrustError:
        return False
    return hmac.compare_digest(expected, mac)

def rotate_key(root: Path | str) -> str:
    base = Path(root).expanduser().resolve()
    if os.environ.get(ENV_KEY):
        raise CheckpointTrustError("Extern verwalteter Checkpoint-Schlüssel kann nicht lokal rotiert werden.")
    ring = _load_keyring(base)
    old = str(ring.get("active_key_id") or "")
    kid = _new_key_id()
    ring["keys"][kid] = base64.b64encode(secrets.token_bytes(KEY_BYTES)).decode("ascii")
    ring["active_key_id"] = kid
    retired = list(ring.get("retired_key_ids") or [])
    if old and old not in retired:
        retired.append(old)
    ring["retired_key_ids"] = retired
    ring["rotated_at_unix_ns"] = time.time_ns()
    atomic_write_json(_keyring_path(base), ring)
    try:
        os.chmod(_keyring_path(base), 0o600)
    except OSError:
        pass
    return kid


def write_prune_anchor(root: Path | str, removed: list[dict[str, str]], first_retained_generation_id: str) -> None:
    base = Path(root).expanduser().resolve()
    payload = {
        "schema_version": 1,
        "created_at_unix_ns": time.time_ns(),
        "removed": removed,
        "first_retained_generation_id": first_retained_generation_id,
    }
    payload["authentication"] = sign_payload(base, payload)
    atomic_write_json(_control_dir(base) / "trust-prune-anchor.json", payload)


def verify_prune_anchor(root: Path | str) -> dict[str, Any] | None:
    base = Path(root).expanduser().resolve()
    path = _control_dir(base) / "trust-prune-anchor.json"
    if not path.exists():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    if not isinstance(value, dict) or value.get("schema_version") != 1:
        return None
    auth = value.get("authentication")
    unsigned = {key: item for key, item in value.items() if key != "authentication"}
    if not isinstance(auth, dict) or not verify_payload(base, unsigned, auth):
        return None
    return value
