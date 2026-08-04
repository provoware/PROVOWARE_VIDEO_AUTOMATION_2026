#!/usr/bin/env python3
from __future__ import annotations

import argparse
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

from PIL import ImageGrab
from tkinter import Tk

from videobatch_fast.config import DEFAULT_CONFIG
from videobatch_fast.error_handling import ErrorDefinition
from videobatch_fast.preview_service import build_preview
from videobatch_fast.media_import_dialog import MediaImportDialog
from videobatch_fast.plugin_approval_manager import PluginApprovalManagerDialog
from videobatch_fast.registry import PROJECT_ROOT, load_json
from videobatch_fast.ui import VideoBatchFastUI
from videobatch_fast.ui_components import SolutionDialog
from videobatch_fast.versioning import build_label
from videobatch_fast.workflow_dialogs import (
    PluginPermissionDecisionDialog,
    VisualApprovalSignDialog,
    archive_preview_dialog,
    recovery_dialog,
    update_assistant_dialog,
)
from videobatch_fast.visual_regression import compare_visual, create_difference_image, validate_semantic_colors, write_visual_report

FIXED_PROJECT = {
    "project_name": "Neues Projekt",
    "quick_note": "",
    "audio_paths": [],
    "media_paths": [],
    "playlist_paths": [],
    "calendar_year": 2026,
    "calendar_month": 8,
    "calendar_marks": {},
}


def _cancel_after_callbacks(root: Tk) -> None:
    try:
        callbacks = root.tk.call("after", "info")
        for callback in callbacks:
            try:
                root.after_cancel(callback)
            except Exception:
                pass
    except Exception:
        pass


def _widget_texts(root: Tk) -> str:
    values: list[str] = []
    try:
        title = root.title()
        if title:
            values.append(str(title))
    except Exception:
        pass

    def walk(widget) -> None:
        try:
            visible = widget is root or bool(widget.winfo_ismapped())
        except Exception:
            visible = True
        try:
            value = widget.cget("text")
            if visible and value:
                values.append(str(value))
        except Exception:
            pass
        try:
            variable = widget.cget("textvariable")
            if visible and variable:
                values.append(str(widget.getvar(variable)))
        except Exception:
            pass
        for child in widget.winfo_children():
            walk(child)

    walk(root)
    return "\n".join(values)


def _clipped_widgets(root: Tk) -> list[str]:
    errors: list[str] = []
    root_x, root_y = root.winfo_rootx(), root.winfo_rooty()
    root_right = root_x + root.winfo_width()
    root_bottom = root_y + root.winfo_height()

    def walk(widget) -> None:
        for child in widget.winfo_children():
            try:
                if child.winfo_ismapped() and child.winfo_width() > 4 and child.winfo_height() > 4:
                    ancestor = child.master
                    inside_scroll_canvas = False
                    while ancestor is not None and ancestor is not root:
                        try:
                            if ancestor.winfo_class() == "Canvas":
                                inside_scroll_canvas = True
                                break
                            ancestor = ancestor.master
                        except Exception:
                            break
                    x, y = child.winfo_rootx(), child.winfo_rooty()
                    right, bottom = x + child.winfo_width(), y + child.winfo_height()
                    if not inside_scroll_canvas and (x < root_x - 3 or y < root_y - 3 or right > root_right + 3 or bottom > root_bottom + 3):
                        errors.append(f"{child.winfo_class()} außerhalb des sichtbaren Fensters: {x},{y},{right},{bottom}")
            except Exception:
                pass
            walk(child)

    walk(root)
    return errors[:25]



