from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src" / "videobatch_fast"

PHASE2_FILES = (
    SRC / "qt_phase2.py",
    SRC / "qt_phase2_components.py",
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
    app = _text(SRC / "qt_phase2.py")
    media = _text(SRC / "qt_media_import_dialog.py")

    assert "SelectionPreviewController" in components
    assert "analyze_audio" in components
    assert "order_images" in components
    assert "apply_anchors" in components
    assert "WaveformSceneView" in components
    assert "QPainter" in components

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
        "Spezialdialoge",
        "Audio-Browser",
        "Medien-Browser",
        "Recovery",
        "Visuelle Freigabe",
    ):
        assert label in source
