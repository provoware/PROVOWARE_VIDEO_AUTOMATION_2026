#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from videobatch_fast.plugin_signing import generate_keypair


def main() -> int:
    parser = argparse.ArgumentParser(description="Erzeugt ein Ed25519-Schlüsselpaar für Plugin-Signaturen.")
    parser.add_argument("--private", required=True, type=Path)
    parser.add_argument("--public", required=True, type=Path)
    args = parser.parse_args()
    private_path, public_path = generate_keypair(args.private, args.public)
    print(f"Privater Schlüssel: {private_path}")
    print(f"Öffentlicher Schlüssel: {public_path}")
    print("Wichtig: Privaten Schlüssel niemals in das Projekt oder ein Plugin-Paket legen.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
