from __future__ import annotations

import errno
import os
from pathlib import Path

from .paths import state_dir


class RenderBusyError(RuntimeError):
    """Raised when another VideoBatch process already owns the global render lease."""


def render_lock_path() -> Path:
    path = state_dir() / "runtime"
    path.mkdir(parents=True, exist_ok=True)
    return path / "render.lock"


class RenderExecutionLease:
    def __init__(self, path: Path | None = None) -> None:
        self.path = Path(path or render_lock_path())
        self._descriptor: int | None = None

    @property
    def acquired(self) -> bool:
        return self._descriptor is not None

    def acquire(self) -> None:
        if self._descriptor is not None:
            return
        try:
            import fcntl
        except ImportError as exc:  # pragma: no cover - Linux release target
            raise RuntimeError("Globale Render-Sperre wird auf diesem System nicht unterstützt.") from exc
        self.path.parent.mkdir(parents=True, exist_ok=True)
        descriptor = os.open(self.path, os.O_CREAT | os.O_RDWR, 0o600)
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            os.close(descriptor)
            if exc.errno in (errno.EACCES, errno.EAGAIN):
                raise RenderBusyError("Ein anderer VideoBatch-Renderlauf ist bereits aktiv.") from exc
            raise RuntimeError(f"Globale Render-Sperre konnte nicht gesetzt werden: {exc}") from exc
        try:
            os.ftruncate(descriptor, 0)
            os.write(descriptor, f"pid={os.getpid()}\n".encode("ascii"))
            os.fsync(descriptor)
        except OSError:
            fcntl.flock(descriptor, fcntl.LOCK_UN)
            os.close(descriptor)
            raise
        self._descriptor = descriptor

    def release(self) -> None:
        descriptor = self._descriptor
        if descriptor is None:
            return
        self._descriptor = None
        try:
            import fcntl
            fcntl.flock(descriptor, fcntl.LOCK_UN)
        finally:
            os.close(descriptor)
