from __future__ import annotations

import fcntl
import hashlib
import os
import subprocess
import threading
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from PIL import Image, UnidentifiedImageError

from .paths import cache_dir
from .probe import ffmpeg_path, probe_media


class PreviewError(RuntimeError):
    pass


PREVIEW_CACHE_SUBDIR = "previews"
PREVIEW_CACHE_MAX_BYTES = 1024 * 1024 * 1024
PREVIEW_CACHE_MAX_FILES = 2_000
PREVIEW_CACHE_MIN_FILE_BYTES = 100
PREVIEW_CACHE_TEMP_SUFFIX = ".partial"
PREVIEW_CACHE_STATUS_FILE = ".last-prune"
PREVIEW_CACHE_LOCK_SUBDIR = ".locks"
PREVIEW_CACHE_LOCK_TIMEOUT_SECONDS = 35.0
PREVIEW_CACHE_STALE_PARTIAL_SECONDS = 120.0
_CACHE_KEY_LENGTH = 24
_CACHE_KEY_CHARS = frozenset("0123456789abcdef")


def preview_cache_directory() -> Path:
    directory = cache_dir() / PREVIEW_CACHE_SUBDIR
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def preview_cache_path(source: Path, width: int = 1280) -> Path:
    stat = source.stat()
    digest = hashlib.sha256(
        f"{source.resolve()}:{stat.st_mtime_ns}:{stat.st_size}:{width}".encode()
    ).hexdigest()[:_CACHE_KEY_LENGTH]
    return preview_cache_directory() / f"{digest}.png"


def _is_cache_key(value: str) -> bool:
    return len(value) == _CACHE_KEY_LENGTH and all(
        character in _CACHE_KEY_CHARS for character in value
    )


def _is_managed_preview(path: Path) -> bool:
    return path.suffix.lower() == ".png" and _is_cache_key(path.stem)


def _is_managed_partial(path: Path) -> bool:
    name = path.name
    if not name.startswith(".") or not name.endswith(PREVIEW_CACHE_TEMP_SUFFIX):
        return False
    body = name[1 : -len(PREVIEW_CACHE_TEMP_SUFFIX)]
    key, separator, process_id = body.partition(".png.")
    return bool(separator) and _is_cache_key(key) and process_id.isdigit()


def _cache_entries(directory: Path) -> list[tuple[Path, int, int]]:
    entries: list[tuple[Path, int, int]] = []
    try:
        candidates = tuple(directory.iterdir())
    except OSError:
        return entries
    for path in candidates:
        if not _is_managed_preview(path) or not path.is_file():
            continue
        try:
            stat = path.stat()
        except OSError:
            continue
        entries.append((path, stat.st_size, stat.st_atime_ns))
    return entries


def _record_prune(directory: Path) -> str:
    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    marker = directory / PREVIEW_CACHE_STATUS_FILE
    temporary = marker.with_name(
        f".{marker.name}.{os.getpid()}.{threading.get_ident()}{PREVIEW_CACHE_TEMP_SUFFIX}"
    )
    try:
        temporary.write_text(stamp, encoding="utf-8")
        os.replace(temporary, marker)
    except OSError:
        temporary.unlink(missing_ok=True)
    return stamp


def _read_last_prune(directory: Path) -> str:
    try:
        return (directory / PREVIEW_CACHE_STATUS_FILE).read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def preview_cache_status(
    *,
    directory: Path | None = None,
    max_bytes: int = PREVIEW_CACHE_MAX_BYTES,
    max_files: int = PREVIEW_CACHE_MAX_FILES,
) -> dict[str, int | str]:
    """Return read-only cache facts for diagnostics and user-facing status views."""
    cache = Path(directory) if directory is not None else preview_cache_directory()
    cache.mkdir(parents=True, exist_ok=True)
    entries = _cache_entries(cache)
    total_bytes = sum(size for _path, size, _accessed in entries)
    byte_limit = max(0, int(max_bytes))
    file_limit = max(0, int(max_files))
    usage_percent = int(round((total_bytes / byte_limit) * 100)) if byte_limit else 0
    return {
        "directory": str(cache),
        "files": len(entries),
        "bytes": total_bytes,
        "max_files": file_limit,
        "max_bytes": byte_limit,
        "usage_percent": min(999, max(0, usage_percent)),
        "last_prune_at": _read_last_prune(cache),
    }


