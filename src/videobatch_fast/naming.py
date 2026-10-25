from __future__ import annotations

import fcntl
import json
import os
import re
import time
import unicodedata
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable

_RESERVED = {".", "..", "CON", "PRN", "AUX", "NUL"}
_RESERVATION_SUFFIX = ".videobatch.reserve"


def safe_stem(value: str, *, fallback: str = "Video") -> str:
    text = unicodedata.normalize("NFKC", str(value)).strip()
    text = "".join(char if char.isalnum() or char in " ._-" else "_" for char in text)
    text = re.sub(r"\s+", " ", text).strip(" ._")
    if not text or text.upper() in _RESERVED:
        text = fallback
    return text[:120]


def timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S_%f")


def unique_output_path(directory: Path, audio: Path, *, reserved: set[Path] | None = None, index: int | None = None) -> Path:
    directory = Path(directory)
    reserved = reserved if reserved is not None else set()
    suffix = f"_{index:03d}" if index is not None else ""
    base = f"{safe_stem(audio.stem)}_{timestamp()}{suffix}"
    candidate = directory / f"{base}.mp4"
    counter = 2
    while candidate.exists() or candidate in reserved or reservation_marker(candidate).exists():
        candidate = directory / f"{base}_{counter}.mp4"
        counter += 1
    reserved.add(candidate)
    return candidate


def reservation_marker(target: Path) -> Path:
    target = Path(target)
    return target.with_name(f".{target.name}{_RESERVATION_SUFFIX}")


def _pid_is_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _remove_stale_marker(marker: Path, *, stale_after: float = 86_400.0) -> bool:
    # Never reclaim a marker held by another cooperating writer, even when old.
    try:
        descriptor = os.open(marker, os.O_RDONLY | os.O_NOFOLLOW)
    except OSError:
        return False
    try:
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return False
        stat = os.fstat(descriptor)
        with os.fdopen(os.dup(descriptor), "r", encoding="utf-8") as handle:
            try:
                payload = json.load(handle)
                pid = int(payload.get("pid", 0) or 0)
            except (ValueError, TypeError, AttributeError):
                pid = 0
        if pid > 0 and _pid_is_alive(pid):
            return False
        if pid <= 0 and time.time() - stat.st_mtime <= stale_after:
            return False
        current = marker.lstat()
        if (current.st_dev, current.st_ino) != (stat.st_dev, stat.st_ino):
            return False
        marker.unlink()
        return True
    except (OSError, UnicodeError):
        return False
    finally:
        os.close(descriptor)


@dataclass(slots=True)
class OutputReservation:
    target: Path
    marker: Path
    released: bool = False
    owner_token: str = ""
    descriptor: int = -1

    def release(self) -> None:
        if self.released:
            return
        try:
            try:
                payload = json.loads(self.marker.read_text(encoding="utf-8"))
            except (OSError, ValueError, UnicodeError):
                return
            if isinstance(payload, dict) and payload.get("owner_token") == self.owner_token:
                self.marker.unlink(missing_ok=True)
        finally:
            if self.descriptor >= 0:
                os.close(self.descriptor)
                self.descriptor = -1
            self.released = True


def reserve_output_targets(targets: Iterable[Path]) -> list[OutputReservation]:
    reservations: list[OutputReservation] = []
    seen: set[Path] = set()
    try:
        for raw_target in targets:
            target = Path(raw_target).resolve()
            if target in seen:
                raise FileExistsError(f"Doppelter Zielpfad im Stapel: {target}")
            seen.add(target)
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists():
                raise FileExistsError(f"Ausgabedatei existiert bereits: {target}")
            marker = reservation_marker(target)
            if marker.exists():
                _remove_stale_marker(marker)
            flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
            try:
                fd = os.open(marker, flags, 0o600)
            except FileExistsError as exc:
                raise FileExistsError(f"Ziel ist bereits durch einen anderen Auftrag reserviert: {target}") from exc
            owner_token = uuid.uuid4().hex
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                payload = {
                    "owner_token": owner_token,
                    "schema_version": 1,
                    "pid": os.getpid(),
                    "created_unix": time.time(),
                    "target": str(target),
                }
                os.write(fd, (json.dumps(payload, ensure_ascii=False) + "\n").encode("utf-8"))
                os.fsync(fd)
            except BaseException:
                # The descriptor remains ours until publication has completed.
                marker.unlink(missing_ok=True)
                os.close(fd)
                raise
            reservations.append(OutputReservation(target, marker, owner_token=owner_token, descriptor=fd))
        return reservations
    except Exception:
        for reservation in reservations:
            reservation.release()
        raise


def release_output_reservations(reservations: Iterable[OutputReservation]) -> None:
    for reservation in reservations:
        reservation.release()


def used_name(path: Path, suffix: str = "__verwendet") -> str:
    stem = path.stem
    while stem.endswith(suffix):
        stem = stem[: -len(suffix)]
    return f"{safe_stem(stem + suffix)}{path.suffix.lower()}"
