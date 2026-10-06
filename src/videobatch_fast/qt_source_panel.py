from __future__ import annotations

from PySide6.QtWidgets import QComboBox, QFrame, QHBoxLayout, QPushButton, QVBoxLayout

from .qt_media_list import AUDIO_EXTS, MEDIA_EXTS, SORT_MODES, DropList
from .qt_ui_polish import configure_clear_button, configure_file_buttons, field_label, text_label


def _source_card(window, label: str, widget: DropList, add_text: str) -> QFrame:
    card = QFrame()
    card.setObjectName("sourceCard")
    layout = QVBoxLayout(card)
    layout.setContentsMargins(10, 10, 10, 10)
    layout.setSpacing(7)

    header = QHBoxLayout()
    header.addWidget(field_label(label))
    header.addStretch()
    sorter = QComboBox()
    sorter.setAccessibleName(f"{label} sortieren")
    sorter.setMinimumWidth(175)
    for sort_label, sort_mode in SORT_MODES:
        sorter.addItem(sort_label, sort_mode)
    sorter.currentIndexChanged.connect(
        lambda _index, target=widget, control=sorter: target.sort_by(str(control.currentData()))
    )
    header.addWidget(sorter)
    layout.addLayout(header)

    widget.setMinimumHeight(170)
    layout.addWidget(widget, 1)

    actions = QHBoxLayout()
    add = QPushButton(add_text)
    remove = QPushButton("Entfernen")
    configure_file_buttons(add, remove, label)
    add.clicked.connect(window._choose_audio if widget is window.audio else window._choose_media)
    remove.clicked.connect(widget.remove_selected)
    actions.addWidget(add, 1)
    actions.addWidget(remove)
    layout.addLayout(actions)
    return card


def build_sources_panel(window) -> QFrame:
    panel, layout = window._panel(
        "1 · Dateien auswählen",
        "Audio und Bilder/Videos stehen nebeneinander. So bleiben beide Listen und ihre Schalter sichtbar.",
    )
    window.audio = DropList(AUDIO_EXTS)
    window.media = DropList(MEDIA_EXTS)

    layout.addWidget(text_label(
        "Strg + Mausrad vergrößert nur die jeweilige Liste. Sortieren ändert nur die Ansicht; "
        "die Produktionsreihenfolge bleibt bis zu einer bewussten Neuordnung erhalten.",
        "helperText", wrap=True,
    ))

    lists = QHBoxLayout()
    lists.setSpacing(10)
    lists.addWidget(_source_card(window, "Audiodateien", window.audio, "Audio auswählen …"), 1)
    lists.addWidget(_source_card(window, "Bilder / Videos", window.media, "Bilder/Videos auswählen …"), 1)
    layout.addLayout(lists, 1)

    window.clear = QPushButton("Alle ausgewählten Dateien entfernen")
    configure_clear_button(window.clear)
    layout.addWidget(window.clear)
    return panel
