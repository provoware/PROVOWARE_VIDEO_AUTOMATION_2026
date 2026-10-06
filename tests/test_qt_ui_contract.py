from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QT_UI = ROOT / "src" / "videobatch_fast" / "qt_ui.py"
QT_THEME = ROOT / "src" / "videobatch_fast" / "qt_theme.py"
QT_MEDIA_LIST = ROOT / "src" / "videobatch_fast" / "qt_media_list.py"
QT_LOAD_DASHBOARD = ROOT / "src" / "videobatch_fast" / "qt_system_load_dashboard.py"
QT_MAIN_LAYOUT = ROOT / "src" / "videobatch_fast" / "qt_main_layout.py"
QT_WORKSPACE_LAYOUT = ROOT / "src" / "videobatch_fast" / "qt_workspace_layout.py"
QT_SOURCE_PANEL = ROOT / "src" / "videobatch_fast" / "qt_source_panel.py"
QT_UI_POLISH = ROOT / "src" / "videobatch_fast" / "qt_ui_polish.py"
QT_LEGACY_APPEARANCE = ROOT / "src" / "videobatch_fast" / "qt_legacy_appearance.py"
DISPLAY_FORMATTING = ROOT / "src" / "videobatch_fast" / "display_formatting.py"


def _imports(source: str) -> set[str]:
    tree = ast.parse(source)
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


def test_qt_frontend_is_native_and_tk_free() -> None:
    source = QT_UI.read_text(encoding="utf-8")
    imports = _imports(source)

    assert any(name == "PySide6" or name.startswith("PySide6.") for name in imports)
    assert "tkinter" not in imports
    assert not any(name.startswith("tkinter.") for name in imports)
    assert "mainloop(" not in source
    assert "BatchRunner" in source
    assert "build_jobs" in source
    compile(source, str(QT_UI), "exec")


def test_qt_theme_and_dependency_contract_exist() -> None:
    theme = QT_THEME.read_text(encoding="utf-8")
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    requirements = (ROOT / "requirements-qt.txt").read_text(encoding="utf-8")
    runtime_lock = (ROOT / "requirements.lock").read_text(encoding="utf-8")

    assert "APP_STYLE" in theme
    assert 'qt = ["PySide6==6.11.2"]' in pyproject
    assert "-r requirements.lock" in requirements
    assert "PySide6==6.11.2" in runtime_lock


def test_qt_theme_exposes_high_visibility_accessibility_contract() -> None:
    theme = QT_THEME.read_text(encoding="utf-8") + QT_UI_POLISH.read_text(encoding="utf-8")

    for token in (
        "background: #0b1016;",
        "color: #f3f7ff;",
        "border: 2px solid #6f87a3;",
        "QCheckBox {",
        "QCheckBox::indicator {",
        "width: 22px;",
        "height: 22px;",
        "border: 2px solid #dbe8f8;",
        "QCheckBox::indicator:checked {",
        "background: #2f7cff;",
        "border: 2px solid #ffffff;",
        "QLabel#subtitle { color: #e2eaf5; }",
        "border: 2px solid #7f98b8;",
        "selection-color: #ffffff;",
        "background: #007f99;",
        "QPushButton:pressed, QPushButton:checked {",
        "background: #ffbf3f;",
        "QPushButton:focus, QToolButton:focus, QLineEdit:focus, QComboBox:focus,",
        "border: 3px solid #ffffff;",
        "min-height: 34px;",
        "QScrollBar:vertical {",
        "width: 16px;",
        "QToolTip {",
        "SCALE_LEVELS = (100, 125, 150, 175, 200)",
        "def scaled_style(percent: int) -> str:",
        "QPushButton#secondary {",
        "QPushButton#quietDanger {",
        'QLabel#statusChip[state="warning"]',
        'QLabel#statusChip[state="error"]',
        "QTableWidget::item {",
        "QProgressBar#jobProgress::chunk { background: #ffbf3f; }",
    ):
        assert token in theme


