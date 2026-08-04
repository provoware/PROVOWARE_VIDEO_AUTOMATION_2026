from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable

from .incremental_directory import DirectoryRecord


def safe_media_directory(path: Path) -> Path:
    candidate = Path(path).expanduser()
    try:
        if candidate.is_dir() and os.access(candidate, os.R_OK | os.X_OK):
            return candidate
    except OSError:
        pass
    downloads = Path.home() / "Downloads"
    try:
        if downloads.is_dir() and os.access(downloads, os.R_OK | os.X_OK):
            return downloads
    except OSError:
        pass
    return Path.home()


def sort_directory_records(
    records: Iterable[DirectoryRecord],
    sort_key: str,
    reverse: bool,
) -> list[DirectoryRecord]:
    def key(record: DirectoryRecord):
        directory = 0 if record.is_dir else 1
        if sort_key == "size":
            value = record.size
        elif sort_key == "modified":
            value = record.modified
        elif sort_key == "kind":
            value = "Ordner" if record.is_dir else record.path.suffix.lower()
        else:
            value = record.path.name.casefold()
        return directory, value, record.path.name.casefold()

    result = sorted(records, key=key, reverse=reverse)
    if reverse:
        result.sort(key=lambda item: not item.is_dir)
    return result


def human_size(value: int) -> str:
    number = float(value)
    for unit in ("B", "KB", "MB", "GB"):
        if number < 1024 or unit == "GB":
            return f"{number:.1f} {unit}"
        number /= 1024
    return f"{value} B"
