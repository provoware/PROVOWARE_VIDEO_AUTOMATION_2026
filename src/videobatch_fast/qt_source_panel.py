from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QComboBox, QFrame, QGridLayout, QHBoxLayout,
                               QPushButton, QScrollArea, QVBoxLayout, QWidget)

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
    sorter.setMinimumWidth(115)
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


class ResponsiveSourceColumns(QWidget):
    """Equal source panels on wide screens; vertical stack on narrow screens."""

    def __init__(self, audio_card: QWidget, media_card: QWidget) -> None:
        super().__init__()
        self.audio_card = audio_card
        self.media_card = media_card
        self.stacked = False
        self.column_ratio = (1, 1)
        self.grid = QGridLayout(self)
        self.grid.setContentsMargins(0, 0, 0, 0)
        self.grid.setSpacing(10)
        self.grid.setColumnStretch(0, 1)
        self.grid.setColumnStretch(1, 1)
        self.grid.addWidget(audio_card, 0, 0)
        self.grid.addWidget(media_card, 0, 1)

    def set_column_ratio(self, left: int, right: int) -> None:
        """Breiten der Listen ändern; auf schmalen Fenstern bleibt der Stapel erhalten."""
        if (left, right) not in {(1, 1), (3, 2), (2, 3)}:
            return
        self.column_ratio = (left, right)
        if not self.stacked:
            self.grid.setColumnStretch(0, left)
            self.grid.setColumnStretch(1, right)
        self.grid.invalidate()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        # Panels must keep readable minimum widths even at 125–200% zoom.
        # Text zoom increases the necessary panel width; never squash labels.
        threshold = max(790, round(790 * self.fontMetrics().height() / 19))
        narrow = self.width() < threshold
        if narrow == self.stacked:
            return
        self.stacked = narrow
        self.grid.removeWidget(self.media_card)
        self.grid.addWidget(self.media_card, 1 if narrow else 0, 0 if narrow else 1)
        self.grid.setColumnStretch(0, 1 if narrow else self.column_ratio[0])
        self.grid.setColumnStretch(1, 0 if narrow else self.column_ratio[1])
        self.grid.setRowStretch(0, 0 if narrow else 1)
        self.grid.setRowStretch(1, 0 if narrow else 1)
        self.updateGeometry()


def build_sources_panel(window) -> QWidget:
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

    window.source_columns = ResponsiveSourceColumns(
        _source_card(window, "Audiodateien", window.audio, "Audio auswählen …"),
        _source_card(window, "Bilder / Videos", window.media, "Bilder/Videos auswählen …"),
    )
    # Kleine, barrierefrei bedienbare Alternative zum Verschieben per Maus.
    widths = ((1, 1, "gleich"), (3, 2, "Audio breiter"), (2, 3, "Bilder/Videos breiter"))
    window.source_width_button = QPushButton("Listenbreite: gleich")
    window.source_width_button.setAccessibleName("Breite der Audio- und Medienbereiche ändern")
    window.source_width_button.setToolTip(
        "Wechselt zwischen gleich breiten Listen und einer breiteren Audio- oder Medienliste. "
        "Bei wenig Platz stehen die Bereiche weiterhin untereinander."
    )

    def change_widths() -> None:
        current = window.source_columns.column_ratio
        index = next((i for i, (left, right, _) in enumerate(widths) if (left, right) == current), 0)
        left, right, description = widths[(index + 1) % len(widths)]
        window.source_columns.set_column_ratio(left, right)
        window.source_width_button.setText(f"Listenbreite: {description}")

    window.source_width_button.clicked.connect(change_widths)
    width_row = QHBoxLayout()
    width_row.addStretch()
    width_row.addWidget(window.source_width_button)
    layout.addLayout(width_row)
    layout.addWidget(window.source_columns, 1)

    order_row = QHBoxLayout()
    adopt = QPushButton("Ansicht als Produktionsreihenfolge übernehmen")
    adopt.setObjectName("secondary")
    adopt.setAccessibleDescription(
        "Übernimmt die aktuell sichtbare Sortierung beider Listen bewusst für die Produktion."
    )
    adopt.clicked.connect(window.audio.apply_view_as_production_order)
    adopt.clicked.connect(window.media.apply_view_as_production_order)
    order_row.addWidget(adopt, 1)

    window.clear = QPushButton("Alle ausgewählten Dateien entfernen")
    configure_clear_button(window.clear)
    order_row.addWidget(window.clear)
    layout.addLayout(order_row)
    scroll = QScrollArea()
    scroll.setObjectName("mainWorkspaceScroll")
    scroll.setWidgetResizable(True)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    scroll.setWidget(panel)
    return scroll
