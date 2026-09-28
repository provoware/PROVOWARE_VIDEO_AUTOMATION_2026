from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QT_UI = ROOT / "src" / "videobatch_fast" / "qt_ui.py"
QT_THEME = ROOT / "src" / "videobatch_fast" / "qt_theme.py"


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
    theme = QT_THEME.read_text(encoding="utf-8")

    for token in (
        "background: #0b1016;",
        "color: #f3f7ff;",
        "border: 1px solid #526985;",
        "QCheckBox {",
        "QCheckBox::indicator {",
        "width: 22px;",
        "height: 22px;",
        "selection-color: #ffffff;",
    ):
        assert token in theme


def test_media_selection_lists_support_bounded_ctrl_wheel_zoom() -> None:
    source = QT_UI.read_text(encoding="utf-8")

    for token in (
        "zoomChanged = Signal(int)",
        "MIN_ZOOM_POINT_SIZE = 10.0",
        "MAX_ZOOM_POINT_SIZE = 22.0",
        "def wheelEvent(self, event: QWheelEvent)",
        "Qt.KeyboardModifier.ControlModifier",
        "event.angleDelta().y() or event.pixelDelta().y()",
        "Strg + Mausrad",
    ):
        assert token in source
