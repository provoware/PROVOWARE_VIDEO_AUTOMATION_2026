from __future__ import annotations

import queue
import threading
from collections import deque
from typing import Any

EventItem = tuple[str, dict[str, Any]]


class EventBuffer:
    """Bounded UI event buffer that coalesces noisy progress events."""

    def __init__(self, maxsize: int = 2000) -> None:
        if maxsize < 10:
            raise ValueError("Eventpuffer muss mindestens zehn Einträge aufnehmen.")
        self.maxsize = maxsize
        self._items: deque[EventItem] = deque()
        self._lock = threading.Lock()
        self.dropped = 0

    def put(self, item: EventItem) -> None:
        name, payload = item
        with self._lock:
            if name == "progress" and self._items and self._items[-1][0] == "progress":
                self._items[-1] = item
                return
            if len(self._items) >= self.maxsize:
                if not self._discard_noisy_event():
                    if name in {"progress", "log"}:
                        self.dropped += 1
                        return
                    self._items.popleft()
                    self.dropped += 1
            self._items.append((name, payload))

    def _discard_noisy_event(self) -> bool:
        for index, (name, _) in enumerate(self._items):
            if name in {"progress", "log"}:
                del self._items[index]
                self.dropped += 1
                return True
        return False

    def get_nowait(self) -> EventItem:
        with self._lock:
            if not self._items:
                raise queue.Empty
            return self._items.popleft()

    def qsize(self) -> int:
        with self._lock:
            return len(self._items)
