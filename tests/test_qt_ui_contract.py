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
        "background: #05070a;",
        "color: #ffffff;",
        "background: #1f2c3c;",
        "border: 2px solid #9db7d6;",
        "QLabel#subtitle { color: #eef4ff; }",
        "QCheckBox {",
        "QCheckBox::indicator {",
        "width: 26px;",
        "height: 26px;",
        "border: 3px solid #f7fbff;",
        "QCheckBox::indicator:checked {",
        "background: #1687ff;",
        "QCheckBox::indicator:hover {",
        "border-color: #ffd166;",
        "QComboBox QAbstractItemView {",
        "selection-color: #ffffff;",
    ):
        assert token in theme
