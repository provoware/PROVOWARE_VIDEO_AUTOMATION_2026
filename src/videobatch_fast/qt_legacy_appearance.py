from __future__ import annotations

from typing import Any

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

from .config import save_config
from .qt_theme import scaled_style


def apply_theme(window: Any, percent: int | None = None) -> None:
    """Keep both size controls, saved settings and Qt's actual style in sync."""
    app = QApplication.instance()
    if app is None:
        return
    theme_control = getattr(window, "parity_theme", None)
    theme = str(theme_control.currentData() or "neon_gravity") if theme_control else "neon_gravity"
    size_control = getattr(window, "parity_font_scale", None)
    scale = max(80, min(200, int(percent if percent is not None else size_control.value())))
    for control in (window.view_scale, size_control):
        if control is None:
            continue
        blocked = control.blockSignals(True)
        try:
            if control is window.view_scale:
                index = control.findData(scale)
                if index < 0:
                    index = next((i for i in range(control.count()) if control.itemData(i) > scale), control.count())
                    control.insertItem(index, f"{scale} %", scale)
                control.setCurrentIndex(index)
            else:
                control.setValue(scale)
        finally:
            control.blockSignals(blocked)
    # No window-wide QWidget rule may override the semantic button/status roles.
    if window.styleSheet():
        window.setStyleSheet("")
    font = QFont(app.font())
    font.setPointSizeF(12.0 * scale / 100.0)
    if app.font() != font:
        app.setFont(font)
    style = scaled_style(scale, theme)
    if app.styleSheet() != style:
        app.setStyleSheet(style)
    cfg = getattr(window, "_parity_config", None)
    if getattr(window, "_parity_ready", False) and isinstance(cfg, dict):
        if cfg.get("font_scale") != scale or cfg.get("theme") != theme:
            updated = dict(cfg, font_scale=scale, theme=theme)
            save_config(updated)
            window._parity_config = updated
    # A change in the settings panel also needs the main layout's reflow rules.
    if percent is None and hasattr(window, "_apply_view_scale"):
        window._apply_view_scale()
