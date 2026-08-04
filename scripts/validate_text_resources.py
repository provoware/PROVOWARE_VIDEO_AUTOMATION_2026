#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from videobatch_fast.text_resources import validate_text_resources  # noqa: E402


def main() -> int:
    errors = validate_text_resources(ROOT)
    if errors:
        for error in errors:
            print(f"TEXTVERTRAG_FEHLER: {error}")
        return 1
    print("Textvertrag bestanden: alle statischen UI-Texte sind ausgelagert und alle Schlüssel vorhanden.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
