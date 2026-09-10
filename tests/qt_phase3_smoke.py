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
        os.environ["XDG_STATE_HOME"] = str(Path(temporary) / "state")
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

        source = Path(temporary) / "source.wav"
        media = Path(temporary) / "cover.png"
        source.write_bytes(b"smoke-audio")
        media.write_bytes(b"smoke-image")
        window.audio.add_paths([source])
        window.media.add_paths([media])
        window.project_panel.name.setText("Phase 3 Smoke")
        window.project_panel.note.setPlainText("Projektzustand muss atomar gespeichert werden.")

        project = Path(temporary) / "phase3-smoke.vbfast.json"
        window._project_file = project
        assert window._save_current_project()
        payload = json.loads(project.read_text(encoding="utf-8"))
        assert payload["project_name"] == "Phase 3 Smoke"
        assert payload["audio_paths"] == [str(source.resolve())]
        assert payload["media_paths"] == [str(media.resolve())]
        assert payload["meta"]["frontend"] == "qt-phase3"

        for route in window.workspace_navigation.buttons:
            window._route_workspace(route)
            app.processEvents()
        assert window.workspace_navigation.buttons["diagnostics"].property("active") is True

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
