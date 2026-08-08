from __future__ import annotations

import threading
from pathlib import Path
from tkinter import TclError

from PIL import ImageTk

from .preview_service import PreviewError, build_preview, load_preview_bitmap


class CanonicalQueueThumbnailMixin:
    """Reuse the persistent preview cache for non-blocking queue thumbnails."""

    def _queue_thumbnail_source(self, job) -> Path | None:
        for candidate in tuple(getattr(job, "source_media", ())):
            path = Path(candidate)
            if path.is_file():
                return path
        output = getattr(job, "output", None)
        if output is not None:
            path = Path(output)
            if path.is_file():
                return path
        return None

    def _queue_thumbnail_photo(self, source: Path | None):
        if source is None:
            return None
        cache = getattr(self, "_dashboard_queue_thumbnail_photos", None)
        if cache is None:
            cache = {}
            self._dashboard_queue_thumbnail_photos = cache
        return cache.get(source)

    def _request_queue_thumbnail(self, item_id: str, job) -> None:
        source = self._queue_thumbnail_source(job)
        if source is None:
            return
        photos = getattr(self, "_dashboard_queue_thumbnail_photos", None)
        if photos is None:
            photos = {}
            self._dashboard_queue_thumbnail_photos = photos
        if source in photos:
            try:
                self._dashboard_queue_tree.item(item_id, image=photos[source])
            except TclError:
                pass
            return
        pending = getattr(self, "_dashboard_queue_thumbnail_pending", None)
        if pending is None:
            pending = set()
            self._dashboard_queue_thumbnail_pending = pending
        item_sources = getattr(self, "_dashboard_queue_thumbnail_items", None)
        if item_sources is None:
            item_sources = {}
            self._dashboard_queue_thumbnail_items = item_sources
        item_sources[item_id] = source
        if source in pending:
            return
        pending.add(source)

        def worker() -> None:
            preview_path: Path | None = None
            try:
                preview_path = build_preview(source, 160)
            except (PreviewError, OSError):
                preview_path = None
            try:
                self.root.after(
                    0,
                    lambda: self._install_queue_thumbnail(item_id, source, preview_path),
                )
            except (RuntimeError, TclError):
                pending.discard(source)

        threading.Thread(
            target=worker,
            name=f"queue-thumb-{source.name[:24]}",
            daemon=True,
        ).start()

    def _install_queue_thumbnail(
        self,
        item_id: str,
        source: Path,
        preview_path: Path | None,
    ) -> None:
        pending = getattr(self, "_dashboard_queue_thumbnail_pending", set())
        pending.discard(source)
        if preview_path is None:
            return
        tree = getattr(self, "_dashboard_queue_tree", None)
        if tree is None:
            return
        item_sources = getattr(self, "_dashboard_queue_thumbnail_items", {})
        if item_sources.get(item_id) != source:
            return
        try:
            if not tree.exists(item_id):
                return
            bitmap = load_preview_bitmap(preview_path, max_width=58, max_height=42)
            photo = ImageTk.PhotoImage(bitmap, master=self.root)
            photos = getattr(self, "_dashboard_queue_thumbnail_photos", {})
            photos[source] = photo
            self._dashboard_queue_thumbnail_photos = photos
            tree.item(item_id, image=photo)
        except (PreviewError, TclError, RuntimeError):
            return

    def _prune_queue_thumbnail_refs(self, active_sources: set[Path]) -> None:
        photos = getattr(self, "_dashboard_queue_thumbnail_photos", None)
        if not photos:
            return
        for source in tuple(photos):
            if source not in active_sources:
                photos.pop(source, None)