def prune_preview_cache(
    *,
    directory: Path | None = None,
    max_bytes: int = PREVIEW_CACHE_MAX_BYTES,
    max_files: int = PREVIEW_CACHE_MAX_FILES,
    protected: Path | None = None,
) -> dict[str, int | str]:
    """Remove oldest managed previews until both configured limits are respected."""
    cache = Path(directory) if directory is not None else preview_cache_directory()
    cache.mkdir(parents=True, exist_ok=True)
    byte_limit = max(0, int(max_bytes))
    file_limit = max(0, int(max_files))
    entries = _cache_entries(cache)
    before_bytes = sum(size for _path, size, _accessed in entries)
    before_files = len(entries)
    protected_resolved = protected.resolve() if protected is not None else None
    removed_bytes = 0
    removed_files = 0

    for path, size, _accessed in sorted(entries, key=lambda item: (item[2], item[0].name)):
        current_files = before_files - removed_files
        current_bytes = before_bytes - removed_bytes
        if current_files <= file_limit and current_bytes <= byte_limit:
            break
        try:
            if protected_resolved is not None and path.resolve() == protected_resolved:
                continue
            path.unlink(missing_ok=True)
        except OSError:
            continue
        removed_files += 1
        removed_bytes += size

    last_prune_at = _record_prune(cache)
    return {
        "before_files": before_files,
        "before_bytes": before_bytes,
        "removed_files": removed_files,
        "removed_bytes": removed_bytes,
        "after_files": before_files - removed_files,
        "after_bytes": before_bytes - removed_bytes,
        "last_prune_at": last_prune_at,
    }


@contextmanager
def preview_generation_lock(
    target: Path,
    *,
    timeout_seconds: float = PREVIEW_CACHE_LOCK_TIMEOUT_SECONDS,
) -> Iterator[None]:
    """Serialize generation for one cache key across threads and Kubuntu processes."""
    lock_directory = target.parent / PREVIEW_CACHE_LOCK_SUBDIR
    lock_path = lock_directory / f"{target.stem}.lock"
    timeout = max(0.0, float(timeout_seconds))
    try:
        lock_directory.mkdir(parents=True, exist_ok=True)
        handle = lock_path.open("a+b")
    except OSError as exc:
        raise PreviewError("Die Vorschau-Sperre konnte nicht sicher vorbereitet werden.") from exc

    deadline = time.monotonic() + timeout
    acquired = False
    try:
        while True:
            try:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                acquired = True
                break
            except BlockingIOError as exc:
                if time.monotonic() >= deadline:
                    raise PreviewError(
                        "Die identische Vorschau wird bereits erzeugt. Bitte erneut versuchen."
                    ) from exc
                time.sleep(0.05)
            except OSError as exc:
                raise PreviewError("Die Vorschau-Sperre konnte nicht aktiviert werden.") from exc
        yield
    finally:
        if acquired:
            try:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            except OSError:
                pass
        handle.close()


def clear_preview_cache(
    *,
    directory: Path | None = None,
    lock_timeout_seconds: float = 0.25,
) -> dict[str, int]:
    """Delete only VideoBatch preview files; originals and foreign cache files stay untouched."""
    cache = Path(directory) if directory is not None else preview_cache_directory()
    cache.mkdir(parents=True, exist_ok=True)
    removed_files = 0
    removed_bytes = 0
    skipped_busy = 0

    for path, size, _accessed in _cache_entries(cache):
        try:
            with preview_generation_lock(path, timeout_seconds=lock_timeout_seconds):
                path.unlink(missing_ok=True)
        except PreviewError:
            skipped_busy += 1
            continue
        except OSError:
            continue
        removed_files += 1
        removed_bytes += size

    removed_partials = 0
    cutoff = time.time() - PREVIEW_CACHE_STALE_PARTIAL_SECONDS
    try:
        candidates = tuple(cache.iterdir())
    except OSError:
        candidates = ()
    for path in candidates:
        if not _is_managed_partial(path):
            continue
        try:
            if path.stat().st_mtime > cutoff:
                continue
            path.unlink(missing_ok=True)
            removed_partials += 1
        except OSError:
            continue

    _record_prune(cache)
    return {
        "removed_files": removed_files,
        "removed_bytes": removed_bytes,
        "removed_partials": removed_partials,
        "skipped_busy": skipped_busy,
    }


