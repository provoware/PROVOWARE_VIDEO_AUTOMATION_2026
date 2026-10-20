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
    assert "from provoware_grid import choose_columns" in source
    assert "intrinsic_min_widths=intrinsic" in source
    assert 'SCALE_LEVELS = (80, 100, 110, 125, 150, 175, 200)' in theme
    assert 'window.view_scale.setCurrentIndex(window.view_scale.findData(110))' in main
    assert 'window.progress_dashboard = QWidget()' in main
    assert "meters.addWidget(window.progress, 0, 1)" in footer
    assert "meters.addWidget(window.job_progress, 1, 1)" in footer
    assert "window.settings_grid = ResponsiveSettingsPanel()" in main
    assert "window.settings_grid.set_zoom_percent(value)" in main
    assert "window.source_columns.set_zoom_percent(value)" in main
    assert "adaptiveSettingScroll" in main


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

        columns.resize(560, 700)
        app.processEvents()
        assert columns.stacked
        assert columns.grid.itemAtPosition(0, 0).widget() is first
        assert columns.grid.itemAtPosition(1, 0).widget() is second
    finally:
        columns.close()


def test_grid_reroutes_on_zoom_and_settings_keep_each_field(monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    pytest.importorskip("PySide6")
    from PySide6.QtWidgets import QApplication, QFrame, QPushButton
    from videobatch_fast.qt_source_panel import ResponsiveSourceColumns
    from videobatch_fast.qt_adaptive_settings import ResponsiveSettingsPanel

    app = QApplication.instance() or QApplication([])
    sources = ResponsiveSourceColumns(QFrame(), QFrame())
    settings = ResponsiveSettingsPanel()
    fields = [QPushButton(f"Feld {index}") for index in range(6)]
    try:
        for index, widget in enumerate(fields):
            settings.add_field(f"Einstellung {index}", widget)
        sources.resize(1300, 400)
        settings.resize(800, 300)
        sources.show()
        settings.show()
        app.processEvents()
        assert not sources.stacked
        assert settings.columns == 2
        assert settings.grid.itemAtPosition(0, 0).widget() is not None
        assert settings.grid.itemAtPosition(0, 1).widget() is not None

        sources.set_zoom_percent(200)
        settings.set_zoom_percent(200)
        app.processEvents()
        assert sources.stacked
        assert settings.columns == 1
        assert settings.grid.itemAtPosition(5, 0).widget() is not None
        assert len({widget.parent() for widget in fields}) == 6
        for button in fields:
            assert button.isVisible()

        sources.set_zoom_percent(80)
        settings.set_zoom_percent(80)
        app.processEvents()
        assert not sources.stacked
        assert settings.columns == 2
    finally:
        sources.close()
        settings.close()

def test_main_window_uses_800_by_600_contract() -> None:
    source = (ROOT / "src/videobatch_fast/qt_ui.py").read_text(encoding="utf-8")
    layout = (ROOT / "src/videobatch_fast/qt_main_layout.py").read_text(encoding="utf-8")
    footer = (ROOT / "src/videobatch_fast/qt_workspace_layout.py").read_text(encoding="utf-8")
    assert "self.setMinimumSize(800, 600)" in source
    assert "self.setMinimumSize(980, 640)" not in source
    assert 'header.addWidget(dashboard, 2, 0, 1, 4)' in layout
    assert 'footer_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)' in footer


@pytest.mark.parametrize("zoom", [80, 100, 110, 125, 150, 175, 200])
def test_action_controls_wrap_and_preserve_buttons(monkeypatch, zoom: int) -> None:
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    pytest.importorskip("PySide6")
    from PySide6.QtWidgets import QApplication, QPushButton
    from videobatch_fast.qt_responsive_controls import ResponsiveControlRow
    from videobatch_fast.qt_theme import scaled_style

    app = QApplication.instance() or QApplication([])
    app.setStyleSheet(scaled_style(zoom))
    buttons = (
        QPushButton("Abbrechen"),
        QPushButton("Probevideo · maximal zehn Sekunden"),
        QPushButton("Videos erstellen"),
    )
    bar = ResponsiveControlRow(buttons)
    try:
        bar.resize(160, 450)
        bar.show()
        bar.set_zoom_percent(zoom)
        app.processEvents()
        assert bar.columns == 1
        for index, button in enumerate(buttons):
            assert bar.grid.itemAtPosition(index, 0).widget() is button
            assert button.isVisible()

        bar.resize(1900, 120)
        app.processEvents()
        assert bar.columns == 3
        for index, button in enumerate(buttons):
            assert bar.grid.itemAtPosition(0, index).widget() is button
    finally:
        bar.close()
