"""Responsive Qt control groups: preserve buttons instead of clipping them."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGridLayout, QSizePolicy, QWidget


class ResponsiveControlRow(QWidget):
    """Show controls in one row when they fit; otherwise stack them vertically.

    A layout, not absolute coordinates, decides positioning. This also works
    when Qt's font scaling changes the controls' real minimumSizeHint().
    """

    def __init__(self, controls: tuple[QWidget, ...], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        if not controls:
            raise ValueError("ResponsiveControlRow benötigt mindestens ein Bedienelement.")
        self.controls = controls
        self.zoom_percent = 110
        self.columns = 0
        self.grid = QGridLayout(self)
        self.grid.setContentsMargins(0, 0, 0, 0)
        self.grid.setHorizontalSpacing(8)
        self.grid.setVerticalSpacing(5)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self._reflow(force=True)

    def set_zoom_percent(self, percent: int) -> None:
        if percent <= 0:
            raise ValueError("Schriftgröße muss größer als null sein.")
        self.zoom_percent = percent
        self._reflow(force=True)

    def _reflow(self, *, force: bool = False) -> None:
        margin = self.grid.contentsMargins()
        available = max(1, self.width() - margin.left() - margin.right())
        # Qt measures translated labels and the current font; no fixed button width.
        min_widths = [max(40, widget.minimumSizeHint().width()) for widget in self.controls]
        required = sum(min_widths) + self.grid.horizontalSpacing() * (len(self.controls) - 1)
        columns = len(self.controls) if available >= required else 1
        if columns == self.columns and not force:
            return
        self.columns = columns
        for widget in self.controls:
            self.grid.removeWidget(widget)
        for column in range(len(self.controls)):
            self.grid.setColumnStretch(column, 0)
        for index, widget in enumerate(self.controls):
            row, column = divmod(index, columns)
            self.grid.addWidget(widget, row, column, Qt.AlignmentFlag.AlignVCenter)
            self.grid.setColumnStretch(column, 1)
        self.updateGeometry()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._reflow()