def test_qt_dashboard_exposes_total_job_and_activity_feedback() -> None:
    source = "".join(
        path.read_text(encoding="utf-8")
        for path in (QT_UI, QT_MAIN_LAYOUT, QT_WORKSPACE_LAYOUT, QT_UI_POLISH, DISPLAY_FORMATTING)
    )
    for token in (
        '("active", "Aktiv")',
        'QLabel("Gesamt")',
        'QLabel("Auftrag")',
        'window.job_progress.setObjectName("jobProgress")',
        '"Einzel-Fortschritt"',
        'getattr(snap, "job_percent"',
        'getattr(snap, "elapsed_seconds"',
        'getattr(snap, "eta_seconds"',
        'getattr(snap, "last_activity_seconds"',
        'f"Qualität: {spec.resolution}',
        'f"Ziel: {quality_target(spec.key)}',
        '"wird berechnet" if elapsed < 15 else "nicht verfügbar"',
        '"erste Schätzung"',
        '"aktuelle Schätzung"',
        '"⚠ Fehler · Protokoll prüfen"',
        'item.setToolTip("Auftrag fehlgeschlagen.',
        '"Aktueller Programmstatus. Der sichtbare Text nennt den momentanen Zustand."',
        '"Der sichtbare Text nennt den aktuell empfohlenen nächsten Arbeitsschritt."',
        '"Der sichtbare Text beschreibt den aktuellen Arbeitszustand."',
        'window.progress.setAccessibleName("Gesamtfortschritt")',
        'window.job_progress.setAccessibleName("Fortschritt des aktuellen Auftrags")',
        'open_output_folder(window)',
        'QPushButton("Ergebnisprotokoll anzeigen")',
        'self.kpi_values["done"].setText(str(ok))',
        'self._refresh(preserve_results=True)',
        'def _show_start_error(self, message: str, phase: str) -> None:',
        'self._show_start_error(str(data), "Vorbereitung")',
        'self._show_start_error(f"{type(exc).__name__}: {exc}", "Start")',
    ):
        assert token in source
    assert "qt_legacy_parity" not in QT_UI.read_text(encoding="utf-8")


def test_display_formatting_values_and_quality_targets_are_complete() -> None:
    import sys

    sys.path.insert(0, str(ROOT / "src"))
    from videobatch_fast.display_formatting import (
        QUALITY_TARGETS,
        format_clock,
        format_eta,
        format_size,
        quality_target,
    )
    from videobatch_fast.quick_modes import QUICK_MODES

    assert set(QUALITY_TARGETS) == set(QUICK_MODES)
    assert quality_target("unknown") == "Zielprofil nicht verfügbar"
    assert format_clock(-1) == "00:00:00"
    assert format_clock(3661.9) == "01:01:01"
    assert format_size(-1) == "0.0 B"
    assert format_size(1024) == "1.0 KiB"
    assert format_size(1024**2) == "1.0 MiB"
    assert format_eta(None, 5, 0) == "wird berechnet"
    assert format_eta(None, 15, 0) == "nicht verfügbar"
    assert format_eta(30, 10, 5) == "erste Schätzung · ca. 00:00:30"
    assert format_eta(30, 20, 10) == "aktuelle Schätzung · ca. 00:00:30"


def test_media_selection_lists_support_bounded_ctrl_wheel_zoom() -> None:
    source = QT_MEDIA_LIST.read_text(encoding="utf-8")

    for token in (
        "zoomChanged = Signal(int)",
        "MIN_ZOOM_POINT_SIZE = 10.0",
        "MAX_ZOOM_POINT_SIZE = 22.0",
        "def wheelEvent(self, event: QWheelEvent)",
        "def keyPressEvent(self, event: QKeyEvent)",
        "Qt.KeyboardModifier.ControlModifier",
        "event.angleDelta().y() or event.pixelDelta().y()",
        "Qt.Key.Key_Delete",
        "Qt.Key.Key_Plus",
        "Qt.Key.Key_Minus",
        "Qt.Key.Key_0",
        "Strg + Mausrad",
        "Strg + Mausrad oder Strg +/-",
    ):
        assert token in source



