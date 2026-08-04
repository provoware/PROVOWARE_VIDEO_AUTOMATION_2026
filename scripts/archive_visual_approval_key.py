#!/usr/bin/env python3
from __future__ import annotations

import argparse
import getpass
import os
from pathlib import Path

from videobatch_fast.key_archive import create_encrypted_key_archive, verify_key_archive
from videobatch_fast.visual_approval import approval_key_dir


def _passphrase(confirm: bool) -> str:
    value = os.environ.get("PROVOWARE_KEY_BACKUP_PASSPHRASE", "")
    if value:
        return value
    first = getpass.getpass("Archivkennwort: ")
    if confirm:
        second = getpass.getpass("Archivkennwort wiederholen: ")
        if first != second:
            raise SystemExit("Kennwörter stimmen nicht überein.")
    return first


def main() -> int:
    parser = argparse.ArgumentParser(description="Verschlüsselt oder prüft den privaten visuellen Ed25519-Freigabeschlüssel.")
    parser.add_argument("--output", type=Path, default=Path.home() / "provoware_visual_approval_key_backup.pvak")
    parser.add_argument("--key-dir", type=Path, default=approval_key_dir())
    parser.add_argument("--verify", type=Path)
    args = parser.parse_args()
    passphrase = _passphrase(confirm=not bool(args.verify))
    if args.verify:
        result = verify_key_archive(args.verify, passphrase)
        print(("SCHLÜSSELARCHIV GÜLTIG" if result.valid else "SCHLÜSSELARCHIV FEHLER") + f" · {result.message}")
        return 0 if result.valid else 1
    private_path = args.key_dir / "desktop_approval_ed25519_private.pem"
    public_path = args.key_dir / "desktop_approval_ed25519_public.pem"
    target = create_encrypted_key_archive(private_path, public_path, args.output, passphrase)
    result = verify_key_archive(target, passphrase)
    if not result.valid:
        print(f"SCHLÜSSELARCHIV FEHLER · {result.message}")
        return 1
    print(f"SCHLÜSSELARCHIV ERSTELLT · {target} · Schlüssel {result.key_id}")
    print("Wichtig: Archiv und Kennwort getrennt und offline aufbewahren.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
