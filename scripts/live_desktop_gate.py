#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import tempfile
import time
from typing import Any
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
GEOMETRIES = ((1440, 900), (1500, 920), (1920, 1080))
FONT_SCALES = (90, 105, 125)


def _check(name: str, condition: bool, detail: str) -> dict[str, object]:
    return {"name": name, "passed": bool(condition), "detail": detail}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Reale Desktopprüfung mit optionalem sourcegebundenem Stable-Evidence-Export."
    )
    parser.add_argument("--evidence-dir", type=Path)
    return parser


def _display_state(physical_mode: bool) -> tuple[str, str] | None:
    display = os.environ.get("DISPLAY", "").strip()
    wayland = os.environ.get("WAYLAND_DISPLAY", "").strip()
    if physical_mode and os.environ.get("VIDEOBATCH_PHYSICAL_ACCEPTANCE") != "1":
        print("DESKTOP-EVIDENCE BLOCKIERT · VIDEOBATCH_PHYSICAL_ACCEPTANCE=1 fehlt")
        return None
    if not display and not wayland:
        print("DESKTOP-GATE BLOCKIERT · keine aktive grafische Sitzung erkannt")
        return None
    return display, wayland


def _initial_state() -> dict[str, Any]:
    return {
        "project_name": "Desktopprüfung",
        "quick_note": "",
        "audio_paths": [],
        "media_paths": [],
        "playlist_paths": [],
        "calendar_marks": {},
        "calendar_notes": {},
        "workspace_layout_profiles": {},
    }


def _scaling_matrix(root: Any, app: Any) -> list[dict[str, object]]:
    profiles: list[dict[str, object]] = []
    for target_w, target_h in GEOMETRIES:
        for zoom in FONT_SCALES:
            root.geometry(f"{target_w}x{target_h}+0+0")
            app._global_zoom_changed(str(zoom))
            root.update_idletasks()
            root.update()
            actual_w, actual_h = root.winfo_width(), root.winfo_height()
            widgets_visible = all(bool(widget.winfo_ismapped()) for widget in (app.main_notebook, app.start_button))
            passed = (
                actual_w >= target_w - 2
                and actual_h >= target_h - 2
                and widgets_visible
                and root.winfo_reqwidth() <= actual_w
                and root.winfo_reqheight() <= actual_h
            )
            profiles.append(
                {
                    "geometry": f"{target_w}x{target_h}",
                    "font_scale": zoom,
                    "actual": f"{actual_w}x{actual_h}",
                    "passed": passed,
                }
            )
    return profiles


def _base_checks(root: Any, app: Any, build: str, screen_w: int, screen_h: int) -> list[dict[str, object]]:
    checks = [
        _check("Bildschirmgröße", screen_w >= 1024 and screen_h >= 680, f"{screen_w}x{screen_h}"),
        _check("Fenster sichtbar", bool(root.winfo_ismapped()), f"{root.winfo_width()}x{root.winfo_height()}"),
        _check("Build im Fenstertitel", build in root.title(), root.title()),
        _check("Hauptnavigation sichtbar", bool(app.main_notebook.winfo_ismapped()), app.main_notebook.winfo_class()),
    ]
    app.main_notebook.select(1)
    root.update_idletasks()
    root.update()
    button_state = str(app.start_button.cget("state"))
    checks.extend(
        [
            _check("Startaktion sichtbar", bool(app.start_button.winfo_ismapped()), str(app.start_button.cget("text"))),
            _check("Startaktion sicher initialisiert", button_state in {"disabled", "normal", "active"}, button_state),
        ]
    )
    next_focus = root.tk.call("tk_focusNext", app.start_button._w)
    checks.append(_check("Tastaturfokus vorhanden", bool(next_focus), str(next_focus)))
    return checks


def _physical_checks(screen_w: int, screen_h: int) -> list[dict[str, object]]:
    session_type = os.environ.get("XDG_SESSION_TYPE", "").strip().lower()
    desktop_name = os.environ.get("XDG_CURRENT_DESKTOP", "")
    return [
        _check("KDE/Plasma-Sitzung", "kde" in desktop_name.lower() or "plasma" in desktop_name.lower(), desktop_name or "unbekannt"),
        _check("Native Sitzung X11/Wayland", session_type in {"x11", "wayland"}, session_type or "unbekannt"),
        _check("Physischer Full-HD-Prüfraum", screen_w >= 1920 and screen_h >= 1080, f"{screen_w}x{screen_h}"),
    ]


def _capture_screenshot(root: Any, image_grab: Any) -> Path:
    target_dir = ROOT / "visual_inspection"
    target_dir.mkdir(parents=True, exist_ok=True)
    screenshot = target_dir / "live_desktop_approval.png"
    x, y = root.winfo_rootx(), root.winfo_rooty()
    w, h = root.winfo_width(), root.winfo_height()
    image_grab.grab(bbox=(x, y, x + w, y + h), all_screens=True).save(screenshot)
    return screenshot