def test_media_selection_lists_offer_deterministic_view_sort_without_pairing_drift() -> None:
    source = (
        QT_MEDIA_LIST.read_text(encoding="utf-8")
        + QT_UI.read_text(encoding="utf-8")
        + QT_SOURCE_PANEL.read_text(encoding="utf-8")
    )
    for token in (
        '("Name A–Z", "name")',
        '("Änderung neu → alt", "modified")',
        '("Größe groß → klein", "size")',
        "def media_path_sort_key",
        'if mode == "modified":',
        'if mode == "size":',
        "def sort_by(self, mode: str)",
        "def production_paths(self) -> list[Path]:",
        "production_order = list(self._production_paths)",
        "def apply_view_as_production_order(self) -> None:",
        "Ansicht als Produktionsreihenfolge übernehmen",
        "self.audio.production_paths(), self.media.production_paths()",
    ):
        assert token in source


def test_media_selection_lists_show_metadata_and_image_thumbnails() -> None:
    source = QT_MEDIA_LIST.read_text(encoding="utf-8")
    for token in (
        "def media_size_text(size: int) -> str:",
        "def media_path_display_text(path: Path) -> str:",
        "geändert {changed}",
        "IMAGE_THUMBNAIL_EXTS",
        "item = QListWidgetItem(media_path_display_text(path))",
        "pixmap = QPixmap(resolved)",
        "item.setIcon(QIcon(pixmap))",
        "self.setIconSize(QSize(72, 54))",
        "scale = bounded / 11.0",
    ):
        assert token in source


def test_header_dashboard_exposes_graphical_cpu_ram_swap_load() -> None:
    source = QT_LOAD_DASHBOARD.read_text(encoding="utf-8") + QT_UI.read_text(encoding="utf-8")
    theme = QT_THEME.read_text(encoding="utf-8")
    for token in (
        "SystemLoadSampler",
        "self.timer.setInterval(1000)",
        'for key, label in (("cpu", "CPU"), ("ram", "RAM"), ("swap", "SWAP"))',
        'bar.setAccessibleName(f"{label}-Auslastung")',
        "bar.setAccessibleDescription(tooltip)",
        "def refresh(self)",
        "sample.cpu_percent",
        "sample.ram_percent",
        "sample.swap_percent",
    ):
        assert token in source
    for token in (
        "QFrame#loadDashboard",
        "QLabel#loadLabel",
        "QProgressBar#loadMeter",
        "border: 2px solid #7f98b8;",
    ):
        assert token in theme


def test_main_workspace_supports_global_scaling_without_page_scroll_or_three_column_squeeze() -> None:
    layout = QT_MAIN_LAYOUT.read_text(encoding="utf-8")
    workspace = QT_WORKSPACE_LAYOUT.read_text(encoding="utf-8")
    source = layout + workspace
    for token in (
        'window.view_scale.setAccessibleName("Ansichtsgröße")',
        "for value in SCALE_LEVELS:",
        "build_workflow_stack(window)",
        'stack.setObjectName("workflowPages")',
        '"media": window._sources_panel()',
        '"effects": window._settings_panel()',
        '"queue": window._queue_panel()',
        "set_workflow_route(window, route)",
        "guide.setVisible(route == \"dashboard\")",
        'footer.setVisible(route in {"dashboard", "media", "effects", "queue"})',
        "app.setStyleSheet(scaled_style(value))",
        'view_label.setBuddy(window.view_scale)',
        '("Ctrl+Alt+Up", 1)',
        '("Ctrl+Alt+Down", -1)',
        'QKeySequence("Ctrl+Alt+0")',
        'window.table.verticalHeader().setDefaultSectionSize(round(38 * value / 100))',
        'window.audio.setAccessibleName("Audiodateien")',
        'window.table.setAccessibleName("Automatische Auftragsliste")',
    ):
        assert token in source
    assert "mainWorkspaceScroll" not in layout
    assert "QSplitter" not in layout



