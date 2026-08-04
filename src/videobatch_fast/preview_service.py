from __future__ import annotations

import hashlib
import os
import subprocess
import time
from pathlib import Path

from PIL import Image, UnidentifiedImageError

from .paths import cache_dir
from .probe import ffmpeg_path, probe_media


class PreviewError(RuntimeError):
    pass


PREVIEW_CACHE_SUBDIR = "previews"
PREVIEW_CACHE_MAX_BYTES = 256 * 1024 * 1024
PREVIEW_CACHE_MAX_FILES = 2_000
PREVIEW_CACHE_MIN_FILE_BYTES = 100
PREVIEW_CACHE_TEMP_SUFFIX = ".partial"


def preview_cache_directory() -> Path:
    directory = cache_dir() / PREVIEW_CACHE_SUBDIR
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def preview_cache_path(source: Path, width: int = 1280) -> Path:
    stat = source.stat()
    digest = hashlib.sha256(
        f"{source.resolve()}:{stat.st_mtime_ns}:{stat.st_size}:{width}".encode()
    ).hexdigest()[:24]
    return preview_cache_directory() / f"{digest}.png"


def _cache_entries(directory: Path) -> list[tuple[Path, int, int]]:
    entries: list[tuple[Path, int, int]] = []
    try:
        candidates = tuple(directory.iterdir())
    except OSError:
        return entries
    for path in candidates:
        if path.suffix.lower() != ".png" or not path.is_file():
            continue
        try:
            stat = path.stat()
        except OSError:
            continue
        entries.append((path, stat.st_size, stat.st_atime_ns))
    return entries


def prune_preview_cache(
    *,
    directory: Path | None = None,
    max_bytes: int = PREVIEW_CACHE_MAX_BYTES,
    max_files: int = PREVIEW_CACHE_MAX_FILES,
    protected: Path | None = None,
) -> dict[str, int]:
    """Remove oldest previews until both configured limits are respected."""
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

    return {
        "before_files": before_files,
        "before_bytes": before_bytes,
        "removed_files": removed_files,
        "removed_bytes": removed_bytes,
        "after_files": before_files - removed_files,
        "after_bytes": before_bytes - removed_bytes,
    }


def _touch_cache_hit(path: Path) -> None:
    try:
        now = time.time_ns()
        os.utime(path, ns=(now, path.stat().st_mtime_ns))
    except OSError:
        pass


def build_preview(source: Path, width: int = 1280) -> Path:
    source = Path(source)
    if not source.is_file():
        raise PreviewError("Quelldatei ist nicht erreichbar.")
    binary = ffmpeg_path()
    if not binary:
        raise PreviewError("FFmpeg fehlt.")
    target = preview_cache_path(source, width)
    try:
        if target.exists() and target.stat().st_size > PREVIEW_CACHE_MIN_FILE_BYTES:
            _touch_cache_hit(target)
            prune_preview_cache(protected=target)
            return target
    except OSError:
        target.unlink(missing_ok=True)

    info = probe_media(source)
    if info.kind not in {"image", "video"}:
        raise PreviewError("Für diesen Dateityp ist keine Bildvorschau verfügbar.")

    temporary = target.with_name(f".{target.name}.{os.getpid()}{PREVIEW_CACHE_TEMP_SUFFIX}")
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

    if result.returncode or not temporary.exists() or temporary.stat().st_size < PREVIEW_CACHE_MIN_FILE_BYTES:
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
