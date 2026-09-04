from __future__ import annotations

import threading
from dataclasses import dataclass

RAM_LIMIT_PRESETS_GB = (1.0, 1.5, 2.0, 2.5)
GIB = 1024**3


@dataclass(frozen=True, slots=True)
class ExecutionControlSnapshot:
    paused: bool
    cpu_limit_percent: int | None
    memory_limit_bytes: int | None


class ExecutionControl:
    """Thread-safe runtime controls shared by UI, batch runner and FFmpeg monitor."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._paused = False
        self._cpu_limit_percent: int | None = None
        self._memory_limit_bytes: int | None = None

    def snapshot(self) -> ExecutionControlSnapshot:
        with self._lock:
            return ExecutionControlSnapshot(
                paused=self._paused,
                cpu_limit_percent=self._cpu_limit_percent,
                memory_limit_bytes=self._memory_limit_bytes,
            )

    def pause(self) -> None:
        with self._lock:
            self._paused = True

    def resume(self) -> None:
        with self._lock:
            self._paused = False

    def set_cpu_limit_50(self, enabled: bool) -> None:
        with self._lock:
            self._cpu_limit_percent = 50 if enabled else None

    def set_memory_limit_gb(self, gigabytes: float | None) -> None:
        if gigabytes is not None and float(gigabytes) not in RAM_LIMIT_PRESETS_GB:
            raise ValueError(f"RAM-Grenze muss eine der Vorgaben {RAM_LIMIT_PRESETS_GB!r} sein.")
        with self._lock:
            self._memory_limit_bytes = None if gigabytes is None else int(float(gigabytes) * GIB)

    @property
    def paused(self) -> bool:
        return self.snapshot().paused
