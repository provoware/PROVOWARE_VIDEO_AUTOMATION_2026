"""Pilotprüfung: verstellbare Audio-/Medienbreiten ohne Verlust des Umbruchs."""
from __future__ import annotations

import pytest


def test_source_widths_change_and_survive_reflow(monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    pytest.importorskip("PySide6")
    from PySide6.QtWidgets import QApplication, QFrame
    from videobatch_fast.qt_source_panel import ResponsiveSourceColumns

    app = QApplication.instance() or QApplication([])
    first, second = QFrame(), QFrame()
    columns = ResponsiveSourceColumns(first, second)
    try:
        columns.resize(1300, 450)
        columns.show()
        app.processEvents()
        assert not columns.stacked
        assert (columns.grid.columnStretch(0), columns.grid.columnStretch(1)) == (1, 1)
        columns.set_column_ratio(3, 2)
        assert (columns.grid.columnStretch(0), columns.grid.columnStretch(1)) == (3, 2)

        columns.resize(560, 700)
        app.processEvents()
        assert columns.stacked
        assert columns.grid.itemAtPosition(0, 0).widget() is first
        assert columns.grid.itemAtPosition(1, 0).widget() is second
        assert columns.grid.columnStretch(1) == 0
        columns.set_column_ratio(2, 3)

        columns.resize(1300, 450)
        app.processEvents()
        assert not columns.stacked
        assert (columns.grid.columnStretch(0), columns.grid.columnStretch(1)) == (2, 3)
        columns.set_column_ratio(1, 1)
        assert (columns.grid.columnStretch(0), columns.grid.columnStretch(1)) == (1, 1)
    finally:
        columns.close()
