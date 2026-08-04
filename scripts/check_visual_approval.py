#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "VISUAL_INSPECTION_MANIFEST.json"


def main() -> int:
    parser = argparse.ArgumentParser(description="Prüft den manuellen visuellen Desktop-Abnahmevermerk.")
    parser.add_argument("--require", action="store_true", help="Fehlende Freigabe als Releasefehler behandeln.")
    args = parser.parse_args()

    from videobatch_fast.visual_approval import verify_visual_approval
    from videobatch_fast.automated_desktop_approval import verify_automated_desktop_approval

    if not MANIFEST.is_file():
        print("VISUELLE DESKTOP-FREIGABE FEHLT · Prüfmanifest ist nicht vorhanden")
        return 1
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    check = verify_visual_approval(manifest, ROOT)
    if check.valid:
        print(f"VISUELLE DESKTOP-FREIGABE GÜLTIG · {check.reviewer} · {check.approved_at} · Schlüssel {check.key_id}")
        return 0
    automated = verify_automated_desktop_approval(ROOT)
    if automated.valid:
        print(f"AUTOMATISIERTE DESKTOP-FREIGABE GÜLTIG · {automated.session_type} · {automated.generated_at}")
        return 0
    if check.status == "missing" and automated.status == "missing" and not args.require:
        print("VISUELLE DESKTOP-FREIGABE OFFEN · reale Desktopprüfung noch nicht abgeschlossen")
        return 0
    print(f"VISUELLE DESKTOP-FREIGABE BLOCKIERT · manuell: {check.message} · automatisch: {automated.message}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
