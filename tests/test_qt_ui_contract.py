from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QT_UI = ROOT / "src" / "videobatch_fast" / "qt_ui.py"
QT_THEME = ROOT / "src" / "videobatch_fast" / "qt_theme.py"
QT_MEDIA_LIST = ROOT / "src" / "videobatch_fast" / "qt_media_list.py"
QT_LOAD_DASHBOARD = ROOT / "src" / "videobatch_fast" / "qt_system_load_dashboard.py"


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
    ):
        assert token in theme


def test_media_selection_lists_support_bounded_ctrl_wheel_zoom() -> None:
    source = QT_MEDIA_LIST.read_text(encoding="utf-8")

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



def test_media_selection_lists_offer_deterministic_sort_modes() -> None:
    source = QT_MEDIA_LIST.read_text(encoding="utf-8") + QT_UI.read_text(encoding="utf-8")
    for token in (
        '("Name A–Z", "name")',
        '("Änderung neu → alt", "modified")',
        '("Größe groß → klein", "size")',
        "def media_path_sort_key",
        'if mode == "modified":',
        'if mode == "size":',
        "def sort_by(self, mode: str)",
        "selected = {str(item.data(Qt.ItemDataRole.UserRole))",
        "Sortieren ordnet die jeweilige Liste neu",
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
