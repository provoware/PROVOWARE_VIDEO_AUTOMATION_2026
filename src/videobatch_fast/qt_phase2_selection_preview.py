from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt


class SelectionPreviewMixin:
    """Selection-driven preview behavior shared by the Phase-2 window."""

    def _show_selection_preview(self) -> None:
        route = getattr(self, "_route_workspace", None)
        if callable(route):
            route("preview")
            return
        if hasattr(self, "phase3_dock"):
            self.phase3_dock.hide()
        self.phase2_dock.show()
        self.phase2_dock.raise_()
        self.phase2_tabs.setCurrentWidget(self.preview_panel)

    def _preview_audio_selection(self) -> None:
        item = self.audio.currentItem()
        if item is None:
            if self.media.currentItem() is None:
                self.preview_panel.set_source(None, include_image=False)
            return
        raw = item.data(Qt.ItemDataRole.UserRole)
        if raw:
            self.preview_panel.set_source(Path(str(raw)), include_image=False)
            self._show_selection_preview()

    def _preview_media_selection(self) -> None:
        item = self.media.currentItem()
        if item is None:
            return
        raw = item.data(Qt.ItemDataRole.UserRole)
        if raw:
            self.preview_panel.set_source(Path(str(raw)), include_image=True)
            self._show_selection_preview()
