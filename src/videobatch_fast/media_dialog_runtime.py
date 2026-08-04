from __future__ import annotations

import queue
from tkinter import TclError


class MediaDialogRuntimeMixin:
    """Main-thread event bridge and bounded worker coordination for Tk dialogs."""

    def _start_event_pump(self) -> None:
        self._poll_job = self.window.after(25, self._poll_background_events)

    def _poll_background_events(self) -> None:
        self._poll_job = None
        if self._closed:
            return
        for _ in range(96):
            try:
                event = self._events.get_nowait()
            except queue.Empty:
                break
            self._dispatch_background_event(event)
        try:
            if self.window.winfo_exists():
                self._poll_job = self.window.after(25, self._poll_background_events)
        except TclError:
            self._closed = True

    def _dispatch_background_event(self, event: tuple) -> None:
        kind = event[0]
        if kind == "scan_batch":
            _, generation, batch = event
            self._apply_scan_batch(generation, batch)
        elif kind == "scan_done":
            _, generation, error = event
            self._finish_scan(generation, error)
        elif kind == "preview":
            _, path, generation, payload = event
            self._show_preview(path, generation, payload)
        elif kind == "thumbnail":
            _, path, preview_path, error = event
            self._show_thumbnail(path, preview_path, error)

    def _post_event(self, event: tuple) -> bool:
        while not self._closed:
            try:
                self._events.put(event, timeout=0.1)
                return True
            except queue.Full:
                continue
        return False

    def _submit(self, function, *args):
        if self._closed:
            return None
        try:
            return self._executor.submit(function, *args)
        except RuntimeError:
            return None

    def _preview_enter(self) -> None:
        with self._preview_lock:
            self._preview_workers += 1
            self._preview_busy.set()

    def _preview_leave(self) -> None:
        with self._preview_lock:
            self._preview_workers = max(0, self._preview_workers - 1)
            if self._preview_workers == 0:
                self._preview_busy.clear()
