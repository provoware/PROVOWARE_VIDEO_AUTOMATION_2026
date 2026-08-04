from __future__ import annotations

import threading
import time
from collections.abc import Callable


class TaskManager:
    """Track background tasks and make application shutdown bounded and observable."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._threads: dict[str, threading.Thread] = {}
        self._closing = False

    def start(self, name: str, target: Callable[[], None], *, replace: bool = False) -> bool:
        with self._lock:
            if self._closing:
                return False
            current = self._threads.get(name)
            if current is not None and current.is_alive() and not replace:
                return False

            def run() -> None:
                try:
                    target()
                finally:
                    with self._lock:
                        if self._threads.get(name) is threading.current_thread():
                            self._threads.pop(name, None)

            thread = threading.Thread(target=run, daemon=True, name=f"VideoBatchTask-{name}")
            self._threads[name] = thread
            thread.start()
            return True

    def active_names(self) -> tuple[str, ...]:
        with self._lock:
            return tuple(sorted(name for name, thread in self._threads.items() if thread.is_alive()))

    def shutdown(self, timeout: float = 5.0) -> tuple[str, ...]:
        deadline = time.monotonic() + max(0.0, timeout)
        with self._lock:
            self._closing = True
            threads = list(self._threads.items())
        for _, thread in threads:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            thread.join(timeout=remaining)
        return self.active_names()
