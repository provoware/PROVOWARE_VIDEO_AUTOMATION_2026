from __future__ import annotations

APP_STYLE = """
QWidget {
    background: #0b1016;
    color: #f3f7ff;
    font-family: "Noto Sans", "DejaVu Sans", sans-serif;
    font-size: 11pt;
}
QMainWindow { background: #070b10; }
QFrame#panel, QFrame#card, QFrame#workflowGuide, QFrame#actionFooter {
    background: #182433;
    border: 2px solid #6f87a3;
    border-radius: 12px;
}
QFrame#card { min-height: 56px; }
QFrame#loadDashboard {
    background: #101822;
    border: 2px solid #7f98b8;
    border-radius: 10px;
}
QLabel#loadLabel {
    color: #e2eaf5;
    font-size: 8.5pt;
    font-weight: 750;
}
QProgressBar#loadMeter {
    min-height: 15px;
    max-height: 15px;
    font-size: 8pt;
    font-weight: 700;
}
QLabel#title { font-size: 22pt; font-weight: 800; }
QLabel#subtitle { color: #e2eaf5; }
QLabel#section { font-size: 13pt; font-weight: 700; }
QLabel#kpiValue { font-size: 16pt; font-weight: 800; }
QLabel#kpiLabel { color: #e2eaf5; font-size: 9.5pt; }
QLabel#statusChip {
    background: #202c3b;
    border: 1px solid #5b7392;
    border-radius: 10px;
    padding: 5px 10px;
    font-weight: 700;
}
QPushButton {
    background: #007f99;
    border: 2px solid #2ee6ff;
    color: #ffffff;
    border-radius: 9px;
    padding: 8px 12px;
    font-weight: 650;
}
QPushButton:hover { background: #009fbd; }
QPushButton:pressed, QPushButton:checked {
    background: #ffbf3f;
    border-color: #ffe29a;
    color: #161006;
}
QPushButton:disabled { color: #b6c2d2; background: #171f2a; }
QPushButton, QToolButton, QLineEdit, QComboBox {
    min-height: 34px;
}
QPushButton:focus, QToolButton:focus, QLineEdit:focus, QComboBox:focus,
QListWidget:focus, QTableWidget:focus, QPlainTextEdit:focus, QCheckBox:focus {
    border: 3px solid #ffffff;
}
QPushButton#primary {
    background: #ffbf3f;
    border-color: #ffe29a;
    color: #161006;
}
QPushButton#primary:hover { background: #ffd36f; }
QPushButton#danger {
    background: #a61f3b;
    border-color: #ff7890;
    color: #ffffff;
}

QFrame#workflowGuide {
    background: #131d29;
    border-color: #48627f;
}
QFrame#actionFooter {
    background: #131d29;
    border: 1px solid #355078;
    border-radius: 12px;
}
QLabel#guideTitle {
    font-weight: 800;
    color: #f3f7ff;
    padding-right: 4px;
}
QLabel#stepChip {
    background: #202c3b;
    border: 1px solid #5b7392;
    border-radius: 8px;
    padding: 5px 9px;
    font-weight: 700;
}
QLabel#nextStep {
    font-size: 11.5pt;
    font-weight: 800;
    color: #f2f6ff;
}
QLabel#safeHint {
    background: #14251f;
    border: 1px solid #315b49;
    border-radius: 8px;
    padding: 7px 9px;
    color: #cdebdc;
}
QToolButton {
    background: #007f99;
    border: 1px solid #2ee6ff;
    border-radius: 7px;
    color: #ffffff;
    padding: 5px 2px;
    text-align: left;
    font-weight: 650;
}
QToolButton:hover { background: #009fbd; }
QToolButton:checked {
    background: #ffbf3f;
    border-color: #ffe29a;
    color: #161006;
}
QPushButton#workspaceNav {
    text-align: left;
    padding: 8px 10px;
}
QPushButton#workspaceNav[active="true"] {
    background: #ffbf3f;
    border-color: #ffe29a;
    color: #161006;
}
QScrollArea#secondaryScroll {
    background: transparent;
    border: 0;
}

QCheckBox {
    color: #f3f7ff;
    spacing: 9px;
    font-weight: 650;
}
QCheckBox::indicator {
    width: 22px;
    height: 22px;
    border: 2px solid #dbe8f8;
    border-radius: 4px;
    background: #05080d;
}
QCheckBox::indicator:checked {
    background: #2f7cff;
    border: 2px solid #ffffff;
}
QCheckBox::indicator:disabled {
    background: #202a37;
    border-color: #8999ad;
}

QListWidget, QTableWidget, QPlainTextEdit, QLineEdit, QComboBox {
    background: #05080d;
    border: 2px solid #7f98b8;
    border-radius: 8px;
    padding: 5px;
    selection-background-color: #2f6fd2;
    selection-color: #ffffff;
}
QListWidget::item {
    padding: 6px;
    border-radius: 5px;
}
QListWidget::item:selected {
    background: #2f6fd2;
    color: #ffffff;
}
QTableWidget { gridline-color: #526985; }
QHeaderView::section {
    background: #202b3a;
    color: #f3f7ff;
    border: 0;
    border-bottom: 1px solid #526985;
    padding: 7px;
    font-weight: 700;
}
QProgressBar {
    background: #0c121a;
    border: 1px solid #526985;
    border-radius: 7px;
    min-height: 18px;
    text-align: center;
}
QProgressBar::chunk { background: #00c8e8; border-radius: 6px; }
QProgressBar#jobProgress::chunk { background: #ffbf3f; }
QSplitter::handle { background: #0b1017; width: 7px; }
QScrollBar:vertical {
    width: 16px;
    background: #101822;
}
QScrollBar::handle:vertical {
    min-height: 32px;
    background: #7f98b8;
    border-radius: 7px;
}
QScrollBar:horizontal {
    height: 16px;
    background: #101822;
}
QScrollBar::handle:horizontal {
    min-width: 32px;
    background: #7f98b8;
    border-radius: 7px;
}
QToolTip {
    background: #f3f7ff;
    color: #070b10;
    border: 2px solid #2f6fd2;
    padding: 6px;
}
"""
