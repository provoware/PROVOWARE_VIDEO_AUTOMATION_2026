from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QAbstractItemView, QLabel, QPushButton, QTableWidget, QTableWidgetItem,
)


VISUAL_HIERARCHY_STYLE = """
QFrame#panel { border-color: #526985; }
QFrame#card {
    min-height: 56px;
    background: #101a26;
    border-color: #425b78;
}
QLabel#panelHint {
    color: #c6d4e6;
    padding-bottom: 4px;
}
QLabel#helperText {
    color: #aebfd3;
    font-size: 9.5pt;
}
QLabel#fieldLabel {
    color: #f3f7ff;
    font-weight: 700;
}
QLabel#section { font-weight: 800; }
QLabel#statusChip {
    border-width: 2px;
    padding: 6px 11px;
    font-weight: 800;
}
QLabel#statusChip[state="ready"], QLabel#statusChip[state="success"] {
    background: #123427;
    border-color: #55d99a;
    color: #ddffef;
}
QLabel#statusChip[state="warning"] {
    background: #3b2e12;
    border-color: #f0c45d;
    color: #fff1c2;
}
QLabel#statusChip[state="busy"] {
    background: #102f3d;
    border-color: #5dd7f5;
    color: #e1f9ff;
}
QLabel#statusChip[state="error"] {
    background: #421722;
    border-color: #ff7890;
    color: #fff0f3;
}
QPushButton#secondary {
    background: #18293a;
    border-color: #7fa5ca;
    color: #eef6ff;
}
QPushButton#secondary:hover { background: #22384e; }
QPushButton#quietDanger {
    background: #21171b;
    border-color: #9a5262;
    color: #ffdce3;
}
QPushButton#quietDanger:hover {
    background: #3a1d25;
    border-color: #ff7890;
}
QFrame#actionFooter {
    background: #111c28;
    border: 2px solid #58789d;
}
QLabel#nextStep {
    background: #0d2632;
    border: 1px solid #356f84;
    border-radius: 8px;
    padding: 7px 9px;
    color: #f2fbff;
}
QToolButton {
    background: #142333;
    border-color: #6685a8;
}
QToolButton:hover {
    background: #1e344a;
    border-color: #8fb9e2;
}
QTableWidget {
    gridline-color: #34495f;
    alternate-background-color: #0d1620;
}
QTableWidget::item {
    padding: 7px 6px;
    border-bottom: 1px solid #25394e;
}
QTableWidget::item:selected {
    background: #2f6fd2;
    color: #ffffff;
}
"""


def text_label(text: str, object_name: str, *, wrap: bool = False) -> QLabel:
    label = QLabel(text)
    label.setObjectName(object_name)
    label.setWordWrap(wrap)
    return label


def field_label(text: str) -> QLabel:
    return text_label(text, "fieldLabel")


def configure_file_buttons(add: QPushButton, remove: QPushButton, label: str) -> None:
    add.setObjectName("secondary")
    remove.setObjectName("quietDanger")
    remove.setAccessibleDescription(f"Entfernt markierte Einträge aus {label}.")


def configure_clear_button(button: QPushButton) -> None:
    button.setObjectName("quietDanger")
    button.setAccessibleDescription("Leert beide Dateilisten. Originaldateien bleiben unverändert.")


def configure_output_button(button: QPushButton) -> None:
    button.setObjectName("secondary")
    button.setAccessibleDescription("Wählt den Ordner für die fertigen Videos.")


def configure_secondary_buttons(*buttons: QPushButton) -> None:
    for button in buttons:
        button.setObjectName("secondary")


def configure_job_table(table: QTableWidget) -> None:
    table.setHorizontalHeaderLabels(["#", "Audio", "Medium", "Status", "Einzel-Fortschritt"])
    table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    table.setWordWrap(False)
    table.setTextElideMode(Qt.TextElideMode.ElideMiddle)
    table.verticalHeader().setVisible(False)
    table.verticalHeader().setDefaultSectionSize(38)
    table.horizontalHeader().setStretchLastSection(True)
    table.setColumnWidth(0, 42)
    table.setColumnWidth(3, 105)
    table.setColumnWidth(4, 145)


def job_table_item(text: str, column: int) -> QTableWidgetItem:
    item = QTableWidgetItem(text)
    if column in (1, 2):
        item.setToolTip(text)
    return item


def install_workflow_shortcuts(window) -> None:
    configure_secondary_buttons(window.open_output, window.show_result_log)
    window.audio.setToolTip(window.audio.toolTip() + " · Alt+1: Dateiauswahl")
    window.output.setToolTip("Alt+2: Ausgabeordner")
    window.start.setToolTip("Alt+3: Videos erstellen")
    window._workflow_shortcuts = []

    def activate(route: str, target) -> None:
        handler = getattr(window, "_route_workspace", None)
        if callable(handler):
            handler(route)
        else:
            pages = getattr(window, "_workflow_pages", {})
            if route in pages:
                window.workflow_stack.setCurrentWidget(pages[route])
        target.setFocus()

    for sequence, route, target in (
        ("Alt+1", "media", window.audio),
        ("Alt+2", "effects", window.output),
        ("Alt+3", "queue", window.start),
    ):
        shortcut = QShortcut(QKeySequence(sequence), window)
        shortcut.activated.connect(
            lambda key=route, widget=target: activate(key, widget)
        )
        window._workflow_shortcuts.append(shortcut)


def update_status_chip(label: QLabel, text: str) -> None:
    normalized = text.upper()
    if any(token in normalized for token in ("FEHLER", "SCHUTZSTOPP", "ABGEBROCHEN")):
        state = "error"
    elif any(token in normalized for token in ("PRÜFT", "ANALYSE", "STARTET", "LÄUFT", "STOPPT")):
        state = "busy"
    elif "HINWEIS" in normalized or normalized == "PRÜFEN":
        state = "warning"
    elif normalized == "FERTIG":
        state = "success"
    else:
        state = "ready"
    label.setProperty("state", state)
    label.setText(text)
    label.style().unpolish(label)
    label.style().polish(label)
