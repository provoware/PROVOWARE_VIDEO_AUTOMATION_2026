from __future__ import annotations

import threading
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from .app_events import AppEvent
from .models import MediaInfo
from .preview_service import build_preview
from .probe import probe_media
from .selection_preview_events import (
    SelectionPreviewFailedPayload,
    SelectionPreviewReadyPayload,
)

EventCallback = Callable[[AppEvent], None]
PreviewBuilder = Callable[[Path, int], Path]
MediaProber = Callable[[Path], MediaInfo]


@dataclass(frozen=True, slots=True)
class SelectionPreviewRequest:
    token: int
    path: Path
    width: int
    include_image: bool


def resolve_tree_selection(tree: object, path_map: dict[str, Path]) -> Path | None:
    """Return the actively clicked row, then fall back to the latest selected row."""
    selection = getattr(tree, "selection")
    focus_value = getattr(tree, "focus")
    selected = tuple(selection())
    if not selected:
        return None
    focus = str(focus_value() or "")
    if focus in selected and focus in path_map:
        return path_map[focus]
    for item_id in reversed(selected):
        path = path_map.get(str(item_id))
        if path is not None:
            return path
    return None


class SelectionPreviewController:
    """Serialize selection previews and publish only the newest request.

    Tk widgets are never touched by this worker. Rapid clicks replace the pending
    request instead of creating parallel FFmpeg processes. The external callback
    receives exactly one validated ``AppEvent`` per completed current request.
    """

    def __init__(
        self,
        emit: EventCallback,
        *,
        preview_builder: PreviewBuilder = build_preview,
        media_prober: MediaProber = probe_media,
    ) -> None:
        self._emit = emit
        self._preview_builder = preview_builder
        self._media_prober = media_prober
        self._condition = threading.Condition()
        self._pending: SelectionPreviewRequest | None = None
        self._token = 0
        self._closed = False
        self._callback_errors: list[str] = []
        self._thread = threading.Thread(
            target=self._worker,
            daemon=True,
            name="VideoBatchSelectionPreview",
        )
        self._thread.start()

    @property
    def callback_errors(self) -> tuple[str, ...]:
        return tuple(self._callback_errors)

    def request(self, path: Path, width: int, *, include_image: bool) -> int:
        with self._condition:
            if self._closed:
                return self._token
            self._token += 1
            self._pending = SelectionPreviewRequest(
                token=self._token,
                path=Path(path),
                width=max(320, min(2200, int(width))),
                include_image=bool(include_image),
            )
            self._condition.notify()
            return self._token

    def invalidate(self) -> int:
        with self._condition:
            self._token += 1
            self._pending = None
            self._condition.notify()
            return self._token

    def shutdown(self, timeout: float = 3.0) -> bool:
        with self._condition:
            self._closed = True
            self._pending = None
            self._condition.notify_all()
        self._thread.join(timeout=max(0.0, timeout))
        return not self._thread.is_alive()

    def _is_current(self, request: SelectionPreviewRequest) -> bool:
        with self._condition:
            return not self._closed and request.token == self._token

    def _next_request(self) -> SelectionPreviewRequest | None:
        with self._condition:
            while self._pending is None and not self._closed:
                self._condition.wait()
            if self._closed:
                return None
            request = self._pending
            self._pending = None
            return request

    def _publish(self, event: AppEvent) -> None:
        try:
            self._emit(event)
        except Exception as exc:
            self._callback_errors.append(f"{type(exc).__name__}: {exc}")
            if len(self._callback_errors) > 20:
                del self._callback_errors[:-20]

    def _ready_event(
        self,
        request: SelectionPreviewRequest,
        preview_path: Path | None,
        info: MediaInfo,
        size_bytes: int,
    ) -> AppEvent:
        return AppEvent(
            name="selection_preview_ready",
            payload=SelectionPreviewReadyPayload(
                token=request.token,
                path=request.path,
                preview=preview_path,
                info=info,
                size_bytes=size_bytes,
                include_image=request.include_image,
            ),
            operation_id=f"selection-preview-{request.token}",
        )

    def _failed_event(self, request: SelectionPreviewRequest, exc: Exception) -> AppEvent:
        return AppEvent(
            name="selection_preview_failed",
            payload=SelectionPreviewFailedPayload(
                token=request.token,
                path=request.path,
                message=f"{type(exc).__name__}: {exc}",
                include_image=request.include_image,
            ),
            operation_id=f"selection-preview-{request.token}",
        )

    def _worker(self) -> None:
        while True:
            request = self._next_request()
            if request is None:
                return
            try:
                preview_path = (
                    self._preview_builder(request.path, request.width)
                    if request.include_image
                    else None
                )
                info = self._media_prober(request.path)
                try:
                    size_bytes = request.path.stat().st_size
                except OSError:
                    size_bytes = int(info.size_bytes or 0)
                event = self._ready_event(request, preview_path, info, size_bytes)
            except Exception as exc:
                event = self._failed_event(request, exc)
            if self._is_current(request):
                self._publish(event)