def _run_ui_probe(physical_mode: bool) -> tuple[list[dict[str, object]], list[dict[str, object]], int, int, Path, str]:
    from PIL import ImageGrab
    from tkinter import Tk
    from videobatch_fast.config import DEFAULT_CONFIG
    from videobatch_fast.ui import VideoBatchFastUI
    from videobatch_fast.versioning import build_label

    checks: list[dict[str, object]] = []
    profiles: list[dict[str, object]] = []
    with tempfile.TemporaryDirectory(prefix="videobatch-live-desktop-") as tmp:
        project_file = Path(tmp) / "desktop-check.vbfast.json"
        root = Tk()
        try:
            screen_w, screen_h = root.winfo_screenwidth(), root.winfo_screenheight()
            width = min(max(1024, int(screen_w * 0.82)), screen_w)
            height = min(max(680, int(screen_h * 0.82)), screen_h)
            root.geometry(f"{width}x{height}+0+0")
            config = dict(DEFAULT_CONFIG)
            config.update({"window_geometry": f"{width}x{height}", "font_scale": 100})
            with patch("videobatch_fast.ui.load_config", return_value=config), patch(
                "videobatch_fast.ui.load_project_state",
                return_value=(project_file, _initial_state(), False),
            ):
                app = VideoBatchFastUI(root)
            root.update_idletasks()
            root.update()
            time.sleep(0.25)
            root.update()
            build = build_label()
            checks.extend(_base_checks(root, app, build, screen_w, screen_h))
            profiles = _scaling_matrix(root, app)
            passed_profiles = sum(1 for item in profiles if item["passed"])
            checks.append(_check("Skalierungsmatrix 90/105/125 %", passed_profiles == len(profiles), f"{passed_profiles}/{len(profiles)} Profile"))
            screenshot = _capture_screenshot(root, ImageGrab)
            size = screenshot.stat().st_size if screenshot.exists() else 0
            checks.append(_check("Screenshot erzeugt", screenshot.is_file() and size > 10_000, f"{size} Bytes"))
            if physical_mode:
                checks.extend(_physical_checks(screen_w, screen_h))
            return checks, profiles, screen_w, screen_h, screenshot, build
        finally:
            try:
                root.destroy()
            except Exception:
                pass


def _write_report(
    checks: list[dict[str, object]],
    profiles: list[dict[str, object]],
    screen_w: int,
    screen_h: int,
    screenshot: Path,
    build: str,
    display: str,
    wayland: str,
    physical_mode: bool,
) -> tuple[dict[str, Any], bool]:
    from videobatch_fast.automated_desktop_approval import REPORT_NAME, sha256_file

    passed = all(bool(item["passed"]) for item in checks)
    report = {
        "schema_version": 2,
        "build": build,
        "status": "passed" if passed else "failed",
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "session_type": os.environ.get("XDG_SESSION_TYPE", "unknown"),
        "display": display or wayland,
        "desktop": os.environ.get("XDG_CURRENT_DESKTOP", ""),
        "physical_acceptance": bool(physical_mode),
        "scaling_profiles": profiles,
        "screen": {"width": screen_w, "height": screen_h},
        "screenshot": "visual_inspection/live_desktop_approval.png",
        "screenshot_sha256": sha256_file(screenshot),
        "checks": checks,
    }
    (ROOT / REPORT_NAME).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report, passed


def _export_if_requested(report: dict[str, Any], evidence_dir: Path | None) -> int:
    if evidence_dir is None:
        return 0
    kind = str(report["session_type"]).lower()
    if kind not in {"x11", "wayland"}:
        print(f"DESKTOP-EVIDENCE BLOCKIERT · unbekannte Sitzung {kind}")
        return 2
    from export_stable_evidence import export_desktop

    export_desktop(evidence_dir / f"kde_{kind}.json")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    physical_mode = args.evidence_dir is not None
    displays = _display_state(physical_mode)
    if displays is None:
        return 2
    display, wayland = displays
    checks, profiles, screen_w, screen_h, screenshot, build = _run_ui_probe(physical_mode)
    report, passed = _write_report(
        checks, profiles, screen_w, screen_h, screenshot, build, display, wayland, physical_mode
    )
    for item in checks:
        print(f"{'✓' if item['passed'] else '✕'} {item['name']}: {item['detail']}")
    print("AUTOMATISIERTE DESKTOP-FREIGABE BESTANDEN" if passed else "AUTOMATISIERTE DESKTOP-FREIGABE BLOCKIERT")
    if not passed:
        return 1
    return _export_if_requested(report, args.evidence_dir)


if __name__ == "__main__":
    raise SystemExit(main())
