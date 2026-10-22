from __future__ import annotations

import ast
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src" / "videobatch_fast"

PHASE2_FILES = (
    SRC / "qt_phase2.py",
    SRC / "qt_phase2_components.py",
    SRC / "qt_phase2_selection_preview.py",
    SRC / "qt_preview_panel.py",
    SRC / "qt_media_import_dialog.py",
    SRC / "qt_workflow_dialogs.py",
)


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_phase2_qt_modules_are_tk_free_and_parseable() -> None:
    for path in PHASE2_FILES:
        source = _text(path)
        ast.parse(source, filename=str(path))
        lowered = source.casefold()
        assert "tkinter" not in lowered
        assert "imagetk" not in lowered
        assert "toplevel(" not in lowered
        assert "mainloop(" not in lowered
        assert "pyside6" in lowered


def test_phase2_reuses_verified_core_services() -> None:
    components = _text(SRC / "qt_phase2_components.py")
    preview = _text(SRC / "qt_preview_panel.py")
    app = _text(SRC / "qt_phase2.py")
    media = _text(SRC / "qt_media_import_dialog.py")

    assert "PreviewPanel" in components
    assert "SelectionPreviewController" in preview
    assert "analyze_audio" in components
    assert "order_images" in components
    assert "apply_anchors" in components
    assert "WaveformSceneView" in components
    assert "QPainter" in components
    assert "EventBuffer" in preview

    assert "build_jobs" in app
    assert "scene_analyses=analyses" in app
    assert "SLIDESHOW_MODE_ALL_IMAGES" in app
    assert "VideoBatchQtWindow" in app

    assert "scan_directory_batches" in media
    assert "safe_media_directory" in media
    assert "PreviewPanel" in media


def test_requested_special_dialog_parity_is_present() -> None:
    source = _text(SRC / "qt_workflow_dialogs.py")
    tree = ast.parse(source)
    classes = {node.name for node in tree.body if isinstance(node, ast.ClassDef)}
    functions = {node.name for node in tree.body if isinstance(node, ast.FunctionDef)}

    assert {
        "GuidedDecisionDialog",
        "PluginPermissionDecisionDialog",
        "VisualApprovalSignDialog",
    } <= classes
    assert {
        "plugin_permission_dialog",
        "update_assistant_dialog",
        "archive_preview_dialog",
        "recovery_dialog",
    } <= functions


def test_phase2_entrypoint_contains_all_requested_workflows() -> None:
    source = _text(SRC / "qt_phase2.py")
    for label in (
        "Vorschau",
        "Diashow & Waveform",
        "Weitere Werkzeuge",
        "Audio-Browser",
        "Medien-Browser",
        "Recovery",
        "Visuelle Freigabe",
    ):
        assert label in source


def test_beginner_slideshow_keeps_primary_options_fixed_above_secondary_scroll() -> None:
    source = _text(SRC / "qt_phase2_components.py")
    build = source.index("class SlideshowPanel")
    assignment = source.index("self.assignment = QComboBox()", build)
    transition = source.index("self.transition = QComboBox()", build)
    scene_sync = source.index("self.scene_sync = QCheckBox", build)
    scroll = source.index("scroll = QScrollArea()", build)
    ordering = source.index('order_hint = QLabel("Optional: Bildreihenfolge ändern")', build)

    assert assignment < scroll
    assert transition < scroll
    assert scene_sync < scroll
    assert scroll < ordering
    assert 'scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)' in source
    assert "Die drei Grundoptionen bleiben immer sichtbar" in source


def test_selecting_audio_or_media_routes_preview_without_squeezing_file_page() -> None:
    source = _text(SRC / "qt_phase2_selection_preview.py")
    app = _text(SRC / "qt_phase2.py")
    assert "class SelectionPreviewMixin" in source
    assert 'route("preview")' in source
    assert "self.phase2_dock.show()" in source
    assert "self.phase2_dock.raise_()" in source
    assert "self.phase2_tabs.setCurrentWidget(self.preview_panel)" in source
    assert source.count("self._show_selection_preview()") == 2
    assert "SelectionPreviewMixin" in app


def test_source_widths_change_and_survive_reflow(monkeypatch):
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
        assert columns.splitter.orientation() == Qt.Horizontal
        assert isinstance(columns.splitter.handle(1), QSplitterHandle)
        columns.set_column_ratio(3, 2)
        app.processEvents()
        sizes = columns.splitter.sizes()
        assert 1.25 < sizes[0] / max(1, sizes[1]) < 1.75

        # Derselbe native Trennstrich kann beliebige Zwischenpositionen annehmen.
        columns.splitter.moveSplitter(430, 1)
        app.processEvents()
        manually_selected = columns.column_ratio
        assert manually_selected == tuple(columns.splitter.sizes())
        assert manually_selected != (3, 2)

        columns.resize(560, 700)
        app.processEvents()
        assert columns.stacked
        assert columns.splitter.orientation() == Qt.Vertical

        columns.resize(1300, 450)
        app.processEvents()
        assert not columns.stacked
        assert columns.splitter.orientation() == Qt.Horizontal
        ratio = columns.splitter.sizes()
        assert abs(ratio[0] / max(1, ratio[1]) - manually_selected[0] / manually_selected[1]) < 0.25
        columns.set_column_ratio(1, 1)
        app.processEvents()
        equal = columns.splitter.sizes()
        assert abs(equal[0] - equal[1]) < 25
    finally:
        columns.close()
