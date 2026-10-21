"""Native Qt geometry contracts for responsive media columns and compact status."""
from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_responsive_layout_contract_is_readable_without_horizontal_scrolling():
    source = (ROOT / "src/videobatch_fast/qt_source_panel.py").read_text(encoding="utf-8")
    main = (ROOT / "src/videobatch_fast/qt_main_layout.py").read_text(encoding="utf-8")
    footer = (ROOT / "src/videobatch_fast/qt_workspace_layout.py").read_text(encoding="utf-8")
    theme = (ROOT / "src/videobatch_fast/qt_theme.py").read_text(encoding="utf-8")
    assert "class ResponsiveSourceColumns(QWidget)" in source
    assert "ScrollBarAlwaysOff" in source
    assert "scroll.setWidget(panel)" in source
    assert "fontMetrics().height()" in source
    assert 'SCALE_LEVELS = (80, 100, 110, 125, 150, 175, 200)' in theme
    assert 'window.view_scale.setCurrentIndex(window.view_scale.findData(110))' in main
    assert 'window.progress_dashboard = QWidget()' in main
    assert "meters.addWidget(window.progress, 0, 1)" in footer
    assert "meters.addWidget(window.job_progress, 1, 1)" in footer


def test_equal_columns_reflow_to_vertical_stack(monkeypatch):
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
        assert columns.grid.itemAtPosition(0, 0).widget() is first
        assert columns.grid.itemAtPosition(0, 1).widget() is second
        columns.set_column_ratio(3, 2)
        assert (columns.grid.columnStretch(0), columns.grid.columnStretch(1)) == (3, 2)

        columns.resize(560, 700)
        app.processEvents()
        assert columns.stacked
        assert columns.grid.itemAtPosition(0, 0).widget() is first
        assert columns.grid.itemAtPosition(1, 0).widget() is second
        assert columns.grid.columnStretch(1) == 0
        columns.resize(1300, 450)
        app.processEvents()
        assert not columns.stacked
        assert (columns.grid.columnStretch(0), columns.grid.columnStretch(1)) == (3, 2)
        columns.set_column_ratio(1, 1)
        assert (columns.grid.columnStretch(0), columns.grid.columnStretch(1)) == (1, 1)
    finally:
        columns.close()
