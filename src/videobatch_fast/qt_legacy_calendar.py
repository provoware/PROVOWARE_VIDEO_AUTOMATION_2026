from __future__ import annotations

from collections.abc import Callable
from typing import Any

from PySide6.QtWidgets import (
    QCalendarWidget,
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

ComboFactory = Callable[[QWidget, list[tuple[str, str]], str], QComboBox]
SaveProject = Callable[[object], None]


def build_calendar_tab(
    window: Any,
    *,
    combo_factory: ComboFactory,
    save_project: SaveProject,
) -> QWidget:
    tab = QWidget()
    layout = QVBoxLayout(tab)
    window.parity_calendar = QCalendarWidget()
    layout.addWidget(window.parity_calendar, 1)

    form = QFormLayout()
    window.parity_calendar_type = combo_factory(
        tab,
        [("Notiz", "note"), ("Aufgabe", "task"), ("Erinnerung", "reminder"), ("Termin", "deadline")],
        "note",
    )
    window.parity_calendar_color = combo_factory(
        tab,
        [
            ("Neutral", "none"),
            ("Erledigt / Erfolg", "success"),
            ("Beachten", "warning"),
            ("Blockiert", "error"),
            ("Information", "info"),
            ("Aktiv", "active"),
        ],
        "none",
    )
    window.parity_calendar_note = QLineEdit()
    window.parity_calendar_note.setPlaceholderText("Kurze Notiz zum ausgewählten Tag")
    form.addRow("Art", window.parity_calendar_type)
    form.addRow("Markierung", window.parity_calendar_color)
    form.addRow("Notiz", window.parity_calendar_note)
    layout.addLayout(form)

    actions = QHBoxLayout()
    save = QPushButton("Kalendereintrag speichern")
    save.setObjectName("primary")
    remove = QPushButton("Eintrag löschen")
    actions.addWidget(remove)
    actions.addStretch()
    actions.addWidget(save)
    layout.addLayout(actions)

    window.parity_calendar.selectionChanged.connect(lambda: load_calendar_selection(window))
    save.clicked.connect(lambda: save_calendar_selection(window, save_project=save_project))
    remove.clicked.connect(lambda: remove_calendar_selection(window, save_project=save_project))
    return tab


def calendar_key(window: Any) -> str:
    return window.parity_calendar.selectedDate().toString("yyyy-MM-dd")


def load_calendar_selection(window: Any) -> None:
    key = calendar_key(window)
    entry = window._parity_calendar_notes.get(key, {})
    type_index = window.parity_calendar_type.findData(str(entry.get("entry_type", "note")))
    color_index = window.parity_calendar_color.findData(
        str(entry.get("color", window._parity_calendar_marks.get(key, "none")))
    )
    window.parity_calendar_type.setCurrentIndex(max(0, type_index))
    window.parity_calendar_color.setCurrentIndex(max(0, color_index))
    window.parity_calendar_note.setText(str(entry.get("note", "")))


def save_calendar_selection(window: Any, *, save_project: SaveProject) -> None:
    key = calendar_key(window)
    note = window.parity_calendar_note.text().strip()[:500]
    entry_type = str(window.parity_calendar_type.currentData() or "note")
    color = str(window.parity_calendar_color.currentData() or "none")
    if note or color != "none":
        window._parity_calendar_notes[key] = {
            "note": note,
            "entry_type": entry_type,
            "color": color,
        }
    else:
        window._parity_calendar_notes.pop(key, None)
    if color == "none":
        window._parity_calendar_marks.pop(key, None)
    else:
        window._parity_calendar_marks[key] = color
    save_project(window)


def remove_calendar_selection(window: Any, *, save_project: SaveProject) -> None:
    key = calendar_key(window)
    window._parity_calendar_notes.pop(key, None)
    window._parity_calendar_marks.pop(key, None)
    load_calendar_selection(window)
    save_project(window)
