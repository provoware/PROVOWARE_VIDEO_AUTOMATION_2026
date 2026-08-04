from __future__ import annotations

from pathlib import Path

from PIL import ImageTk

from .preview_service import load_preview_bitmap
from .probe import classify_extension, probe_media
from .selection_preview_controller import resolve_tree_selection
from .text_resources import text


class UiSelectionPreviewMixin:
    """Crash-safe selection handling for the project media and audio lists."""

    def _selection_changed(self, audio: bool) -> None:
        """Debounce clicks and keep every preview operation outside Tk."""
        try:
            tree = self.audio_tree if audio else self.media_tree
            path = resolve_tree_selection(tree, self.tree_path_map)
        except Exception as exc:
            self._event(
                "MEDIA_SELECTION_FAILED",
                text("ui.selection_preview.selection_error_title"),
                str(exc),
                level="warning",
                solution=text("ui.selection_preview.selection_error_solution"),
            )
            return
        if path is None:
            self._cancel_pending_selection_preview()
            return
        self._schedule_selection_preview(path, audio=audio, delay_ms=180)

    def _cancel_pending_selection_preview(self) -> None:
        if self._preview_debounce_job is not None:
            try:
                self.root.after_cancel(self._preview_debounce_job)
            except Exception:
                pass
            self._preview_debounce_job = None
        self.preview_request = self.selection_previews.invalidate()

    def _schedule_selection_preview(self, path: Path, *, audio: bool, delay_ms: int) -> None:
        self._cancel_pending_selection_preview()
        self.preview_source = Path(path)
        self.preview_status.set(
            text("ui.selection_preview.audio_pending")
            if audio
            else text("ui.selection_preview.image_pending")
        )
        self.preview_meta.set(self.preview_source.name)

        def dispatch() -> None:
            self._preview_debounce_job = None
            if self.preview_source != path:
                return
            width = max(480, min(2200, round(720 * self.preview_zoom.get() / 100)))
            self.preview_request = self.selection_previews.request(
                path,
                width,
                include_image=not audio,
            )

        self._preview_debounce_job = self.root.after(max(0, int(delay_ms)), dispatch)

    def _request_preview(self, path: Path) -> None:
        """Compatibility entry point for zoom and preview actions."""
        self._schedule_selection_preview(Path(path), audio=False, delay_ms=0)

    def _apply_selection_preview(self, payload: dict) -> None:
        if payload.get("token") != self.preview_request:
            return
        path = Path(payload["path"])
        if path != self.preview_source:
            return
        info = payload.get("info")
        size_bytes = int(payload.get("size_bytes", 0) or 0)
        if not payload.get("include_image"):
            self.preview_status.set(text("ui.selection_preview.audio_ready"))
            self.preview_meta.set(
                f"{path.name} · {self._duration(getattr(info, 'duration', None))} · "
                f"{getattr(info, 'codec', '') or text('ui.selection_preview.format_check')} · "
                f"{size_bytes / 1024**2:.1f} MB"
            )
            self.guidance_text.set(text("ui.selection_preview.audio_guidance"))
            return
        self._show_preview(
            path,
            Path(payload["preview"]),
            info=info,
            size_bytes=size_bytes,
        )

    def _apply_selection_preview_failure(self, payload: dict) -> None:
        if payload.get("token") != self.preview_request:
            return
        path = Path(payload.get("path", self.preview_source or ""))
        if path != self.preview_source:
            return
        self.preview_status.set(text("ui.selection_preview.failed_status"))
        self.preview_meta.set(path.name)
        self._show_error("PREVIEW_FAILED", str(payload.get("message", "")))

    def _show_preview(
        self,
        path: Path,
        preview_path: Path,
        *,
        info=None,
        size_bytes: int | None = None,
    ) -> None:
        try:
            max_width = max(320, self.preview_label.winfo_width() - 24)
            max_height = max(220, self.preview_label.winfo_height() - 24)
            bitmap = load_preview_bitmap(
                preview_path,
                max_width=max_width,
                max_height=max_height,
            )
            photo = ImageTk.PhotoImage(bitmap, master=self.root)
        except Exception as exc:
            self._show_error("PREVIEW_FAILED", str(exc))
            return
        self.preview_photo = photo
        self.preview_label.configure(image=photo, text="")
        if info is None:
            info = probe_media(path)
        if size_bytes is None:
            try:
                size_bytes = path.stat().st_size
            except OSError:
                size_bytes = int(getattr(info, "size_bytes", 0) or 0)
        geometry = (
            f"{info.width} × {info.height}"
            if getattr(info, "width", None) and getattr(info, "height", None)
            else text("ui.selection_preview.unknown_resolution")
        )
        self.preview_meta.set(
            f"{path.name} · {geometry} · {int(size_bytes) / 1024**2:.1f} MB · "
            f"Zoom {self.preview_zoom.get()} %"
        )
        self.preview_status.set(text("ui.selection_preview.ready_status"))
        self.guidance_text.set(text("ui.selection_preview.ready_guidance"))

    def _probe_selected_media(self) -> None:
        paths = self._selected_paths(False) or self._selected_paths(True)
        path = paths[-1] if paths else self.preview_source
        if path is None:
            self.guidance_text.set("Wähle zuerst eine Audio-, Bild- oder Videodatei aus.")
            return
        self._schedule_selection_preview(
            Path(path),
            audio=classify_extension(Path(path)) == "audio",
            delay_ms=0,
        )
        self.guidance_text.set("Die ausgewählte Datei wird erneut sicher geprüft.")
