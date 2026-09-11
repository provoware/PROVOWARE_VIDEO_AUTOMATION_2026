from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from videobatch_fast.config import load_config
from videobatch_fast.qt_legacy_parity import (
    _archive_last_results,
    _plugin_scan,
    _update_package,
    _visual_approval,
)
from videobatch_fast.qt_legacy_parity_completion import (
    _apply_view_order,
    _remember_directory,
)
from videobatch_fast.qt_phase2 import VideoBatchQtPhase2Window
from videobatch_fast.qt_phase3 import VideoBatchQtPhase3Window


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="videobatch-qt-phase3-") as temporary:
        temporary_path = Path(temporary)
        os.environ["XDG_CONFIG_HOME"] = str(temporary_path / "config")
        os.environ["XDG_STATE_HOME"] = str(temporary_path / "state")
        os.environ["XDG_DATA_HOME"] = str(temporary_path / "data")
        app = QApplication.instance() or QApplication([])

        # The special-tool callbacks must already be replaced before construction,
        # otherwise Qt would retain references to the historical demo handlers.
        assert VideoBatchQtPhase2Window._show_plugin_dialog is _plugin_scan
        assert VideoBatchQtPhase2Window._show_plugin_decision is _plugin_scan
        assert VideoBatchQtPhase2Window._show_update_dialog is _update_package
        assert VideoBatchQtPhase2Window._show_archive_dialog is _archive_last_results
        assert VideoBatchQtPhase2Window._show_visual_approval is _visual_approval

        window = VideoBatchQtPhase3Window(autoload_project=False)
        window.show()
        app.processEvents()

        assert len(window.workspace_navigation.buttons) == 8
        assert window.phase3_tabs.count() == 2
        assert [window.phase3_tabs.tabText(index) for index in range(2)] == [
            "Projekt",
            "Diagnose & Assurance",
        ]

        # Tk -> Qt parity adapters must be fully attached after the first event turn.
        assert window._parity_ready is True
        assert window._parity_completion_ready is True
        assert window.mode.findData("custom") >= 0
        assert window.parity_tabs.count() == 5
        assert [window.parity_tabs.tabText(index) for index in range(5)] == [
            "Einstellungen",
            "Playlist",
            "Kalender",
            "Wartung",
            "Medien & Ansicht",
        ]
        assert window.start.isEnabled(), "Start must stay clickable and explain missing preparation."
        menu_titles = [action.text().replace("&", "") for action in window.menuBar().actions()]
        assert menu_titles == ["Datei", "Medien", "Ansicht", "Produktion", "Werkzeuge", "Hilfe"]

        # Preview parity: the former 25-800 % range plus fit/fullscreen controls is back.
        assert window.preview_panel.parity_zoom.minimum() == 25
        assert window.preview_panel.parity_zoom.maximum() == 800
        assert window.preview_panel._parity_fit_button.text() == "Einpassen"
        assert window.preview_panel._parity_fullscreen_button.text() == "Vollbild"
        window.preview_panel.set_parity_zoom(175, persist=False)
        assert window.preview_panel._parity_zoom == 175
        assert window.preview_panel.parity_zoom.value() == 175

        source_z = temporary_path / "z-source.wav"
        source_a = temporary_path / "a-source.wav"
        media_z = temporary_path / "z-cover.png"
        media_a = temporary_path / "a-cover.png"
        source_z.write_bytes(b"smoke-audio-z")
        source_a.write_bytes(b"smoke-audio-a")
        media_z.write_bytes(b"smoke-image-z")
        media_a.write_bytes(b"smoke-image-a")
        window.audio.add_paths([source_z, source_a])
        window.media.add_paths([media_z, media_a])

        # Sorting changes only the view until the user explicitly accepts it as
        # production order. This restores the old data-safety contract.
        window.parity_audio_sort.setCurrentIndex(window.parity_audio_sort.findData("name_asc"))
        app.processEvents()
        displayed_audio = [
            Path(str(window.audio.item(row).data(Qt.ItemDataRole.UserRole)))
            for row in range(window.audio.count())
        ]
        assert displayed_audio == [source_a.resolve(), source_z.resolve()]
        assert window.audio.paths() == [source_z.resolve(), source_a.resolve()]
        _apply_view_order(window, audio=True)
        assert window.audio.paths() == [source_a.resolve(), source_z.resolve()]

        # Last-used source folders are persisted independently for audio/media.
        _remember_directory(window, "last_audio_dir", [source_a])
        _remember_directory(window, "last_media_dir", [media_a])
        config = load_config()
        assert Path(config["last_audio_dir"]) == temporary_path
        assert Path(config["last_media_dir"]) == temporary_path

        # Independent area zoom is restored and remains separate from global font size.
        window.parity_area_zoom_area.setCurrentIndex(
            window.parity_area_zoom_area.findData("media")
        )
        window.parity_area_zoom_value.setValue(120)
        app.processEvents()
        assert window._parity_area_zoom["media"] == 120

        window.project_panel.name.setText("Phase 3 Smoke")
        window.project_panel.note.setPlainText("Projektzustand muss atomar gespeichert werden.")
        window.parity_playlist.add([source_a])
        window.slideshow._parity_order_mode = "random"
        window.slideshow._manual_seed = 17
        window._parity_calendar_notes["2026-09-11"] = {
            "note": "Parität prüfen",
            "entry_type": "task",
            "color": "active",
        }
        window._parity_calendar_marks["2026-09-11"] = "active"

        # The active Qt workspace is stored inside the project meta block.
        window._route_workspace("queue")
        app.processEvents()
        state = window._collect_project_state()
        assert state["meta"]["qt_active_workspace"] == "queue"
        assert state["audio_sort"] == "import"

        project = temporary_path / "phase3-smoke.vbfast.json"
        window._project_file = project
        assert window._save_current_project()
        payload = json.loads(project.read_text(encoding="utf-8"))
        assert payload["project_name"] == "Phase 3 Smoke"
        assert payload["audio_paths"] == [str(source_a.resolve()), str(source_z.resolve())]
        assert payload["media_paths"] == [str(media_z.resolve()), str(media_a.resolve())]
        assert payload["playlist_paths"] == [str(source_a.resolve())]
        assert payload["slideshow_order_mode"] == "random"
        assert payload["slideshow_random_seed"] == 17
        assert payload["calendar_notes"]["2026-09-11"]["note"] == "Parität prüfen"
        assert payload["meta"]["frontend"] == "qt-phase3"
        assert payload["meta"]["qt_active_workspace"] == "queue"

        for route in window.workspace_navigation.buttons:
            window._route_workspace(route)
            app.processEvents()
        assert window.workspace_navigation.buttons["diagnostics"].property("active") is True

        window._route_workspace("effects")
        app.processEvents()
        assert window.parity_dock.isVisible()
        assert window.parity_tabs.currentIndex() == 0

        window.diagnostics_panel.run_diagnostic()
        app.processEvents()
        assert window.diagnostics_panel.table.rowCount() == 1
        assert window.diagnostics_panel.status.text() in {"GRÜN", "ROT · 1 Fehler"}

        geometry_before_close = f"{window.width()}x{window.height()}"
        window.close()
        for _ in range(5):
            app.processEvents()
        assert not window.isVisible()
        config = load_config()
        assert config["window_geometry"] == geometry_before_close
        assert config["preview_zoom"] == 175
        assert config["area_zoom"]["media"] == 120
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
