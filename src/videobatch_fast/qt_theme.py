from __future__ import annotations

APP_STYLE = """
QWidget {
    background: #05070a;
    color: #ffffff;
    font-family: "Noto Sans", "DejaVu Sans", sans-serif;
    font-size: 11pt;
}
QMainWindow { background: #030507; }
QFrame#panel, QFrame#card, QFrame#workflowGuide, QFrame#actionFooter {
    background: #1f2c3c;
    border: 2px solid #9db7d6;
    border-radius: 12px;
}
QFrame#card { min-height: 56px; }
QFrame#loadDashboard {
    background: #0d1520;
    border: 2px solid #a9c4e5;
    border-radius: 10px;
}
QLabel#loadLabel {
    color: #f6f9ff;
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
QLabel#subtitle { color: #eef4ff; }
QLabel#section { font-size: 13pt; font-weight: 700; }
QLabel#kpiValue { font-size: 16pt; font-weight: 800; }
QLabel#kpiLabel { color: #eef4ff; font-size: 9.5pt; }
QLabel#statusChip {
    background: #26384d;
    border: 2px solid #9db7d6;
    border-radius: 10px;
    padding: 5px 10px;
    font-weight: 750;
}
QPushButton {
    background: #2a3d55;
    border: 2px solid #7895b8;
    border-radius: 9px;
    padding: 8px 12px;
    font-weight: 700;
}
QPushButton:hover { background: #385573; }
QPushButton:disabled { color: #c7d3e2; background: #151c26; }
QPushButton#primary {
    background: #1769e0;
    border-color: #8ab4ff;
    color: #ffffff;
}
QPushButton#primary:hover { background: #267cff; }
QPushButton#danger {
    background: #4b2029;
    border-color: #a34d62;
}

QFrame#workflowGuide {
    background: #111a25;
    border-color: #7e9ec2;
}
QFrame#actionFooter {
    background: #111a25;
    border: 2px solid #7895b8;
    border-radius: 12px;
}
QLabel#guideTitle {
    font-weight: 800;
    color: #ffffff;
    padding-right: 4px;
}
QLabel#stepChip {
    background: #26384d;
    border: 2px solid #9db7d6;
    border-radius: 8px;
    padding: 5px 9px;
    font-weight: 750;
}
QLabel#nextStep {
    font-size: 11.5pt;
    font-weight: 800;
    color: #ffffff;
}
QLabel#safeHint {
    background: #10291f;
    border: 2px solid #56a57c;
    border-radius: 8px;
    padding: 7px 9px;
    color: #eafff4;
}
QToolButton {
    background: transparent;
    border: 0;
    color: #f0f5ff;
    padding: 5px 2px;
    text-align: left;
    font-weight: 700;
}
QToolButton:hover { color: #ffffff; }
QPushButton#workspaceNav {
    text-align: left;
    padding: 8px 10px;
}
QPushButton#workspaceNav[active="true"] {
    background: #275ba7;
    border-color: #8ab4ff;
    color: #ffffff;
}
QScrollArea#secondaryScroll {
    background: transparent;
    border: 0;
}

QCheckBox {
    color: #ffffff;
    spacing: 10px;
    font-weight: 750;
}
QCheckBox::indicator {
    width: 26px;
    height: 26px;
    border: 3px solid #f7fbff;
    border-radius: 5px;
    background: #0a0d12;
}
QCheckBox::indicator:checked {
    background: #1687ff;
    border: 3px solid #ffffff;
}
QCheckBox::indicator:hover {
    border-color: #ffd166;
}
QCheckBox::indicator:disabled {
    background: #343f4d;
    border-color: #aab7c6;
}

QListWidget, QTableWidget, QPlainTextEdit, QLineEdit, QComboBox {
    background: #080c12;
    color: #ffffff;
    border: 2px solid #a9c4e5;
    border-radius: 8px;
    padding: 5px;
    selection-background-color: #235fae;
    selection-color: #ffffff;
}
QComboBox QAbstractItemView {
    background: #080c12;
    color: #ffffff;
    border: 2px solid #a9c4e5;
    selection-background-color: #235fae;
    selection-color: #ffffff;
}
QHeaderView::section {
    background: #26384d;
    color: #ffffff;
    border: 0;
    border-bottom: 2px solid #89a6c8;
    padding: 7px;
    font-weight: 750;
}
QProgressBar {
    background: #080c12;
    color: #ffffff;
    border: 2px solid #7895b8;
    border-radius: 7px;
    min-height: 18px;
    text-align: center;
}
QProgressBar::chunk { background: #1687ff; border-radius: 6px; }
QSplitter::handle { background: #2a3b50; width: 7px; }
"""
