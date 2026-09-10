#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from videobatch_fast.platform_integration import (  # noqa: E402
    PlatformCompatibilityError,
    detect_desktop_platform,
    validate_gui_environment,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="VideoBatch Wayland/Kubuntu 26.04 Vorprüfung")
    parser.add_argument("--json", action="store_true", help="nur maschinenlesbare Ausgabe")
    args = parser.parse_args()

    platform = detect_desktop_platform()
    status = "ready"
    error = ""
    try:
        validate_gui_environment(platform)
    except PlatformCompatibilityError as exc:
        status = "blocked"
        error = str(exc)

    payload = {
        "schema_version": 1,
        "status": status,
        "target": "Kubuntu 26.04 Plasma Wayland",
        "platform": platform.to_dict(),
        "error": error,
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        light = "🟢" if status == "ready" else "🔴"
        print(f"{light} VideoBatch Plattformprüfung: {status}")
        print(f"Sitzung: {platform.session_type}")
        print(f"Tkinter-Transport: {platform.tkinter_transport}")
        print(f"System: {platform.distro_name or platform.distro_id or 'unbekannt'}")
        for warning in platform.warnings:
            print(f"WARNUNG: {warning}")
        if error:
            print(f"FEHLER: {error}")
    return 0 if status == "ready" else 2


if __name__ == "__main__":
    raise SystemExit(main())
