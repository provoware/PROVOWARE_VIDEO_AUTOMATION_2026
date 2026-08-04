from __future__ import annotations

import os
from pathlib import Path
from unittest import mock

from videobatch_fast.preview_service import preview_cache_path, prune_preview_cache


def _write(path: Path, size: int, atime_ns: int) -> None:
    path.write_bytes(b"x" * size)
    os.utime(path, ns=(atime_ns, atime_ns))


def test_preview_cache_key_changes_with_source_content_metadata(tmp_path: Path) -> None:
    source = tmp_path / "image.jpg"
    source.write_bytes(b"first")
    with mock.patch("videobatch_fast.preview_service.preview_cache_directory", return_value=tmp_path / "cache"):
        first = preview_cache_path(source, 320)
        source.write_bytes(b"second-version")
        second = preview_cache_path(source, 320)
        third = preview_cache_path(source, 640)
    assert first != second
    assert second != third


def test_prune_preview_cache_respects_file_limit_and_lru_order(tmp_path: Path) -> None:
    cache = tmp_path / "previews"
    cache.mkdir()
    oldest = cache / "oldest.png"
    middle = cache / "middle.png"
    newest = cache / "newest.png"
    _write(oldest, 120, 1)
    _write(middle, 120, 2)
    _write(newest, 120, 3)

    result = prune_preview_cache(directory=cache, max_bytes=10_000, max_files=2)

    assert result["removed_files"] == 1
    assert not oldest.exists()
    assert middle.exists() and newest.exists()
    assert result["after_files"] == 2


def test_prune_preview_cache_respects_byte_limit_and_protected_file(tmp_path: Path) -> None:
    cache = tmp_path / "previews"
    cache.mkdir()
    protected = cache / "protected.png"
    removable = cache / "removable.png"
    _write(protected, 180, 1)
    _write(removable, 180, 2)

    result = prune_preview_cache(
        directory=cache,
        max_bytes=200,
        max_files=10,
        protected=protected,
    )

    assert protected.exists()
    assert not removable.exists()
    assert result["after_bytes"] == 180


def test_prune_preview_cache_ignores_non_png_and_unreadable_entries(tmp_path: Path) -> None:
    cache = tmp_path / "previews"
    cache.mkdir()
    note = cache / "keep.txt"
    note.write_text("not a thumbnail", encoding="utf-8")
    _write(cache / "preview.png", 120, 1)

    result = prune_preview_cache(directory=cache, max_bytes=0, max_files=0)

    assert note.exists()
    assert result["removed_files"] == 1
    assert result["after_files"] == 0