def _touch_cache_hit(path: Path) -> None:
    try:
        now = time.time_ns()
        os.utime(path, ns=(now, path.stat().st_mtime_ns))
    except OSError:
        pass


def _use_cache_hit(target: Path) -> bool:
    try:
        if target.exists() and target.stat().st_size > PREVIEW_CACHE_MIN_FILE_BYTES:
            _touch_cache_hit(target)
            prune_preview_cache(protected=target)
            return True
    except OSError:
        target.unlink(missing_ok=True)
    return False


def build_preview(source: Path, width: int = 1280) -> Path:
    source = Path(source)
    if not source.is_file():
        raise PreviewError("Quelldatei ist nicht erreichbar.")
    binary = ffmpeg_path()
    if not binary:
        raise PreviewError("FFmpeg fehlt.")
    target = preview_cache_path(source, width)
    if _use_cache_hit(target):
        return target

    with preview_generation_lock(target):
        if _use_cache_hit(target):
            return target

        info = probe_media(source)
        if info.kind not in {"image", "video"}:
            raise PreviewError("Für diesen Dateityp ist keine Bildvorschau verfügbar.")

        temporary = target.with_name(
            f".{target.name}.{os.getpid()}{PREVIEW_CACHE_TEMP_SUFFIX}"
        )
        temporary.unlink(missing_ok=True)
        command = [binary, "-v", "error", "-y"]
        if info.kind == "video":
            command += ["-ss", "0.5"]
        command += [
            "-i",
            str(source),
            "-frames:v",
            "1",
            "-vf",
            f"scale='min({max(320, width)},iw)':-2",
            str(temporary),
        ]
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=30,
                errors="replace",
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            temporary.unlink(missing_ok=True)
            raise PreviewError("Vorschau-Erzeugung wurde sicher abgebrochen.") from exc

        if (
            result.returncode
            or not temporary.exists()
            or temporary.stat().st_size < PREVIEW_CACHE_MIN_FILE_BYTES
        ):
            temporary.unlink(missing_ok=True)
            detail = (result.stderr or "Vorschau konnte nicht erzeugt werden.").strip().splitlines()[-1]
            raise PreviewError(detail)

        try:
            os.replace(temporary, target)
        except OSError as exc:
            temporary.unlink(missing_ok=True)
            raise PreviewError("Vorschaubild konnte nicht sicher gespeichert werden.") from exc
        _touch_cache_hit(target)
        prune_preview_cache(protected=target)
        return target


MAX_PREVIEW_FILE_BYTES = 64 * 1024 * 1024
MAX_PREVIEW_PIXELS = 24_000_000


def load_preview_bitmap(
    preview_path: Path,
    *,
    max_width: int,
    max_height: int,
) -> Image.Image:
    """Load a generated preview defensively before handing pixels to Tk."""
    path = Path(preview_path)
    try:
        size = path.stat().st_size
    except OSError as exc:
        raise PreviewError("Vorschaudatei ist nicht mehr erreichbar.") from exc
    if size <= 0 or size > MAX_PREVIEW_FILE_BYTES:
        raise PreviewError("Vorschaudatei besitzt eine unzulässige Größe.")
    try:
        with Image.open(path) as source:
            width, height = source.size
            if width <= 0 or height <= 0 or width * height > MAX_PREVIEW_PIXELS:
                raise PreviewError("Vorschaubild überschreitet die sichere Pixelgrenze.")
            image = source.convert("RGBA")
            image.thumbnail((max(64, int(max_width)), max(64, int(max_height))))
            return image.copy()
    except (OSError, UnidentifiedImageError, Image.DecompressionBombError) as exc:
        raise PreviewError("Vorschaubild ist beschädigt oder nicht sicher lesbar.") from exc
