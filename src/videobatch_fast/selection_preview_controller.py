from __future__ import annotations

import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from .preview_service import build_preview
from .probe import probe_media

Emit = Callable[[tuple[str, dict[str, Any]]], None]
PreviewBuilder = Callable[[Path, int], Path]
MediaProber = Callable[[Path], Any]


@dataclass(frozen=True)
class SelectionPreviewRequest:
    token: int
    path: Path
    width: int
    include_image: bool


def resolve_tree_selection(tree: Any, path_map: dict[str, Path]) -> Path | None:
    """Return the actively clicked row, then fall back to the latest selected row."""
    selected = tuple(tree.selection())
    if not selected:
        return None
    focus = str(tree.focus() or "")
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
    request instead of creating parallel FFmpeg processes.
    """

    def __init__(
        self,
        emit: Emit,
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
        self._thread = threading.Thread(
            target=self._worker,
            daemon=True,
            name="VideoBatchSelectionPreview",
        )
        self._thread.start()

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
                    size_bytes = int(getattr(info, "size_bytes", 0) or 0)
                payload = {
                    "token": request.token,
                    "path": request.path,
                    "preview": preview_path,
                    "info": info,
                    "size_bytes": size_bytes,
                    "include_image": request.include_image,
                }
                event_name = "selection_preview_ready"
            except Exception as exc:
                payload = {
                    "token": request.token,
                    "path": request.path,
                    "message": f"{type(exc).__name__}: {exc}",
                    "include_image": request.include_image,
                }
                event_name = "selection_preview_failed"
            if self._is_current(request):
                self._emit((event_name, payload))
