"""VideoBatch Qt adapter for the toolkit-independent PROVOWARE grid rules."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame, QGridLayout, QLabel, QSizePolicy, QVBoxLayout, QWidget,
)
from provoware_grid import choose_columns


class ResponsiveSettingsPanel(QFrame):
    """Preserve existing setting widgets while reflowing their visual groups."""

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("dashboardControls")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.grid = QGridLayout(self)
        self.grid.setContentsMargins(8, 5, 8, 5)
        self.grid.setHorizontalSpacing(8)
        self.grid.setVerticalSpacing(4)
        self._fields: list[QWidget] = []
        self.zoom_percent = 110
        self.columns = 0

    def add_field(self, label: str, field: QWidget, *, buddy: QWidget | None = None) -> None:
        card = QWidget(self)
        card.setObjectName("adaptiveSettingGroup")
        column = QVBoxLayout(card)
        column.setContentsMargins(1, 1, 1, 1)
        column.setSpacing(2)
        caption = QLabel(label)
        caption.setObjectName("adaptiveSettingLabel")
        caption.setWordWrap(True)
        caption.setBuddy(buddy or field)
        column.addWidget(caption)
        column.addWidget(field)
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self._fields.append(card)
        self._reflow(force=True)

    def set_zoom_percent(self, value: int) -> None:
        self.zoom_percent = value
        self._reflow()

    def _reflow(self, *, force: bool = False) -> None:
        margins = self.grid.contentsMargins()
        width = max(1, self.width() - margins.left() - margins.right())
        new_columns = choose_columns(
            width, zoom_percent=self.zoom_percent,
            panel_min_width=320, gap=self.grid.horizontalSpacing(),
        )
        if new_columns == self.columns and not force:
            return
        self.columns = new_columns
        for card in self._fields:
            self.grid.removeWidget(card)
        for index, card in enumerate(self._fields):
            row, col = divmod(index, new_columns)
            self.grid.addWidget(card, row, col, Qt.AlignmentFlag.AlignTop)
        self.grid.setColumnStretch(0, 1)
        self.grid.setColumnStretch(1, 1 if new_columns == 2 else 0)
        self.updateGeometry()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._reflow()
