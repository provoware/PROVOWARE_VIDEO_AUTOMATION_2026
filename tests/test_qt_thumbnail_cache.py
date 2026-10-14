"""Persistent Qt image miniatures are safe, reusable and bounded."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QImage

from videobatch_fast.qt_thumbnail_cache import (
    load_thumbnail, prune_thumbnails, thumbnail_path,
)


def test_persistent_thumbnail_roundtrip_and_source_untouched(tmp_path, monkeypatch):
    folder = tmp_path / "thumbs"
    folder.mkdir()
    monkeypatch.setattr(
        "videobatch_fast.qt_thumbnail_cache.thumbnail_directory",
        lambda: folder,
    )
    source = tmp_path / "sample.png"
    image = QImage(640, 480, QImage.Format.Format_RGB32)
    image.fill(0xff336699)
    assert image.save(str(source), "PNG")
    before = source.read_bytes()
    first = load_thumbnail(source)
    assert not first.isNull()
    assert first.width() <= 144 and first.height() <= 96
    cached = thumbnail_path(source)
    assert cached.is_file()
    assert not load_thumbnail(source).isNull()
    assert source.read_bytes() == before

    source.write_bytes(b"changed-invalid")
    assert thumbnail_path(source) != cached
    assert load_thumbnail(source).isNull()
    assert source.read_bytes() == b"changed-invalid"


def test_prune_ignores_foreign_files(tmp_path):
    folder = tmp_path / "thumbs"
    folder.mkdir()
    good = folder / ("a" * 32 + ".png")
    foreign = folder / "family-photo.png"
    good.write_bytes(b"cache")
    foreign.write_bytes(b"original")
    removed = prune_thumbnails(directory=folder, max_items=0, max_bytes=0)
    assert removed == 1
    assert not good.exists()
    assert foreign.read_bytes() == b"original"
