from __future__ import annotations

from .qt_style_data import APP_STYLE

from .qt_ui_polish import VISUAL_HIERARCHY_STYLE



APP_STYLE += VISUAL_HIERARCHY_STYLE

SCALE_LEVELS = (80, 100, 110, 125, 150, 175, 200)


def scaled_style(percent: int) -> str:
    scale = min(SCALE_LEVELS, key=lambda value: abs(value - int(percent))) / 100.0
    return APP_STYLE + f"""
QWidget {{ font-size: {12 * scale:.1f}pt; }}
QLabel#title {{ font-size: {22 * scale:.1f}pt; }}
QLabel#section {{ font-size: {13 * scale:.1f}pt; }}
QLabel#kpiValue {{ font-size: {16 * scale:.1f}pt; }}
QLabel#kpiLabel {{ font-size: {12 * scale:.1f}pt; }}
QLabel#nextStep {{ font-size: {11.5 * scale:.1f}pt; }}
QLabel#loadLabel {{ font-size: {10 * scale:.1f}pt; }}
QPushButton, QToolButton, QLineEdit, QComboBox {{ min-height: {round(34 * scale)}px; }}
QCheckBox::indicator {{ width: {round(22 * scale)}px; height: {round(22 * scale)}px; }}
QProgressBar {{ min-height: {round(18 * scale)}px; }}
QProgressBar#loadMeter {{ min-height: {round(16 * scale)}px; max-height: {round(16 * scale)}px; font-size: {9 * scale:.1f}pt; }}
QWidget#progressDashboard QProgressBar {{ min-height: {round(18 * scale)}px; max-height: {round(18 * scale)}px; font-size: {10 * scale:.1f}pt; }}
QScrollBar:vertical {{ width: {round(16 * scale)}px; }}
QScrollBar:horizontal {{ height: {round(16 * scale)}px; }}
"""