def _prepare_workspace(app: VideoBatchFastUI, state: str) -> None:
    media_root = PROJECT_ROOT / "tests" / "generated_media"
    audio = media_root / "audio_kurz.wav"
    image = media_root / "bild_querformat.png"
    app.audios = [audio]
    app.media = [image]
    app.playlist.items = [audio]
    app.playlist.current = 0
    app._refresh_file_trees()
    app._rebuild_pairs()
    app._refresh_playlist()
    app.pair_status.set("1 Paar · schneller Einpass-Render · Prüfung bereit")
    app.current_job.set("Auftrag 1/1 · audio_kurz.wav + bild_querformat.png")
    app.phase.set("1-Pass · Automatisch schnell")
    app.elapsed.set("00:18")
    app.eta.set("00:24")
    app.speed.set("1,7×")
    app.output_size.set("12,4 MB")
    app.activity.set("jetzt")
    app.job_progress.set(42)
    app.total_progress.set(42)
    if state == "files":
        app.main_notebook.select(1)
        app.library_notebook.select(0)
    elif state == "preview":
        app.main_notebook.select(2)
        preview = build_preview(image, 960)
        app._show_preview(image, preview)
        app.preview_status.set("Vorschau bereit")
    elif state == "playlist":
        app.main_notebook.select(2)
        grid = app.workflow_grids.get("preview")
        if grid is not None and hasattr(app, "playlist_card"):
            root = app.root
            root.after_idle(lambda: grid.scroll_to_widget(app.playlist_card))
        app.playlist_status.set("Bereit · 1 Titel · automatische Wiedergabe aus")
    elif state == "monitor":
        app.main_notebook.select(4)
        grid = app.workflow_grids.get("production")
        if grid is not None and hasattr(app, "monitor_card"):
            app.root.after_idle(lambda: grid.scroll_to_widget(app.monitor_card))
        app._event("VISUAL_RENDER_ACTIVE", "Video wird erstellt", "FFmpeg arbeitet normal.", solution="Fortschritt weiter beobachten.")
        app._event("VISUAL_OUTPUT_GROWING", "Ausgabedatei wächst", "12,4 MB wurden geschrieben.", level="success", solution="Keine Aktion nötig.")
    elif state == "debug_machine":
        app.main_notebook.select(5)
        app.monitor_notebook.select(1)
        app._event("VISUAL_MACHINE_EVENT", "Maschinenereignis erzeugt", "Strukturierter JSONL-Datensatz für die visuelle Prüfung.", solution="Maschinenprotokoll prüfen.")


def _prepare_dialog(app: VideoBatchFastUI, state: str):
    if state == "update":
        return update_assistant_dialog(app.root, "2.7.1", 18, modal=False).window
    if state == "archive":
        return archive_preview_dialog(app.root, 6, "/home/nutzer/Projekte/Demo", "__verwendet", modal=False).window
    if state == "plugin":
        summary = (
            "Plugin: sample-validator\n"
            "Herausgeber: Provoware\n"
            "Fähigkeit: Prüf-Plugin\n"
            "Risiko: niedrig\n\n"
            "Darf zugreifen auf:\n• ausdrücklich übergebene Metadaten\n• keine freie Ordnersuche\n\n"
            "Darf ausführen:\n• begrenzte Validierung im Unterprozess\n\n"
            "Bleibt verboten:\n• Netzwerkzugriff\n• Shell-Aufrufe\n• Änderung an Originaldateien"
        )
        return PluginPermissionDecisionDialog(app.root, summary, "active", modal=False).window
    if state == "recovery":
        return recovery_dialog(app.root, "PROCESS_STALLED", modal=False).window
    if state == "approval_manager":
        return PluginApprovalManagerDialog(app.root).window
    if state == "visual_approval":
        return VisualApprovalSignDialog(app.root, build_label(), default_reviewer="Prüfer Demo", modal=False).window
    if state == "media_import":
        dialog = MediaImportDialog(
            app.root,
            audio=False,
            initial_dir=PROJECT_ROOT / "tests" / "generated_media",
            modal=False,
        )
        dialog.window._videobatch_dialog_ref = dialog
        deadline = time.monotonic() + 3.0
        while not dialog._scan_complete and time.monotonic() < deadline:
            app.root.update()
            time.sleep(0.01)
        dialog._set_view_mode("icons")
        image_records = [record for record in dialog._visible_records if record.path.suffix.lower() in {".png", ".jpg", ".jpeg"}]
        if image_records:
            selected = image_records[0].path
            dialog.icon_grid.selected = {selected}
            dialog.icon_grid.focus_path = selected
            dialog._icon_selection_changed((selected,), selected)
            deadline = time.monotonic() + 2.0
            while dialog.preview_photo is None and time.monotonic() < deadline:
                app.root.update()
                time.sleep(0.01)
        return dialog.window
    if state == "solution":
        definition = ErrorDefinition(
            code="OUTPUT_PERMISSION",
            title="Ausgabeordner ist nicht beschreibbar",
            cause="Der gewählte Ordner kann mit den aktuellen Benutzerrechten nicht verwendet werden.",
            effect="Die Produktion wurde vor dem Schreiben sicher angehalten.",
            automatic_action="Originaldateien und vorhandene Ausgaben bleiben unverändert.",
            solution="Neuen Benutzerordner erstellen oder einen sicheren Ausgabeordner auswählen.",
            alternative="Ordner später selbst korrigieren und erneut prüfen.",
            severity="blocking",
            actions=("create_output_folder", "choose_output", "use_safe_output", "open_logs"),
        )
        actions = {action: (lambda: None) for action in definition.actions}
        return SolutionDialog(app.root, definition, "Pfad: /geschütztes/ziel", actions).window
    raise ValueError(f"Unbekannter Dialogzustand: {state}")


