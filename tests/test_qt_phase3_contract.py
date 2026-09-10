from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src" / "videobatch_fast"

PHASE3_FILES = (
    SRC / "qt_phase3.py",
    SRC / "qt_phase3_components.py",
)


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_phase3_qt_modules_are_tk_free_and_parseable() -> None:
    for path in PHASE3_FILES:
        source = _text(path)
        ast.parse(source, filename=str(path))
        lowered = source.casefold()
        assert "tkinter" not in lowered
        assert "toplevel(" not in lowered
        assert "mainloop(" not in lowered
        assert "pyside6" in lowered


def test_phase3_reuses_verified_project_and_assurance_services() -> None:
    app = _text(SRC / "qt_phase3.py")
    components = _text(SRC / "qt_phase3_components.py")

    for symbol in (
        "load_project_state",
        "save_project_state",
        "projects_dir",
        "build_diagnostic_payload",
        "VideoBatchQtPhase2Window",
    ):
        assert symbol in app

    for symbol in (
        "run_scenarios",
        "run_fault_lab",
        "WorkspaceNavigationPanel",
        "ProjectPanel",
        "DiagnosticsPanel",
    ):
        assert symbol in components


def test_phase3_workspace_routes_cover_complete_operator_flow() -> None:
    source = _text(SRC / "qt_phase3_components.py")
    for route in (
        "dashboard",
        "media",
        "preview",
        "slideshow",
        "effects",
        "queue",
        "project",
        "diagnostics",
    ):
        assert f'(\"{route}\",' in source


def test_project_persistence_is_fail_safe_during_active_processing() -> None:
    source = _text(SRC / "qt_phase3.py")
    tree = ast.parse(source)
    functions = {
        node.name: node
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    assert "_autosave_project" in functions
    assert "_save_current_project" in functions
    assert "runner.running" in source
    assert "self.preparing" in source
    assert "AUTOSAVE_INTERVAL_MS = 300_000" in source


def test_phase3_does_not_switch_the_legacy_entrypoint_yet() -> None:
    app = _text(SRC / "app.py")
    phase3 = _text(SRC / "qt_phase3.py")
    assert "from .canonical_ui import run_app" in app
    assert "def main()" in phase3
    assert "VideoBatchQtPhase3Window" in phase3
