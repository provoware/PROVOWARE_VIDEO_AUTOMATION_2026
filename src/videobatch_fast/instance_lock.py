from __future__ import annotations

import fcntl
import os
import time
from pathlib import Path
from types import TracebackType

from .paths import state_dir
from .safe_io import atomic_write_json


class InstanceAlreadyRunning(RuntimeError):
    pass


def focus_request_path() -> Path:
    return state_dir() / "locks" / "focus_request.json"


def request_existing_instance_focus() -> int:
    """Leave an atomic focus request that the running UI can consume."""
    token = time.time_ns()
    atomic_write_json(
        focus_request_path(),
        {"schema_version": 1, "token": token, "requester_pid": os.getpid()},
    )
    return token


def focus_request_token() -> int:
    path = focus_request_path()
    if not path.is_file() or path.is_symlink():
        return 0
    try:
        import json

        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict) or payload.get("schema_version") != 1:
            return 0
        return max(0, int(payload.get("token", 0)))
    except (OSError, UnicodeError, ValueError, TypeError):
        return 0


class ApplicationLock:
    """Linux/POSIX single-instance lock with useful owner diagnostics."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or (state_dir() / "locks" / "application.lock")
        self._handle = None

    def acquire(self) -> "ApplicationLock":
        self.path.parent.mkdir(parents=True, exist_ok=True)
        handle = self.path.open("a+", encoding="utf-8")
        try:
            os.chmod(self.path, 0o600)
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            handle.seek(0)
            owner = handle.read().strip() or "unbekannt"
            handle.close()
            raise InstanceAlreadyRunning(
                f"VideoBatch läuft bereits. Sperrdatei: {self.path} · Besitzer: {owner}"
            ) from exc
        handle.seek(0)
        handle.truncate()
        handle.write(f"pid={os.getpid()}\n")
        handle.flush()
        os.fsync(handle.fileno())
        self._handle = handle
        return self

    def release(self) -> None:
        handle = self._handle
        self._handle = None
        if handle is None:
            return
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        finally:
            handle.close()

    def __enter__(self) -> "ApplicationLock":
        return self.acquire()

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.release()