def test_output_page_uses_width_instead_of_vertical_scroll_pressure() -> None:
    source = QT_UI.read_text(encoding="utf-8")
    for token in (
        "columns = QHBoxLayout()",
        "columns.addLayout(left, 3)",
        "columns.addLayout(right, 2)",
        "Ziel und Verarbeitung stehen links",
        "Kontrolle und Sicherheit rechts",
    ):
        assert token in source


def test_visual_hierarchy_and_beginner_keyboard_workflow_are_explicit() -> None:
    source = QT_UI.read_text(encoding="utf-8") + QT_UI_POLISH.read_text(encoding="utf-8") + QT_SOURCE_PANEL.read_text(encoding="utf-8")
    for token in (
        'text_label(hint, "panelHint", wrap=True)',
        '"ANALYSE"',
        '"helperText", wrap=True',
        'add.setObjectName("secondary")',
        'remove.setObjectName("quietDanger")',
        'button.setAccessibleDescription("Leert beide Dateilisten.',
        'button.setAccessibleDescription("Wählt den Ordner',
        'configure_secondary_buttons(window.open_output, window.show_result_log)',
        'table.setTextElideMode(Qt.TextElideMode.ElideMiddle)',
        'table.verticalHeader().setDefaultSectionSize(38)',
        '("Alt+1", "media", window.audio)',
        '("Alt+2", "effects", window.output)',
        '("Alt+3", "queue", window.start)',
        'window.audio.setToolTip(window.audio.toolTip() + " · Alt+1: Dateiauswahl")',
        '"Alt+2: Ausgabeordner"',
        '"Alt+3: Videos erstellen"',
        'label.setProperty("state", state)',
        'label.style().unpolish(label)',
        'label.style().polish(label)',
    ):
        assert token in source


def test_accessibility_scaling_composes_with_the_selected_theme() -> None:
    layout = QT_MAIN_LAYOUT.read_text(encoding="utf-8")
    appearance = QT_LEGACY_APPEARANCE.read_text(encoding="utf-8")

    assert 'window.setStyleSheet(_THEME_OVERRIDES.get(theme, ""))' in appearance
    assert "app.setStyleSheet(APP_STYLE" not in appearance
    assert "QKeySequence.StandardKey.ZoomIn" not in layout
    assert "QKeySequence.StandardKey.ZoomOut" not in layout
    assert 'QKeySequence("Ctrl+0")' not in layout
    assert 'window.status.setAccessibleName(' not in layout
    assert 'window.next_step.setAccessibleName(' not in layout
    assert 'window.activity_detail.setAccessibleName(' not in layout


def test_result_preserving_refresh_propagates_through_qt_layers() -> None:
    phase2 = (ROOT / "src" / "videobatch_fast" / "qt_phase2.py").read_text(encoding="utf-8")
    parity = (ROOT / "src" / "videobatch_fast" / "qt_legacy_parity.py").read_text(encoding="utf-8")
    assert "def _refresh(self, *, preserve_results: bool = False)" in phase2
    assert "super()._refresh(preserve_results=preserve_results)" in phase2
    assert "if not preserve_results:" in phase2
    assert "def refresh(self, *, preserve_results: bool = False)" in parity
    assert "original_refresh(self, preserve_results=preserve_results)" in parity
    assert 'self.job_progress.setFormat("Aufträge werden vorbereitet …")' in parity
    assert 'self.kpi_values["active"].setText("Prüfung")' in parity
    assert 'self.activity_detail.setText(f"Aktiv · prüfe {len(audios)} Auftrag/Aufträge mit FFprobe")' in parity
    qt_ui = QT_UI.read_text(encoding="utf-8")
    assert 'self.table.rowCount() - open_' in qt_ui
    assert 'self._row_status(row, "Nicht gestartet", "–")' in qt_ui
    assert 'output_dir = Path(self.output.text().strip()).expanduser()' in qt_ui
    assert 'self.open_output.setEnabled(output_dir.is_dir())' in qt_ui
    assert 'Path(self.output.text().strip()).expanduser().is_dir()' in qt_ui
