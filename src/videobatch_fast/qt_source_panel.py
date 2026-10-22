from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (QComboBox, QFrame, QGridLayout, QHBoxLayout,
                               QLayout, QPushButton, QScrollArea, QSizePolicy,
                               QVBoxLayout, QWidget)

from provoware_grid import choose_columns

from .qt_media_list import AUDIO_EXTS, MEDIA_EXTS, SORT_MODES, DropList
from .qt_responsive_controls import ResponsiveControlRow
from .qt_ui_polish import configure_clear_button, configure_file_buttons, field_label, text_label


def _source_card(window, label: str, widget: DropList, add_text: str) -> QFrame:
    card = QFrame()
    card.setObjectName("sourceCard")
    layout = QVBoxLayout(card)
    layout.setContentsMargins(10, 10, 10, 10)
    layout.setSpacing(7)

    header = QHBoxLayout()
    source_label = field_label(label)
    source_label.setAccessibleName(label)
    source_label.setToolTip(label)
    if not hasattr(window, "_source_header_labels"):
        window._source_header_labels = []
    window._source_header_labels.append((source_label, label, "Audio" if widget is window.audio else "Medien"))
    header.addWidget(source_label)
    header.addStretch()
    sorter = QComboBox()
    sorter.setAccessibleName(f"{label} sortieren")
    # At 200% the previous hard minimum expanded the entire scroll page.
    sorter.setMinimumWidth(0)
    sorter.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
    for sort_label, sort_mode in SORT_MODES:
        sorter.addItem(sort_label, sort_mode)
    sorter.currentIndexChanged.connect(
        lambda _index, target=widget, control=sorter: target.sort_by(str(control.currentData()))
    )
    header.addWidget(sorter)
    layout.addLayout(header)

    widget.setMinimumHeight(170)
    layout.addWidget(widget, 1)

    add = QPushButton(add_text)
    add.setAccessibleName(add_text)
    add.setToolTip(add_text)
    if not hasattr(window, "_source_action_labels"):
        window._source_action_labels = []
    short = "Audio wählen …" if widget is window.audio else "Medien wählen …"
    window._source_action_labels.append((add, add_text, short))
    remove = QPushButton("Entfernen")
    configure_file_buttons(add, remove, label)
    # The full accessible text remains available while 200%-zoom screens
    # receive a short visible action label instead of clipped letters.
    remove.setAccessibleName("Ausgewählte Dateien aus der Liste entfernen")
    remove.setToolTip(
        "Markierte Dateien nur aus der Liste entfernen; Originalmedien bleiben erhalten."
    )
    window._source_action_labels.append((remove, "Entfernen", "Entf."))
    add.clicked.connect(window._choose_audio if widget is window.audio else window._choose_media)
    remove.clicked.connect(widget.remove_selected)
    actions = ResponsiveControlRow((add, remove))
    window._responsive_control_rows.append(actions)
    layout.addWidget(actions)
    return card


class ResponsiveSourceColumns(QWidget):
    """Equal source panels on wide screens; vertical stack on narrow screens."""

    def __init__(self, audio_card: QWidget, media_card: QWidget) -> None:
        super().__init__()
        self.audio_card = audio_card
        self.media_card = media_card
        self.stacked = False
        self.column_ratio = (1, 1)
        self.zoom_percent = 110
        self.grid = QGridLayout(self)
        # The original two-column minimum must not survive a one-column
        # reflow at high zoom and force the scroll page past its right edge.
        self.grid.setSizeConstraint(QLayout.SizeConstraint.SetNoConstraint)
        self.setMinimumWidth(0)
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.grid.setContentsMargins(0, 0, 0, 0)
        self.grid.setSpacing(12)
        self.grid.setColumnStretch(0, 1)
        self.grid.setColumnStretch(1, 1)
        self.grid.addWidget(audio_card, 0, 0)
        self.grid.addWidget(media_card, 0, 1)

    def set_column_ratio(self, left: int, right: int) -> None:
        """Gewichtete Listenbreiten, ohne den automatischen Einspaltenmodus zu stören."""
        if (left, right) not in {(1, 1), (3, 2), (2, 3)}:
            return
        self.column_ratio = (left, right)
        if not self.stacked:
            self.grid.setColumnStretch(0, left)
            self.grid.setColumnStretch(1, right)
        self.grid.invalidate()

    def set_zoom_percent(self, value: int) -> None:
        """Keep the layout consistent with the global Qt typography selector."""
        self.zoom_percent = value
        self._reflow()

    def _reflow(self) -> None:
        # Measured widget minimums supplement the portable 120×80 grid rules.
        intrinsic = (
            max(0, self.audio_card.minimumSizeHint().width()),
            max(0, self.media_card.minimumSizeHint().width()),
        )
        columns = choose_columns(
            max(1, self.width()),
            zoom_percent=self.zoom_percent,
            panel_min_width=360,
            gap=self.grid.spacing(),
            intrinsic_min_widths=intrinsic,
        )
        narrow = columns == 1
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

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._reflow()



