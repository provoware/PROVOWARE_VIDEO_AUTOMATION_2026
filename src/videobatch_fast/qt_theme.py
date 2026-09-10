from __future__ import annotations

APP_STYLE = """
QWidget {
    background: #0f141c;
    color: #e9eef7;
    font-family: "Noto Sans", "DejaVu Sans", sans-serif;
    font-size: 11pt;
}
QMainWindow { background: #0b1017; }
QFrame#panel, QFrame#card {
    background: #151c26;
    border: 1px solid #273244;
    border-radius: 12px;
}
QFrame#card { min-height: 74px; }
QLabel#title { font-size: 22pt; font-weight: 800; }
QLabel#subtitle { color: #9eabc0; }
QLabel#section { font-size: 13pt; font-weight: 700; }
QLabel#kpiValue { font-size: 18pt; font-weight: 800; }
QLabel#kpiLabel { color: #9eabc0; font-size: 9.5pt; }
QLabel#statusChip {
    background: #1c2735;
    border: 1px solid #34445d;
    border-radius: 10px;
    padding: 5px 10px;
    font-weight: 700;
}
QPushButton {
    background: #202b3a;
    border: 1px solid #34445d;
    border-radius: 9px;
    padding: 8px 12px;
    font-weight: 650;
}
QPushButton:hover { background: #29384b; }
QPushButton:disabled { color: #6f7b8e; background: #171e28; }
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
QListWidget, QTableWidget, QPlainTextEdit, QLineEdit, QComboBox {
    background: #0d131b;
    border: 1px solid #2b3749;
    border-radius: 8px;
    padding: 5px;
    selection-background-color: #294f94;
}
QHeaderView::section {
    background: #18212d;
    color: #cdd7e8;
    border: 0;
    border-bottom: 1px solid #2b3749;
    padding: 7px;
    font-weight: 700;
}
QProgressBar {
    background: #101720;
    border: 1px solid #2b3749;
    border-radius: 7px;
    min-height: 18px;
    text-align: center;
}
QProgressBar::chunk { background: #316bf4; border-radius: 6px; }
QSplitter::handle { background: #0b1017; width: 7px; }
"""
