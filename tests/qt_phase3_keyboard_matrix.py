"""Tatsächliche Tastatur- und Scroll-Erreichbarkeit bei hoher Schrift prüfen.

Kein Ersatz für die Sichtabnahme am Kubuntu-Rechner.
"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPoint, QRect, Qt
from PySide6.QtWidgets import (
    QApplication, QAbstractButton, QAbstractScrollArea, QAbstractSpinBox,
    QComboBox, QLineEdit, QPlainTextEdit, QPushButton, QSlider,
    QTextEdit, QToolButton,
)

from videobatch_fast.qt_phase3 import VideoBatchQtPhase3Window


def _on_screen(widget, window) -> bool:
    geo = QRect(widget.mapToGlobal(QPoint(0, 0)), widget.size())
    outer = QRect(window.mapToGlobal(QPoint(0, 0)), window.size())
    if not geo.intersects(outer):
        return False
    ancestor = widget.parentWidget()
    while ancestor is not None and ancestor is not window:
        if isinstance(ancestor, QAbstractScrollArea):
            viewport = ancestor.viewport()
            visible = QRect(viewport.mapToGlobal(QPoint(0, 0)), viewport.size())
            if not geo.intersects(visible):
                return False
        ancestor = ancestor.parentWidget()
    return True


def run() -> int:
    with tempfile.TemporaryDirectory(prefix="videobatch-qt-keyboard-") as root:
        base = Path(root)
        os.environ.update({
            "XDG_CONFIG_HOME": str(base / "config"),
            "XDG_STATE_HOME": str(base / "state"),
            "XDG_DATA_HOME": str(base / "data"),
            "XDG_CACHE_HOME": str(base / "cache"),
        })
        app = QApplication.instance() or QApplication([])
        window = VideoBatchQtPhase3Window(autoload_project=False)
        window.show()
        app.processEvents()
        issues = []
        checks = 0
        try:
            for scale in (175, 200):
                window.view_scale.setCurrentIndex(window.view_scale.findData(scale))
                window.resize(800, 600)
                app.processEvents()
                for page, label in ((0, "dateien"), (1, "ausgabe"), (2, "produktion")):
                    window.main_tabs.setCurrentIndex(page)
                    app.processEvents()
                    # Controls hidden by design (e.g. advanced tool docks)
                    # are not part of the currently offered beginner workflow.
                    controls = [
                        w for cls in (
                            QAbstractButton, QAbstractSpinBox, QComboBox,
                            QLineEdit, QPlainTextEdit, QTextEdit, QSlider,
                        ) for w in window.findChildren(cls)
                        if w.isVisibleTo(window) and w.isEnabled()
                        and w.focusPolicy() != Qt.FocusPolicy.NoFocus
                        and (not isinstance(w, QAbstractButton) or bool(w.text().strip()))
                    ]
                    for widget in controls:
                        checks += 1
                        widget.setFocus(Qt.FocusReason.TabFocusReason)
                        app.processEvents()
                        if QApplication.focusWidget() is not widget:
                            issues.append(f"{label} {scale}%: Tastaturfokus fehlt bei {(widget.text()[:35] if hasattr(widget, 'text') else type(widget).__name__)}")
                            continue
                        if not _on_screen(widget, window):
                            issues.append(f"{label} {scale}%: Nicht in den sichtbaren Scrollbereich gelangt: {widget.text()[:35]}")
        finally:
            window.close()
            app.processEvents()
        print(json.dumps({
            "status": "passed" if not issues else "failed",
            "cases": 6, "focused_controls": checks, "problems": issues,
        }, ensure_ascii=False, indent=2))
        return 0 if not issues and checks >= 12 else 1


if __name__ == "__main__":
    raise SystemExit(run())
