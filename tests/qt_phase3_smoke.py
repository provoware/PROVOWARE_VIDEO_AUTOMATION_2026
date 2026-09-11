from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from videobatch_fast.qt_phase3 import VideoBatchQtPhase3Window


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="videobatch-qt-phase3-") as temporary:
        temporary_path = Path(temporary)
        os.environ["XDG_CONFIG_HOME"] = str(temporary_path / "config")
        os.environ["XDG_STATE_HOME"] = str(temporary_path / "state")
        os.environ["XDG_DATA_HOME"] = str(temporary_path / "data")
        app = QApplication.instance() or QApplication([])
        window = VideoBatchQtPhase3Window(autoload_project=False)
        window.show()
        app.processEvents()

        assert len(window.workspace_navigation.buttons) == 8
        assert window.phase3_tabs.count() == 2
        assert [window.phase3_tabs.tabText(index) for index in range(2)] == [
            "Projekt",
            "Diagnose & Assurance",
        ]

        # Tk -> Qt parity adapter must be fully attached after the first event turn.
        assert window._parity_ready is True
        assert window.mode.findData("custom") >= 0
        assert window.parity_tabs.count() == 4
        assert [window.parity_tabs.tabText(index) for index in range(4)] == [
            "Einstellungen",
            "Playlist",
            "Kalender",
            "Wartung",
        ]
        assert window.start.isEnabled(), "Start must stay clickable and explain missing preparation."
        menu_titles = [action.text().replace("&", "") for action in window.menuBar().actions()]
        assert menu_titles == ["Datei", "Medien", "Ansicht", "Produktion", "Werkzeuge", "Hilfe"]

        source = temporary_path / "source.wav"
        media = temporary_path / "cover.png"
        source.write_bytes(b"smoke-audio")
        media.write_bytes(b"smoke-image")
        window.audio.add_paths([source])
        window.media.add_paths([media])
        window.project_panel.name.setText("Phase 3 Smoke")
        window.project_panel.note.setPlainText("Projektzustand muss atomar gespeichert werden.")
        window.parity_playlist.add([source])
        window.slideshow._parity_order_mode = "random"
        window.slideshow._manual_seed = 17
        window._parity_calendar_notes["2026-09-11"] = {
            "note": "Parität prüfen",
            "entry_type": "task",
            "color": "active",
        }
        window._parity_calendar_marks["2026-09-11"] = "active"

        project = temporary_path / "phase3-smoke.vbfast.json"
        window._project_file = project
        assert window._save_current_project()
        payload = json.loads(project.read_text(encoding="utf-8"))
        assert payload["project_name"] == "Phase 3 Smoke"
        assert payload["audio_paths"] == [str(source.resolve())]
        assert payload["media_paths"] == [str(media.resolve())]
        assert payload["playlist_paths"] == [str(source.resolve())]
        assert payload["slideshow_order_mode"] == "random"
        assert payload["slideshow_random_seed"] == 17
        assert payload["calendar_notes"]["2026-09-11"]["note"] == "Parität prüfen"
        assert payload["meta"]["frontend"] == "qt-phase3"

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

        window.close()
        for _ in range(5):
            app.processEvents()
        assert not window.isVisible()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
