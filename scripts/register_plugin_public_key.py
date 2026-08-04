#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import json
import os
import tempfile
import time
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "registries" / "PLUGIN_TRUST_REGISTRY.json"


def main() -> int:
    parser = argparse.ArgumentParser(description="Registriert einen öffentlichen Ed25519-Schlüssel für Plugin-Prüfungen.")
    parser.add_argument("public_key", type=Path)
    parser.add_argument("--key-id", required=True)
    parser.add_argument("--publisher", required=True)
    args = parser.parse_args()
    value = serialization.load_pem_public_key(args.public_key.read_bytes())
    if not isinstance(value, Ed25519PublicKey):
        raise SystemExit("Der öffentliche Schlüssel ist kein Ed25519-Schlüssel.")
    raw = value.public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    data = json.loads(REGISTRY.read_text(encoding="utf-8"))
    keys = data.setdefault("trusted_keys", {})
    if args.key_id in keys:
        raise SystemExit(f"Schlüssel-ID existiert bereits: {args.key_id}")
    backup = REGISTRY.with_name(f"PLUGIN_TRUST_REGISTRY.backup.{time.strftime('%Y%m%d_%H%M%S')}.json")
    backup.write_bytes(REGISTRY.read_bytes())
    keys[args.key_id] = {
        "algorithm": "ed25519",
        "public_key_base64": base64.b64encode(raw).decode("ascii"),
        "publisher": args.publisher,
        "status": "active",
        "valid_from": time.strftime("%Y-%m-%d"),
    }
    fd, temp_name = tempfile.mkstemp(prefix="plugin_trust_", suffix=".tmp", dir=REGISTRY.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, REGISTRY)
    finally:
        Path(temp_name).unlink(missing_ok=True)
    print(f"Schlüssel registriert: {args.key_id}")
    print(f"Sicherung: {backup}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
