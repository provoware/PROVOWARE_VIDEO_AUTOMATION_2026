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
    assert "window.settings_view = window.settings_grid" in main
    assert "adaptiveSettingScroll" not in main


def test_equal_columns_reflow_to_vertical_stack(monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    pytest.importorskip("PySide6")
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication, QFrame, QSplitterHandle
    from videobatch_fast.qt_source_panel import ResponsiveSourceColumns

    app = QApplication.instance() or QApplication([])
    first, second = QFrame(), QFrame()
    columns = ResponsiveSourceColumns(first, second)
    try:
        columns.resize(1300, 450)
        columns.show()
        app.processEvents()
        assert not columns.stacked
        assert columns.splitter.orientation() == Qt.Horizontal
        assert columns.splitter.widget(0) is first
        assert columns.splitter.widget(1) is second
        assert isinstance(columns.splitter.handle(1), QSplitterHandle)

        columns.resize(560, 700)
        app.processEvents()
        assert columns.stacked
        assert columns.splitter.orientation() == Qt.Vertical
        assert columns.splitter.widget(0) is first
        assert columns.splitter.widget(1) is second
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


def test_compact_header_keeps_status_load_meters_zoom_and_menu() -> None:
    """U1 must save a full header row without hiding operational information."""
    source = (ROOT / "src/videobatch_fast/qt_main_layout.py").read_text(encoding="utf-8")
    assert "heading.addWidget(title, alignment=Qt.AlignmentFlag.AlignVCenter)" in source
    assert "compact_brand = value >= 150 and window.width() <= 1100" in source
    assert "heading.addWidget(window.status, alignment=Qt.AlignmentFlag.AlignVCenter)" in source
    assert "header.addLayout(brand, 0, 0, 1, 2)" in source
    assert "header.addLayout(view_row, 0, 3)" in source
    assert "header.addWidget(window.compact_menu, 0, 2)" in source
    assert "dashboard_row = QHBoxLayout(dashboard)" in source
    assert "dashboard_row.addWidget(window.load_dashboard.frame)" in source
    assert "dashboard_row.addWidget(window.progress_dashboard, 1)" in source
    footer_source = (ROOT / "src/videobatch_fast/qt_workspace_layout.py").read_text(encoding="utf-8")
    assert "window.next_step.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)" in footer_source
    for existing_contract in (
        'window.status.setAccessibleDescription(',
        'window.view_scale.setAccessibleName("Schrift- und Ansichtsgröße")',
        'window.compact_menu.clicked.connect(open_compact_menu)',
        'window.progress_dashboard_layout = QGridLayout(window.progress_dashboard)',
        'header.addWidget(dashboard, 2, 0, 1, 4)',
    ):
        assert existing_contract in source


def test_media_import_actions_stay_above_scrolling_lists_and_keep_callbacks(monkeypatch):
    """U2: the original import commands remain accessible when the lists scroll."""
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    pytest.importorskip("PySide6")
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication, QFrame, QVBoxLayout, QWidget
    from videobatch_fast.qt_source_panel import build_sources_panel

    app = QApplication.instance() or QApplication([])

    class MediaHost(QWidget):
        def __init__(self):
            super().__init__()
            self._responsive_control_rows = []
            self.calls = []
            self.main_layout = QVBoxLayout(self)

        def _panel(self, title, hint):
            frame = QFrame()
            return frame, QVBoxLayout(frame)

        def _choose_audio(self):
            self.calls.append("audio")

        def _choose_media(self):
            self.calls.append("media")

    host = MediaHost()
    scroll = build_sources_panel(host)
    host.main_layout.addWidget(host.media_import_bar)
    host.main_layout.addWidget(scroll, 1)
    try:
        host.resize(800, 600)
        host.show()
        host.media_import_bar.set_zoom_percent(200)
        app.processEvents()
        assert host.media_import_bar.objectName() == "mediaImportToolbar"
        assert host.media_import_bar.parent() is host
        assert scroll.widget() is not host.media_import_bar
        assert host.media_import_bar.isVisibleTo(host)
        assert len(host._source_import_buttons) == 2
        audio, media = host._source_import_buttons
        assert host.media_import_bar.controls == (audio, media)
        assert audio.accessibleName() == "Audio auswählen …"
        assert media.accessibleName() == "Bilder/Videos auswählen …"
        audio.click()
        media.click()
        assert host.calls == ["audio", "media"]
        scroll.verticalScrollBar().setValue(scroll.verticalScrollBar().maximum())
        app.processEvents()
        assert host.media_import_bar.isVisibleTo(host)
        assert host.source_columns.splitter.widget(0) is host.source_columns.audio_card
        assert host.source_columns.splitter.widget(1) is host.source_columns.media_card
        remove_buttons = [
            button for button, full, _short in host._source_action_labels
            if full == "Entfernen"
        ]
        assert len(remove_buttons) == 2
        assert all(button.parentWidget() is not host.media_import_bar for button in remove_buttons)
    finally:
        host.close()


def test_media_toolbar_route_contract_and_existing_ordering_are_preserved():
    source = (ROOT / "src/videobatch_fast/qt_source_panel.py").read_text(encoding="utf-8")
    main = (ROOT / "src/videobatch_fast/qt_main_layout.py").read_text(encoding="utf-8")
    routes = (ROOT / "src/videobatch_fast/qt_workspace_layout.py").read_text(encoding="utf-8")
    assert "outer.addWidget(window.media_import_bar)" in main
    assert 'import_bar.setVisible(page_key == "media")' in routes
    assert "window._source_import_buttons.append(add)" in source
    assert "layout.addWidget(remove, 0, Qt.AlignmentFlag.AlignRight)" in source
    for contract in (
        "add.clicked.connect(window._choose_audio if widget is window.audio else window._choose_media)",
        "remove.clicked.connect(widget.remove_selected)",
        "sorter.currentIndexChanged.connect(",
        "window.source_columns.splitter.splitterMoved.connect(",
        "adopt.clicked.connect(window.audio.apply_view_as_production_order)",
        "adopt.clicked.connect(window.media.apply_view_as_production_order)",
        "scroll.setWidget(panel)",
    ):
        assert contract in source


@pytest.mark.parametrize("size, zoom", [
    ((1366, 768), 110),
    ((1024, 768), 175),
    ((800, 600), 200),
])
def test_output_page_uses_one_scroll_area_and_preserves_controls(
    monkeypatch, tmp_path, size: tuple[int, int], zoom: int
) -> None:
    """U3 guards the real output-widget hierarchy, routes, and saved values."""
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    for key, folder in (
        ("HOME", "home"), ("XDG_CONFIG_HOME", "config"),
        ("XDG_STATE_HOME", "state"), ("XDG_DATA_HOME", "data"),
        ("XDG_CACHE_HOME", "cache"),
    ):
        location = tmp_path / folder
        location.mkdir(exist_ok=True)
        monkeypatch.setenv(key, str(location))
    pytest.importorskip("PySide6")
    from PySide6.QtWidgets import QApplication, QScrollArea
    from videobatch_fast.qt_phase3 import VideoBatchQtPhase3Window

    app = QApplication.instance() or QApplication([])
    window = VideoBatchQtPhase3Window(autoload_project=False)
    try:
        window.resize(*size)
        window.show()
        window.view_scale.setCurrentIndex(window.view_scale.findData(zoom))
        window.main_tabs.setCurrentIndex(1)
        app.processEvents()

        output_page = window._workflow_pages["effects"]
        assert isinstance(output_page, QScrollArea)
        assert window.settings_view is window.settings_grid
        assert window.settings_grid.isVisibleTo(window)
        assert output_page.verticalScrollBar().value() == 0

        # No second QScrollArea may surround everyday settings.
        ancestor = window.settings_grid.parentWidget()
        scrolls = []
        while ancestor is not None:
            if isinstance(ancestor, QScrollArea):
                scrolls.append(ancestor)
            ancestor = ancestor.parentWidget()
        assert scrolls == [output_page]
        assert len(window.settings_grid._fields) == 6

        values = (
            window.resolution.currentData(), window.quality.currentData(),
            window.effect.currentData(), window.output.text(),
            window.effect_intensity.value(), window.transition.currentData(),
            window.fade_seconds.value(), window.verification.currentText(),
        )
        assert all(control.isVisibleTo(window) for control in (
            window.resolution, window.quality, window.effect, window.output,
            window.effect_intensity, window.transition, window.fade_seconds,
            window.verification,
        ))
        assert output_page.widget().layout().itemAt(0).widget().text() == "Grundeinstellungen"
        assert window.resolution.mapTo(window, window.resolution.rect().topLeft()).y() < window.height()

        # Expanded expert controls remain reachable via the *same* scrollbar.
        window.exclusions_toggle.setChecked(True)
        window.details_toggle.setChecked(True)
        app.processEvents()
        assert window.media_exclusions.isVisibleTo(window)
        assert window.safety_details.isVisibleTo(window)
        output_page.verticalScrollBar().setValue(output_page.verticalScrollBar().maximum())
        app.processEvents()
        window.main_tabs.setCurrentIndex(2)
        window.main_tabs.setCurrentIndex(1)
        app.processEvents()
        assert output_page.verticalScrollBar().value() == 0
        assert values == (
            window.resolution.currentData(), window.quality.currentData(),
            window.effect.currentData(), window.output.text(),
            window.effect_intensity.value(), window.transition.currentData(),
            window.fade_seconds.value(), window.verification.currentText(),
        )
    finally:
        window.close()
        app.processEvents()
