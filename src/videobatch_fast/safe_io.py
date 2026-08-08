from __future__ import annotations

import errno
import json
import os
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator


class SafeIoError(RuntimeError):
    """Raised when a durable file operation cannot be completed safely."""




def _process_is_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def cleanup_atomic_tempfiles(path: Path | str, *, legacy_min_age_seconds: float = 300.0) -> list[Path]:
    """Remove crash-left atomic tempfiles without touching a live writer.

    New temp names carry the creator PID and can be removed immediately when that
    process no longer exists. Legacy temp names are removed only after a safety age.
    """
    target = Path(path).expanduser()
    removed: list[Path] = []
    now = time.time()
    prefix = f".{target.name}."
    for candidate in target.parent.glob(f".{target.name}.*.tmp"):
        try:
            middle = candidate.name[len(prefix):-4]
            pid_text = middle.split('.', 1)[0]
            pid = int(pid_text) if pid_text.isdigit() else None
            if pid is not None:
                if pid == os.getpid() or _process_is_alive(pid):
                    continue
            else:
                if now - candidate.stat().st_mtime < legacy_min_age_seconds:
                    continue
            candidate.unlink(missing_ok=True)
            removed.append(candidate)
        except (OSError, ValueError):
            continue
    if removed:
        fsync_directory(target.parent)
    return removed


@contextmanager
def exclusive_file_lock(path: Path | str, *, timeout_seconds: float = 5.0, poll_seconds: float = 0.05) -> Iterator[Path]:
    """Serialize cooperating writers across processes on POSIX/Linux.

    The lock is advisory and intentionally bounded: a wedged peer cannot block the
    application forever. flock locks are released by the kernel after process death.
    """
    lock_path = Path(path).expanduser()
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        import fcntl
    except ImportError as exc:  # pragma: no cover - current release target is Linux
        raise SafeIoError('Prozessübergreifende Dateisperre wird auf diesem System nicht unterstützt.') from exc
    descriptor = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o600)
    deadline = time.monotonic() + max(0.0, timeout_seconds)
    try:
        while True:
            try:
                fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except OSError as exc:
                if exc.errno not in (errno.EACCES, errno.EAGAIN):
                    raise SafeIoError(f'Dateisperre konnte nicht gesetzt werden: {lock_path}: {exc}') from exc
                if time.monotonic() >= deadline:
                    raise SafeIoError(f'Zeitlimit beim Warten auf Dateisperre überschritten: {lock_path}') from exc
                time.sleep(max(0.001, poll_seconds))
        yield lock_path
    finally:
        try:
            fcntl.flock(descriptor, fcntl.LOCK_UN)
        finally:
            os.close(descriptor)

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



def atomic_commit_file(temporary: Path | str, target: Path | str) -> Path:
    """Durably commit an already-written file into place in the same directory."""
    source = Path(temporary).expanduser()
    destination = Path(target).expanduser()
    if source.parent.resolve() != destination.parent.resolve():
        raise SafeIoError("Atomarer Commit erfordert Quelldatei und Ziel im selben Verzeichnis.")
    try:
        with source.open("rb") as handle:
            os.fsync(handle.fileno())
        os.replace(source, destination)
        fsync_directory(destination.parent)
    except OSError as exc:
        raise SafeIoError(f"Datei konnte nicht dauerhaft atomar übernommen werden: {destination}: {exc}") from exc
    return destination

def atomic_write_bytes(path: Path | str, payload: bytes, *, mode: int = 0o600) -> Path:
    """Write bytes in the target directory and replace the destination durably."""
    target = Path(path).expanduser()
    target.parent.mkdir(parents=True, exist_ok=True)
    cleanup_atomic_tempfiles(target)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{target.name}.{os.getpid()}.", suffix=".tmp", dir=target.parent)
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
