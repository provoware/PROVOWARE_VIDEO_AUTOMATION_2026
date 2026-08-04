from __future__ import annotations

import json
import os
import tempfile
import time
from pathlib import Path
from typing import Any


class SafeIoError(RuntimeError):
    """Raised when a durable file operation cannot be completed safely."""


def fsync_directory(directory: Path) -> None:
    """Persist directory metadata after replace/rename operations on POSIX."""
    try:
        descriptor = os.open(directory, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    except OSError as exc:
        raise SafeIoError(f"Ordner konnte nicht zur Synchronisation geöffnet werden: {directory}: {exc}") from exc
    try:
        os.fsync(descriptor)
    except OSError as exc:
        raise SafeIoError(f"Ordner konnte nicht dauerhaft synchronisiert werden: {directory}: {exc}") from exc
    finally:
        os.close(descriptor)


def atomic_write_bytes(path: Path | str, payload: bytes, *, mode: int = 0o600) -> Path:
    """Write bytes in the target directory and replace the destination durably."""
    target = Path(path).expanduser()
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".tmp", dir=target.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, mode)
        os.replace(temporary, target)
        fsync_directory(target.parent)
    except Exception:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass
        raise
    return target


def atomic_write_text(path: Path | str, text: str, *, mode: int = 0o600) -> Path:
    return atomic_write_bytes(path, text.encode("utf-8"), mode=mode)


def atomic_write_json(path: Path | str, value: Any, *, mode: int = 0o600, indent: int = 2) -> Path:
    payload = json.dumps(value, ensure_ascii=False, indent=indent, sort_keys=True) + "\n"
    return atomic_write_text(path, payload, mode=mode)


def read_json(path: Path | str) -> Any:
    target = Path(path).expanduser()
    return json.loads(target.read_text(encoding="utf-8"))


def quarantine_file(path: Path | str, *, label: str = "corrupt") -> Path | None:
    """Move a suspicious file aside without overwriting an earlier quarantine."""
    source = Path(path).expanduser()
    if not source.exists() and not source.is_symlink():
        return None
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    for counter in range(1000):
        suffix = f".{label}.{timestamp}" + (f".{counter}" if counter else "")
        candidate = source.with_name(f"{source.stem}{suffix}{source.suffix}")
        if candidate.exists() or candidate.is_symlink():
            continue
        try:
            os.replace(source, candidate)
            fsync_directory(source.parent)
            return candidate
        except OSError as exc:
            raise SafeIoError(f"Beschädigte Datei konnte nicht sicher quarantänisiert werden: {source}: {exc}") from exc
    raise SafeIoError(f"Kein freier Quarantänename für {source}")
