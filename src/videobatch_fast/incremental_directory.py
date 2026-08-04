from __future__ import annotations

from dataclasses import dataclass
import os
import threading
import time
from pathlib import Path
from typing import Iterator


@dataclass(frozen=True)
class DirectoryRecord:
    path: Path
    is_dir: bool
    size: int
    modified: float


def scan_directory_batches(
    directory: Path,
    allowed_suffixes: set[str] | frozenset[str],
    *,
    cancel: threading.Event | None = None,
    pause: threading.Event | None = None,
    batch_size: int = 128,
) -> Iterator[list[DirectoryRecord]]:
    """Yield safe directory entries in small batches so the UI stays responsive."""
    if batch_size < 1:
        raise ValueError("batch_size must be positive")
    allowed = {item.lower() for item in allowed_suffixes}
    batch: list[DirectoryRecord] = []
    with os.scandir(directory) as iterator:
        for item in iterator:
            if cancel is not None and cancel.is_set():
                break
            while pause is not None and pause.is_set():
                if cancel is not None and cancel.is_set():
                    break
                time.sleep(0.01)
            if cancel is not None and cancel.is_set():
                break
            try:
                if item.is_symlink():
                    continue
                is_dir = item.is_dir(follow_symlinks=False)
                if not is_dir and (not item.is_file(follow_symlinks=False) or Path(item.name).suffix.lower() not in allowed):
                    continue
                stat = item.stat(follow_symlinks=False)
            except OSError:
                continue
            batch.append(DirectoryRecord(Path(item.path), is_dir, 0 if is_dir else int(stat.st_size), float(stat.st_mtime)))
            if len(batch) >= batch_size:
                yield batch
                batch = []
    if batch:
        yield batch
