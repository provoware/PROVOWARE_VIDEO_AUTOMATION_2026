#!/usr/bin/env python3
from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import tempfile
import time
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def _check(name: str, condition: bool, detail: str) -> dict[str, object]:
    return {"name": name, "passed": bool(condition), "detail": detail}


def main() -> int:
    display = os.environ.get("DISPLAY", "").strip()
    wayland = os.environ.get("WAYLAND_DISPLAY", "").strip()
    if not display and not wayland:
        print("DESKTOP-GATE BLOCKIERT · keine aktive grafische Sitzung erkannt")
        return 2

    from PIL import ImageGrab
    from tkinter import Tk
    from videobatch_fast.automated_desktop_approval import REPORT_NAME, sha256_file
    from videobatch_fast.config import DEFAULT_CONFIG
    from videobatch_fast.ui import VideoBatchFastUI
    from videobatch_fast.versioning import build_label

    checks: list[dict[str, object]] = []
    with tempfile.TemporaryDirectory(prefix="videobatch-live-desktop-") as tmp:
        project_file = Path(tmp) / "desktop-check.vbfast.json"
        state = {
            "project_name": "Desktopprüfung",
            "quick_note": "",
            "audio_paths": [],
            "media_paths": [],
            "playlist_paths": [],
            "calendar_marks": {},
            "calendar_notes": {},
            "workspace_layout_profiles": {},
        }
        root = Tk()
        try:
            screen_w, screen_h = root.winfo_screenwidth(), root.winfo_screenheight()
            width = min(max(1024, int(screen_w * 0.82)), screen_w)
            height = min(max(680, int(screen_h * 0.82)), screen_h)
            root.geometry(f"{width}x{height}+0+0")
            config = dict(DEFAULT_CONFIG)
            config.update({"window_geometry": f"{width}x{height}", "font_scale": 100})
            with patch("videobatch_fast.ui.load_config", return_value=config), patch(
                "videobatch_fast.ui.load_project_state", return_value=(project_file, state, False)
            ):
                app = VideoBatchFastUI(root)
            root.update_idletasks()
            root.update()
            time.sleep(0.25)
            root.update()

            checks.append(_check("Bildschirmgröße", screen_w >= 1024 and screen_h >= 680, f"{screen_w}x{screen_h}"))
            checks.append(_check("Fenster sichtbar", bool(root.winfo_ismapped()), f"{root.winfo_width()}x{root.winfo_height()}"))
            checks.append(_check("Build im Fenstertitel", build_label() in root.title(), root.title()))
            checks.append(_check("Hauptnavigation sichtbar", bool(app.main_notebook.winfo_ismapped()), app.main_notebook.winfo_class()))
            app.main_notebook.select(1)
            root.update_idletasks()
            root.update()
            button_state = str(app.start_button.cget("state"))
            checks.append(_check("Startaktion sichtbar", bool(app.start_button.winfo_ismapped()), str(app.start_button.cget("text"))))
            checks.append(_check("Startaktion sicher initialisiert", button_state in {"disabled", "normal", "active"}, button_state))
            next_focus = root.tk.call("tk_focusNext", app.start_button._w)
            checks.append(_check("Tastaturfokus vorhanden", bool(next_focus), str(next_focus)))

            target_dir = ROOT / "visual_inspection"
            target_dir.mkdir(parents=True, exist_ok=True)
            screenshot = target_dir / "live_desktop_approval.png"
            x, y = root.winfo_rootx(), root.winfo_rooty()
            w, h = root.winfo_width(), root.winfo_height()
            ImageGrab.grab(bbox=(x, y, x + w, y + h), all_screens=True).save(screenshot)
            checks.append(_check("Screenshot erzeugt", screenshot.is_file() and screenshot.stat().st_size > 10_000, f"{screenshot.stat().st_size if screenshot.exists() else 0} Bytes"))
        finally:
            try:
                root.destroy()
            except Exception:
                pass

    passed = all(bool(item["passed"]) for item in checks)
    report = {
        "schema_version": 1,
        "build": build_label(),
        "status": "passed" if passed else "failed",
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "session_type": os.environ.get("XDG_SESSION_TYPE", "unknown"),
        "display": display or wayland,
        "screen": {"width": screen_w, "height": screen_h},
        "screenshot": "visual_inspection/live_desktop_approval.png",
        "screenshot_sha256": sha256_file(ROOT / "visual_inspection" / "live_desktop_approval.png"),
        "checks": checks,
    }
    (ROOT / REPORT_NAME).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for item in checks:
        print(f"{'✓' if item['passed'] else '✕'} {item['name']}: {item['detail']}")
    print("AUTOMATISIERTE DESKTOP-FREIGABE BESTANDEN" if passed else "AUTOMATISIERTE DESKTOP-FREIGABE BLOCKIERT")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
