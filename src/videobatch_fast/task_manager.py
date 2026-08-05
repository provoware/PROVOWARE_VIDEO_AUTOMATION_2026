from __future__ import annotations

import threading
import time
import traceback
from collections.abc import Callable

TaskErrorCallback = Callable[[str, Exception, str], None]


class TaskManager:
    """Track background tasks and make application shutdown bounded and observable."""

    def __init__(self, on_error: TaskErrorCallback | None = None) -> None:
        self._lock = threading.Lock()
        self._threads: dict[str, threading.Thread] = {}
        self._errors: list[str] = []
        self._closing = False
        self._on_error = on_error

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
                except Exception as exc:
                    detail = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))[-16_000:]
                    with self._lock:
                        self._errors.append(f"{name}: {type(exc).__name__}: {exc}")
                        if len(self._errors) > 20:
                            del self._errors[:-20]
                    if self._on_error is not None:
                        try:
                            self._on_error(name, exc, detail)
                        except Exception:
                            pass
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

    def errors(self) -> tuple[str, ...]:
        with self._lock:
            return tuple(self._errors)

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
