from __future__ import annotations

from typing import Any

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

from .qt_theme import APP_STYLE

_THEME_OVERRIDES = {
    "neon_gravity": """
        QMainWindow, QWidget { background-color: #10141b; color: #eef4ff; }
        QFrame#panel, QFrame#card { background-color: #171d27; }
    """,
    "acid_paper": """
        QMainWindow, QWidget { background-color: #f2f0d8; color: #1b2415; }
        QFrame#panel, QFrame#card { background-color: #fffde8; }
        QLineEdit, QListWidget, QComboBox { background-color: #ffffff; color: #172012; }
    """,
    "toxic_candy": """
        QMainWindow, QWidget { background-color: #1b1020; color: #fff0fb; }
        QFrame#panel, QFrame#card { background-color: #28152f; }
    """,
    "ultraviolet": """
        QMainWindow, QWidget { background-color: #151126; color: #f2edff; }
        QFrame#panel, QFrame#card { background-color: #201936; }
    """,
}


def apply_theme(window: Any) -> None:
    app = QApplication.instance()
    if app is None:
        return
    theme = str(window.parity_theme.currentData() or "neon_gravity")
    scale = int(window.parity_font_scale.value())
    app.setStyleSheet(APP_STYLE + "\n" + _THEME_OVERRIDES.get(theme, ""))
    font = QFont(app.font())
    base = float(getattr(window, "_parity_base_font_size", 10.0) or 10.0)
    font.setPointSizeF(max(7.0, base * scale / 100.0))
    app.setFont(font)
