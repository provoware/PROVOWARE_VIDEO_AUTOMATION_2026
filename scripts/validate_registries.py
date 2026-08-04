#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from videobatch_fast.registry import validate_registries

errors = validate_registries()
if errors:
    print("REGISTRY-PRÜFUNG FEHLGESCHLAGEN")
    for error in errors:
        print(f"✕ {error}")
    raise SystemExit(1)
print("REGISTRY-PRÜFUNG BESTANDEN")
