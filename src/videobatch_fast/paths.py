from __future__ import annotations

import os
import tempfile
import time
from pathlib import Path

APP_ID = "VideoBatchFast"


def _xdg(name: str, fallback: Path) -> Path:
    raw = os.environ.get(name, "").strip()
    return Path(raw).expanduser() if raw else fallback


def config_dir() -> Path:
    return _xdg("XDG_CONFIG_HOME", Path.home() / ".config") / APP_ID


def state_dir() -> Path:
    return _xdg("XDG_STATE_HOME", Path.home() / ".local" / "state") / APP_ID


def cache_dir() -> Path:
    return _xdg("XDG_CACHE_HOME", Path.home() / ".cache") / APP_ID


def default_output_dir() -> Path:
    return Path.home() / "Videos" / "VideoBatchFast"


def _probe_directory(directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".videobatch-access-", dir=directory)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(b"ok")
            handle.flush()
            os.fsync(handle.fileno())
        Path(temporary).unlink()
    finally:
        try:
            Path(temporary).unlink()
        except FileNotFoundError:
            pass


def _prepare_directory(directory: Path) -> None:
    directory = Path(directory).expanduser()
    try:
        _probe_directory(directory)
        return
    except OSError:
        pass
    parent = directory.parent
    parent.mkdir(parents=True, exist_ok=True)
    quarantine = parent / f".{directory.name}.permission-conflict-{time.strftime('%Y%m%dT%H%M%S')}"
    try:
        if directory.exists() or directory.is_symlink():
            os.replace(directory, quarantine)
        _probe_directory(directory)
    except OSError as exc:
        raise PermissionError(f"VideoBatch kann den Benutzerordner nicht vorbereiten: {directory}: {exc}") from exc


def ensure_app_dirs() -> None:
    for directory in (config_dir(), state_dir(), cache_dir(), default_output_dir()):
        _prepare_directory(directory)