def capture_scenario(scenario: dict, output_dir: Path) -> tuple[Path, list[str]]:
    width = int(scenario["width"])
    height = int(scenario["height"])
    root_width = int(scenario.get("root_width", width))
    root_height = int(scenario.get("root_height", height))
    font_scale = int(scenario.get("font_scale", 100))
    scenario_id = str(scenario["id"])
    config = dict(DEFAULT_CONFIG)
    config.update({"window_geometry": f"{root_width}x{root_height}", "font_scale": font_scale})
    root = Tk()
    root.geometry(f"{root_width}x{root_height}+0+0")
    root.update_idletasks()
    with tempfile.TemporaryDirectory() as tmp:
        project_path = Path(tmp) / "visual.vbfast.json"
        with patch("videobatch_fast.ui.load_config", return_value=config), patch(
            "videobatch_fast.ui.load_project_state", return_value=(project_path, dict(FIXED_PROJECT), False)
        ):
            app = VideoBatchFastUI(root)
        page = str(scenario.get("page", "dashboard"))
        capture_widget = root
        if page == "workspace":
            _prepare_workspace(app, str(scenario.get("state", "files")))
        elif page == "dialog":
            app.main_notebook.select(0)
            capture_widget = _prepare_dialog(app, str(scenario.get("state", "update")))
        else:
            app.main_notebook.select(0)
        root.geometry(f"{root_width}x{root_height}+0+0")
        root.update_idletasks()
        root.update()
        _cancel_after_callbacks(root)
        app.datetime_text.set("02.08.2026 · 01:48:00")
        app.status_text.set("Bereit · FFmpeg geprüft · Registries geprüft")
        root.update_idletasks()
        root.update()
        capture_widget.update_idletasks()
        capture_widget.update()
        time.sleep(0.08)
        x = capture_widget.winfo_rootx()
        y = capture_widget.winfo_rooty()
        w = capture_widget.winfo_width()
        h = capture_widget.winfo_height()
        output_dir.mkdir(parents=True, exist_ok=True)
        target = output_dir / f"{scenario_id}.png"
        ImageGrab.grab(bbox=(x, y, x + w, y + h), all_screens=True).save(target)
        registry = load_json("registries/VISUAL_REGRESSION_REGISTRY.json")
        all_text = _widget_texts(capture_widget)
        required_texts = scenario.get("required_visible_texts", registry.get("policy", {}).get("required_visible_texts", []))
        errors = [f"Pflichttext fehlt: {item}" for item in required_texts if item not in all_text]
        if abs(w - width) > 5 or abs(h - height) > 5:
            errors.append(f"Testanzeige zu klein: angefordert {width}x{height}, erhalten {w}x{h}")
        errors.extend(_clipped_widgets(capture_widget))
        required_colors = scenario.get("required_semantic_colors", [])
        if required_colors:
            errors.extend(validate_semantic_colors(target, expected_colors=required_colors))
        dialog_ref = getattr(capture_widget, "_videobatch_dialog_ref", None)
        if dialog_ref is not None:
            dialog_ref._close()
            root.update_idletasks()
        root.destroy()
        return target, errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=PROJECT_ROOT / "tests" / "visual_actual")
    parser.add_argument("--baselines", type=Path, default=PROJECT_ROOT / "tests" / "baselines")
    parser.add_argument("--accept-baselines", action="store_true")
    parser.add_argument("--report", type=Path, default=PROJECT_ROOT / "diagnostics" / "visual_regression_latest.json")
    args = parser.parse_args()
    registry = load_json("registries/VISUAL_REGRESSION_REGISTRY.json")
    results = []
    contract_failures: list[str] = []
    for scenario in registry.get("scenarios", []):
        actual, errors = capture_scenario(scenario, args.output)
        baseline = args.baselines / actual.name
        if errors:
            contract_failures.extend(f"{scenario['id']}: {error}" for error in errors)
            for error in errors:
                print(f"✕ {scenario['id']}: {error}")
        if args.accept_baselines and not errors:
            baseline.parent.mkdir(parents=True, exist_ok=True)
            baseline.write_bytes(actual.read_bytes())
            print(f"BASELINE AKZEPTIERT: {baseline.name}")
        result = compare_visual(str(scenario["id"]), baseline, actual)
        results.append(result)
        diff = PROJECT_ROOT / "diagnostics" / "visual_diff" / f"{scenario['id']}.png"
        if not result.passed and baseline.is_file() and actual.is_file():
            create_difference_image(baseline, actual, diff)
            print(f"  Differenzbild: {diff}")
        elif result.passed:
            diff.unlink(missing_ok=True)
        print(f"{'✓' if result.passed else '✕'} {result.scenario_id}: {result.message}")
    write_visual_report(results, args.report, contract_failures)
    return 0 if all(result.passed for result in results) and not contract_failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
