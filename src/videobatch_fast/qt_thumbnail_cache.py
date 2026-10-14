"""Bounded persistent image thumbnails shared across MediaImportDialog instances.

All decoding and disk I/O must run in a worker, never in the GUI thread.
Video previews are reused from the existing verified preview_service cache.
"""
from __future__ import annotations

import hashlib
import os
import re
import tempfile
import threading
from pathlib import Path

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QImage, QImageReader

from .paths import cache_dir
from .preview_service import build_preview
from .probe import IMAGE_EXTENSIONS

_THUMB_NAME = re.compile(r"^[a-f0-9]{32}\.png$")
MAX_CACHE_ITEMS = 3_000
MAX_CACHE_BYTES = 512 * 1024 * 1024
THUMB_SIZE = QSize(144, 96)
_SAVE_LOCK = threading.Lock()
_SAVES_SINCE_PRUNE = 0


def thumbnail_directory() -> Path:
    folder = cache_dir() / "qt-thumbnails"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def thumbnail_path(source: Path) -> Path:
    metadata = source.stat()
    key = f"{source.absolute()}:{metadata.st_size}:{metadata.st_mtime_ns}:qt-thumb-v1"
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:32]
    return thumbnail_directory() / f"{digest}.png"


def _read_small(path: Path) -> QImage:
    reader = QImageReader(str(path))
    reader.setAutoTransform(True)
    size = reader.size()
    if size.isValid():
        reader.setScaledSize(size.scaled(THUMB_SIZE, Qt.AspectRatioMode.KeepAspectRatio))
    return reader.read()


def load_thumbnail(source: Path) -> QImage:
    """Return an already stored image thumbnail or generate one without UI calls."""
    source = Path(source)
    if source.suffix.lower() not in IMAGE_EXTENSIONS:
        # The existing preview service caches the FFmpeg video frame on disk.
        preview = build_preview(source, width=320)
        return _read_small(preview)

    target = thumbnail_path(source)
    if target.is_file():
        image = _read_small(target)
        if not image.isNull():
            try:
                os.utime(target, None)
            except OSError:
                pass
            return image
        try:
            target.unlink()
        except OSError:
            pass

    image = _read_small(source)
    if image.isNull():
        return image
    temp_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=target.parent, prefix=".thumb-", suffix=".png", delete=False
        ) as output:
            temp_name = output.name
        os.chmod(temp_name, 0o600)
        if image.save(temp_name, "PNG"):
            os.replace(temp_name, target)
            _occasionally_prune()
    except OSError:
        # A read-only cache must never block importing the original image.
        pass
    finally:
        if temp_name is not None:
            try:
                Path(temp_name).unlink(missing_ok=True)
            except OSError:
                pass
    return image


def prune_thumbnails(
    *, directory: Path | None = None, max_items: int = MAX_CACHE_ITEMS,
    max_bytes: int = MAX_CACHE_BYTES,
) -> int:
    """Only delete owned hashed thumbnail files, never foreign files."""
    folder = Path(directory) if directory is not None else thumbnail_directory()
    if not folder.exists():
        return 0
    entries = []
    try:
        for path in folder.iterdir():
            if not _THUMB_NAME.fullmatch(path.name) or path.is_symlink():
                continue
            try:
                stat = path.stat()
                if path.is_file():
                    entries.append((stat.st_atime_ns, stat.st_size, path))
            except OSError:
                continue
    except OSError:
        return 0
    current_size = sum(size for _, size, _ in entries)
    removed = 0
    for _, size, path in sorted(entries):
        if len(entries) - removed <= max_items and current_size <= max_bytes:
            break
        try:
            path.unlink()
        except OSError:
            continue
        removed += 1
        current_size -= size
    return removed


def _occasionally_prune() -> None:
    """Amortize cache maintenance; do not scan thousands of entries per image."""
    global _SAVES_SINCE_PRUNE
    with _SAVE_LOCK:
        _SAVES_SINCE_PRUNE += 1
        due = _SAVES_SINCE_PRUNE >= 32
        if due:
            _SAVES_SINCE_PRUNE = 0
    if due:
        prune_thumbnails()
