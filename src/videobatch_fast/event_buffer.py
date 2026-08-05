from __future__ import annotations

import queue
import threading
from collections import deque
from collections.abc import Mapping

from .app_events import AppEvent


class EventBuffer:
    """Bounded typed UI event buffer that coalesces noisy progress events."""

    def __init__(self, maxsize: int = 2000) -> None:
        if maxsize < 10:
            raise ValueError("Eventpuffer muss mindestens zehn Einträge aufnehmen.")
        self.maxsize = maxsize
        self._items: deque[AppEvent] = deque()
        self._lock = threading.Lock()
        self._next_sequence = 1
        self.dropped = 0

    def put(self, event: AppEvent) -> None:
        if not isinstance(event, AppEvent):
            raise TypeError("EventBuffer.put akzeptiert ausschließlich AppEvent; Legacy-Producer verwenden put_legacy.")
        with self._lock:
            sequenced = event.with_sequence(self._next_sequence)
            self._next_sequence += 1
            if sequenced.name == "progress" and self._items and self._items[-1].name == "progress":
                self._items[-1] = sequenced
                return
            if len(self._items) >= self.maxsize:
                if not self._discard_noisy_event():
                    if sequenced.is_noisy:
                        self.dropped += 1
                        return
                    self._items.popleft()
                    self.dropped += 1
            self._items.append(sequenced)

    def put_legacy(self, name: str, payload: Mapping[str, object]) -> None:
        """Only compatibility boundary for producers not yet migrated to AppEvent."""
        self.put(AppEvent.from_legacy(name, payload))

    def _discard_noisy_event(self) -> bool:
        for index, event in enumerate(self._items):
            if event.is_noisy:
                del self._items[index]
                self.dropped += 1
                return True
        return False

    def get_nowait(self) -> AppEvent:
        with self._lock:
            if not self._items:
                raise queue.Empty
            return self._items.popleft()

    def qsize(self) -> int:
        with self._lock:
            return len(self._items)
