#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from videobatch_fast.plugin_signing import load_private_key, sign_plugin_directory


def main() -> int:
    parser = argparse.ArgumentParser(description="Signiert einen geprüften VideoBatch-Pluginordner.")
    parser.add_argument("plugin_dir", type=Path)
    parser.add_argument("--private-key", required=True, type=Path)
    parser.add_argument("--key-id", required=True)
    args = parser.parse_args()
    target = sign_plugin_directory(args.plugin_dir, load_private_key(args.private_key), args.key_id)
    print(f"Plugin signiert: {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
