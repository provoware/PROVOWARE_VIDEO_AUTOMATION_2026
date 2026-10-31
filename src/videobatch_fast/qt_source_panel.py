from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (QComboBox, QFrame, QHBoxLayout, QSplitter,
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
    window._source_import_buttons.append(add)
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
    # Import belongs to the persistent media toolbar. Destructive removal
    # stays beside its own list, never in the global import controls.
    layout.addWidget(remove, 0, Qt.AlignmentFlag.AlignRight)
    return card


class ResponsiveSourceColumns(QWidget):
    """Zwei per Maus verstellbare Quellenlisten; bei wenig Platz untereinander."""

    def __init__(self, audio_card: QWidget, media_card: QWidget) -> None:
        super().__init__()
        self.audio_card = audio_card
        self.media_card = media_card
        self.stacked = False
        self.column_ratio = (1, 1)
        self.zoom_percent = 110
        self.setMinimumWidth(0)
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.splitter = QSplitter(Qt.Horizontal, self)
        self.splitter.setObjectName("sourceAreaSplitter")
        self.splitter.setAccessibleName("Trennlinie zwischen Audio- und Medienbereich")
        self.splitter.setToolTip("Trennlinie mit der Maus ziehen, um die Listenbreiten zu ändern.")
        self.splitter.setChildrenCollapsible(False)
        self.splitter.setHandleWidth(12)
        self.splitter.setMinimumWidth(0)
        self.splitter.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        for card in (audio_card, media_card):
            card.setMinimumWidth(0)
            card.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
            self.splitter.addWidget(card)
        layout.addWidget(self.splitter)
        self.splitter.splitterMoved.connect(self._remember_manual_sizes)
        self._apply_column_ratio()

    def _apply_column_ratio(self) -> None:
        old = self.splitter.blockSignals(True)
        try:
            self.splitter.setSizes(list(self.column_ratio))
        finally:
            self.splitter.blockSignals(old)

    def _remember_manual_sizes(self, _pos: int, _handle: int) -> None:
        """Beide Listen bleiben sichtbar; die manuelle Breite überlebt den Umbruch."""
        if self.stacked:
            return
        widths = self.splitter.sizes()
        if len(widths) == 2 and min(widths) > 0:
            self.column_ratio = tuple(widths)

    def set_column_ratio(self, left: int, right: int) -> None:
        """Die bisherigen drei Tastatur-Voreinstellungen bleiben verfügbar."""
        if (left, right) not in {(1, 1), (3, 2), (2, 3)}:
            return
        self.column_ratio = (left, right)
        if not self.stacked:
            self._apply_column_ratio()

    def set_zoom_percent(self, value: int) -> None:
        self.zoom_percent = value
        self._reflow()

    def _reflow(self) -> None:
        intrinsic = (
            max(0, self.audio_card.minimumSizeHint().width()),
            max(0, self.media_card.minimumSizeHint().width()),
        )
        columns = choose_columns(
            max(1, self.width()),
            zoom_percent=self.zoom_percent,
            panel_min_width=360,
            gap=self.splitter.handleWidth(),
            intrinsic_min_widths=intrinsic,
        )
        narrow = columns == 1
        if narrow == self.stacked:
            return
        self.stacked = narrow
        self.splitter.setOrientation(Qt.Vertical if narrow else Qt.Horizontal)
        if narrow:
            self.splitter.setSizes([1, 1])
        else:
            self._apply_column_ratio()
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

    window._source_import_buttons = []
    audio_card = _source_card(window, "Audiodateien", window.audio, "Audio auswählen …")
    media_card = _source_card(window, "Bilder / Videos", window.media, "Bilder/Videos auswählen …")
    # The same import buttons stay above the vertically scrollable lists.
    window.media_import_bar = ResponsiveControlRow(tuple(window._source_import_buttons))
    window.media_import_bar.setObjectName("mediaImportToolbar")
    window.media_import_bar.setAccessibleName("Audio und Bilder/Videos hinzufügen")
    window._responsive_control_rows.append(window.media_import_bar)
    window.source_columns = ResponsiveSourceColumns(audio_card, media_card)
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
    window.source_columns.splitter.splitterMoved.connect(
        lambda _position, _handle: window.source_width_button.setText("Listenbreite: frei")
        if not window.source_columns.stacked else None
    )
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
