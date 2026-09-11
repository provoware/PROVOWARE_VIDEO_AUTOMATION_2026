from __future__ import annotations

import os
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from videobatch_fast.qt_media_import_dialog import MediaImportDialog
from videobatch_fast.qt_phase2 import VideoBatchQtPhase2Window
from videobatch_fast.qt_workflow_dialogs import (
    PluginPermissionDecisionDialog,
    VisualApprovalSignDialog,
    recovery_dialog,
)


def main() -> int:
    app = QApplication.instance() or QApplication([])
    window = VideoBatchQtPhase2Window()
    window.show()
    app.processEvents()

    assert window.phase2_tabs.count() == 3
    assert [window.phase2_tabs.tabText(index) for index in range(3)] == [
        "Vorschau",
        "Diashow & Waveform",
        "Weitere Werkzeuge",
    ]
    assert window.slideshow.assignment.count() == 2
    assert window.slideshow.transition.count() >= 4
    assert window.preview_panel._controller is not None

    recovery = recovery_dialog(window, "QT-SMOKE", modal=False)
    permission = PluginPermissionDecisionDialog(window, "Smoke-Test", "missing", modal=False)
    visual = VisualApprovalSignDialog(window, "qt-phase2-smoke", modal=False)
    for dialog in (recovery, permission, visual):
        dialog.show()
        app.processEvents()
        assert dialog.isVisible()
        dialog.close()

    with tempfile.TemporaryDirectory(prefix="videobatch-qt-media-") as temporary:
        browser = MediaImportDialog(
            window,
            audio=False,
            initial_dir=Path(temporary),
            modal=False,
        )
        browser.show()
        for _ in range(5):
            app.processEvents()
        assert browser.current_dir == Path(temporary)
        browser.close()
        app.processEvents()

    window.close()
    for _ in range(5):
        app.processEvents()
    assert not window.isVisible()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