class VerticalSourcesScroll(QScrollArea):
    """Keep the real content width aligned with the visible viewport.

    Qt may honour a stale minimumSizeHint from the previous two-column
    arrangement after a 200-percent font change. Constrain the *scroll
    widget itself*; the responsive cards then reflow to a single column.
    """

    def _fit_width(self) -> None:
        content = self.widget()
        if content is None:
            return
        width = max(1, self.viewport().width())
        if content.width() != width or content.minimumWidth() != width:
            content.setFixedWidth(width)
            content.updateGeometry()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._fit_width()

    def setWidget(self, widget: QWidget) -> None:
        super().setWidget(widget)
        self._fit_width()
        QTimer.singleShot(0, self._fit_width)


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
    widths = ((1, 1, "gleich"), (3, 2, "Audio breiter"), (2, 3, "Bilder/Videos breiter"))
    window.source_width_button = QPushButton("Listenbreite: gleich")
    window.source_width_button.setAccessibleName("Breite der Audio- und Medienbereiche ändern")
    window.source_width_button.setToolTip(
        "Ändert das Breitenverhältnis der beiden Medienlisten. "
        "Auf kleinen Bildschirmen stehen die Listen untereinander."
    )

    def change_widths() -> None:
        current = window.source_columns.column_ratio
        index = next((i for i, (left, right, _) in enumerate(widths) if (left, right) == current), 0)
        left, right, description = widths[(index + 1) % len(widths)]
        window.source_columns.set_column_ratio(left, right)
        window.source_width_button.setText(f"Listenbreite: {description}")

    window.source_width_button.clicked.connect(change_widths)
    layout.addWidget(window.source_width_button, 0, Qt.AlignmentFlag.AlignRight)
    layout.addWidget(window.source_columns, 1)
    panel.setMinimumWidth(0)
    layout.setSizeConstraint(QLayout.SizeConstraint.SetNoConstraint)

    adopt = QPushButton("Ansicht als Produktionsreihenfolge übernehmen")
    adopt.setObjectName("secondary")
    adopt.setAccessibleDescription(
        "Übernimmt die aktuell sichtbare Sortierung beider Listen bewusst für die Produktion."
    )
    adopt.clicked.connect(window.audio.apply_view_as_production_order)
    adopt.clicked.connect(window.media.apply_view_as_production_order)

    window.clear = QPushButton("Alle ausgewählten Dateien entfernen")
    configure_clear_button(window.clear)
    order_row = ResponsiveControlRow((adopt, window.clear))
    window._responsive_control_rows.append(order_row)
    layout.addWidget(order_row)
    scroll = VerticalSourcesScroll()
    scroll.setObjectName("mainWorkspaceScroll")
    scroll.setWidgetResizable(True)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    # Qt's focus-follow logic can change a hidden horizontal scrollbar and
    # clip the LEFT of field labels; never scroll sideways in a vertical UI.
    scroll.horizontalScrollBar().valueChanged.connect(
        lambda position: scroll.horizontalScrollBar().setValue(0) if position else None
    )
    scroll.setWidget(panel)
    return scroll
