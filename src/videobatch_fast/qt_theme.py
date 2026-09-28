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
    background: #161f2b;
    border: 1px solid #3f526a;
    border-radius: 12px;
}
QFrame#card { min-height: 56px; }
QLabel#title { font-size: 22pt; font-weight: 800; }
QLabel#subtitle { color: #c3d0e3; }
QLabel#section { font-size: 13pt; font-weight: 700; }
QLabel#kpiValue { font-size: 16pt; font-weight: 800; }
QLabel#kpiLabel { color: #c3d0e3; font-size: 9.5pt; }
QLabel#statusChip {
    background: #202c3b;
    border: 1px solid #5b7392;
    border-radius: 10px;
    padding: 5px 10px;
    font-weight: 700;
}
QPushButton {
    background: #243247;
    border: 1px solid #526985;
    border-radius: 9px;
    padding: 8px 12px;
    font-weight: 650;
}
QPushButton:hover { background: #31445e; }
QPushButton:disabled { color: #96a4b7; background: #171f2a; }
QPushButton#primary {
    background: #316bf4;
    border-color: #4b7df5;
    color: white;
}
QPushButton#primary:hover { background: #3f78ff; }
QPushButton#danger {
    background: #3a2026;
    border-color: #65313d;
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
    background: transparent;
    border: 0;
    color: #d2dcef;
    padding: 5px 2px;
    text-align: left;
    font-weight: 650;
}
QToolButton:hover { color: #ffffff; }
QPushButton#workspaceNav {
    text-align: left;
    padding: 8px 10px;
}
QPushButton#workspaceNav[active="true"] {
    background: #274f91;
    border-color: #4b7df5;
    color: white;
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
}

QListWidget, QTableWidget, QPlainTextEdit, QLineEdit, QComboBox {
    background: #080d13;
    border: 1px solid #526985;
    border-radius: 8px;
    padding: 5px;
    selection-background-color: #275fb2;
    selection-color: #ffffff;
}
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
QProgressBar::chunk { background: #316bf4; border-radius: 6px; }
QSplitter::handle { background: #0b1017; width: 7px; }
"""
