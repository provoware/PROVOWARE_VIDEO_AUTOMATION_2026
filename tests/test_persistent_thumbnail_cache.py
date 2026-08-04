from __future__ import annotations

import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from videobatch_fast.preview_service import (
    PREVIEW_CACHE_MAX_BYTES,
    build_preview,
    clear_preview_cache,
    preview_cache_path,
    preview_cache_status,
    prune_preview_cache,
)

ROOT = Path(__file__).resolve().parents[1]


def _managed_name(index: int) -> str:
    return f"{index:024x}.png"


def _write(path: Path, size: int, atime_ns: int) -> None:
    path.write_bytes(b"x" * size)
    os.utime(path, ns=(atime_ns, atime_ns))


def test_preview_cache_key_changes_with_source_content_metadata(tmp_path: Path) -> None:
    source = tmp_path / "image.jpg"
    source.write_bytes(b"first")
    with mock.patch(
        "videobatch_fast.preview_service.preview_cache_directory",
        return_value=tmp_path / "cache",
    ):
        first = preview_cache_path(source, 320)
        source.write_bytes(b"second-version")
        second = preview_cache_path(source, 320)
        third = preview_cache_path(source, 640)
    assert first != second
    assert second != third


def test_prune_preview_cache_respects_file_limit_and_lru_order(tmp_path: Path) -> None:
    cache = tmp_path / "previews"
    cache.mkdir()
    oldest = cache / _managed_name(1)
    middle = cache / _managed_name(2)
    newest = cache / _managed_name(3)
    _write(oldest, 120, 1)
    _write(middle, 120, 2)
    _write(newest, 120, 3)

    result = prune_preview_cache(directory=cache, max_bytes=10_000, max_files=2)

    assert result["removed_files"] == 1
    assert not oldest.exists()
    assert middle.exists() and newest.exists()
    assert result["after_files"] == 2
    assert result["last_prune_at"]


def test_prune_preview_cache_respects_byte_limit_and_protected_file(tmp_path: Path) -> None:
    cache = tmp_path / "previews"
    cache.mkdir()
    protected = cache / _managed_name(10)
    removable = cache / _managed_name(11)
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


def test_prune_preview_cache_ignores_foreign_png_and_non_png(tmp_path: Path) -> None:
    cache = tmp_path / "previews"
    cache.mkdir()
    note = cache / "keep.txt"
    foreign_png = cache / "foreign-preview.png"
    managed = cache / _managed_name(20)
    note.write_text("not a thumbnail", encoding="utf-8")
    _write(foreign_png, 140, 1)
    _write(managed, 120, 2)

    result = prune_preview_cache(directory=cache, max_bytes=0, max_files=0)

    assert note.exists()
    assert foreign_png.exists()
    assert not managed.exists()
    assert result["removed_files"] == 1
    assert result["after_files"] == 0


def test_preview_cache_status_uses_one_gibibyte_default_and_managed_files_only(
    tmp_path: Path,
) -> None:
    cache = tmp_path / "previews"
    cache.mkdir()
    _write(cache / _managed_name(30), 256, 1)
    _write(cache / "foreign.png", 512, 2)
    prune_preview_cache(directory=cache)

    status = preview_cache_status(directory=cache)

    assert PREVIEW_CACHE_MAX_BYTES == 1024 * 1024 * 1024
    assert status["max_bytes"] == PREVIEW_CACHE_MAX_BYTES
    assert status["files"] == 1
    assert status["bytes"] == 256
    assert status["last_prune_at"]
    assert status["directory"] == str(cache)


def test_clear_preview_cache_removes_only_managed_files_and_stale_partials(
    tmp_path: Path,
) -> None:
    cache = tmp_path / "previews"
    cache.mkdir()
    managed = cache / _managed_name(40)
    foreign_png = cache / "family-photo.png"
    note = cache / "notes.txt"
    stale_partial = cache / f".{managed.stem}.png.123.partial"
    _write(managed, 300, 1)
    _write(foreign_png, 400, 2)
    note.write_text("keep", encoding="utf-8")
    stale_partial.write_bytes(b"partial")
    old = time.time() - 500
    os.utime(stale_partial, (old, old))

    result = clear_preview_cache(directory=cache)

    assert result["removed_files"] == 1
    assert result["removed_bytes"] == 300
    assert result["removed_partials"] == 1
    assert not managed.exists()
    assert not stale_partial.exists()
    assert foreign_png.exists()
    assert note.exists()


def test_same_cache_key_starts_ffmpeg_only_once_for_parallel_requests(
    tmp_path: Path,
) -> None:
    cache = tmp_path / "previews"
    cache.mkdir()
    source = tmp_path / "source.jpg"
    source.write_bytes(b"source")
    run_count = 0
    count_lock = threading.Lock()

    def fake_run(command, **_kwargs):
        nonlocal run_count
        with count_lock:
            run_count += 1
        time.sleep(0.15)
        Path(command[-1]).write_bytes(b"x" * 256)
        return SimpleNamespace(returncode=0, stderr="")

    with (
        mock.patch(
            "videobatch_fast.preview_service.preview_cache_directory",
            return_value=cache,
        ),
        mock.patch("videobatch_fast.preview_service.ffmpeg_path", return_value="ffmpeg"),
        mock.patch(
            "videobatch_fast.preview_service.probe_media",
            return_value=SimpleNamespace(kind="image"),
        ),
        mock.patch("videobatch_fast.preview_service.subprocess.run", side_effect=fake_run),
    ):
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = tuple(executor.map(lambda _index: build_preview(source, 320), range(2)))

    assert results[0] == results[1]
    assert results[0].is_file()
    assert run_count == 1


def test_media_dialog_exposes_cache_diagnostics_without_audio_clutter() -> None:
    layout = (ROOT / "src/videobatch_fast/media_dialog_layout.py").read_text(
        encoding="utf-8"
    )

    assert 'text="Vorschau-Cache"' in layout
    assert "if not dialog.audio" in layout
    assert 'text="Status aktualisieren"' in layout
    assert 'text="Vorschau-Cache leeren"' in layout
    assert "Originalmedien" in layout
