#!/usr/bin/env python3
from __future__ import annotations

from videobatch_fast.plugins import scan_plugins


def main() -> int:
    checks = scan_plugins(quarantine_invalid=False)
    if not checks:
        print("PLUGIN-PRÜFUNG: keine Plugins installiert")
        return 0
    failed = 0
    for check in checks:
        print(f"{'✓' if check.valid else '✕'} {check.plugin_id}: {check.message}")
        failed += not check.valid
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
