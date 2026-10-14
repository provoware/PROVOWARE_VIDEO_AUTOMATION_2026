"""Media-index safety and incremental-refresh contracts (no media decoding)."""
from __future__ import annotations

import os
import sqlite3

import pytest
import threading
from pathlib import Path

from videobatch_fast.media_index import MediaIndex, media_roots


def _index(tmp_path: Path) -> tuple[MediaIndex, dict[str, Path]]:
    roots = {name: tmp_path / name for name in ("videos", "downloads", "pictures")}
    for root in roots.values():
        root.mkdir()
    return MediaIndex(database=tmp_path / "cache" / "media.sqlite3", roots=roots), roots


def test_only_supported_media_and_no_project_folders(tmp_path: Path) -> None:
    index, roots = _index(tmp_path)
    downloads = roots["downloads"]
    (downloads / "song.MP3").write_bytes(b"audio")
    (downloads / "frame.avif").write_bytes(b"image")
    (downloads / "film.mkv").write_bytes(b"video")
    (downloads / "main.py").write_bytes(b"code")
    (downloads / "README.md").write_bytes(b"text")
    (downloads / "pack.zip").write_bytes(b"archive")
    (downloads / ".venv").mkdir()
    (downloads / ".venv" / "hidden.png").write_bytes(b"x")
    (downloads / "node_modules").mkdir()
    (downloads / "node_modules" / "hidden.wav").write_bytes(b"x")
    (downloads / "deep").mkdir()
    (downloads / "deep" / "cover.jpg").write_bytes(b"x")
    result = index.refresh_root("downloads")
    assert result.complete and result.added == 4
    assert {item.path.name for item in index.cached_directory(downloads)} == {
        "song.MP3", "frame.avif", "film.mkv",
    }
    assert [item.path.name for item in index.cached_directory(downloads / "deep")] == ["cover.jpg"]


def test_second_scan_does_not_reindex_unchanged_sources(tmp_path: Path) -> None:
    index, roots = _index(tmp_path)
    picture = roots["pictures"] / "a.png"
    picture.write_bytes(b"v1")
    assert index.refresh_root("pictures").added == 1
    cached_before = index.cached_directory(roots["pictures"])
    assert cached_before[0].last_known
    unchanged = index.refresh_root("pictures")
    assert unchanged.unchanged == 1
    assert unchanged.changed == unchanged.added == unchanged.removed == 0
    picture.write_bytes(b"changed bytes")
    changed = index.refresh_root("pictures")
    assert changed.changed == 1
    picture.unlink()
    removed = index.refresh_root("pictures")
    assert removed.removed == 1
    assert index.cached_directory(roots["pictures"]) == []


def test_missing_root_and_cancelled_scan_preserve_cache(tmp_path: Path) -> None:
    index, roots = _index(tmp_path)
    picture = roots["videos"] / "video.mp4"
    picture.write_bytes(b"video")
    assert index.refresh_root("videos").added == 1
    picture.unlink()
    cancelled = threading.Event()
    cancelled.set()
    result = index.refresh_root("videos", cancel=cancelled)
    assert not result.complete and result.removed == 0
    assert len(index.cached_directory(roots["videos"])) == 1
    roots["videos"].rmdir()
    result = index.refresh_root("videos")
    assert not result.complete
    assert len(index.cached_directory(roots["videos"])) == 1


def test_symlink_tree_and_extra_root_are_not_followed(tmp_path: Path) -> None:
    index, roots = _index(tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "private.jpg").write_bytes(b"x")
    (roots["downloads"] / "follow_me").symlink_to(outside, target_is_directory=True)
    assert index.refresh_root("downloads").complete
    assert index.cached_directory(outside) == []
    assert index.cached_directory(roots["downloads"] / "follow_me") == []


def test_xdg_user_directories_are_resolved_without_executing_shell(
    tmp_path: Path, monkeypatch,
) -> None:
    config = tmp_path / ".config"
    config.mkdir()
    (config / "user-dirs.dirs").write_text(
        'XDG_DOWNLOAD_DIR="$HOME/Eingang"\n'
        'XDG_PICTURES_DIR="$HOME/Bilder"\n'
        'XDG_VIDEOS_DIR="$HOME/Filme"\n',
        encoding="utf-8",
    )
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(config))
    result = media_roots()
    assert set(result) == {"videos", "downloads", "pictures"}
    assert result["downloads"] == tmp_path / "Eingang"
    assert result["videos"] == tmp_path / "Filme"
    assert result["pictures"] == tmp_path / "Bilder"


def test_corrupt_database_rebuilds_without_touching_original_media(tmp_path: Path) -> None:
    index, roots = _index(tmp_path)
    source = roots["pictures"] / "family.jpg"
    source.write_bytes(b"precious-data")
    index.database.parent.mkdir(parents=True, exist_ok=True)
    index.database.write_bytes(b"not a SQLite database")
    result = index.refresh_root("pictures")
    assert result.complete and result.added == 1
    assert source.read_bytes() == b"precious-data"
    backups = list(index.database.parent.glob("media.sqlite3.corrupt-*"))
    assert len(backups) == 1
    assert backups[0].read_bytes() == b"not a SQLite database"
    assert index.cached_directory(roots["pictures"])[0].path == source


def test_explicit_exclusion_directory(tmp_path: Path) -> None:
    _, roots = _index(tmp_path)
    project = roots["downloads"] / "Coden"
    project.mkdir()
    (project / "ignored.png").write_bytes(b"image")
    index = MediaIndex(database=tmp_path / "new.sqlite3",
                       roots=roots, excluded_paths=frozenset({project}))
    assert index.refresh_root("downloads").added == 0
    assert index.cached_directory(project) == []


def test_xdg_home_does_not_trigger_full_home_scan(tmp_path: Path, monkeypatch) -> None:
    config = tmp_path / ".config"
    config.mkdir()
    (config / "user-dirs.dirs").write_text(
        'XDG_DOWNLOAD_DIR="$HOME"\n'
        'XDG_PICTURES_DIR="/"\n'
        'XDG_VIDEOS_DIR="$HOME/Videos"\n', encoding="utf-8"
    )
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(config))
    roots = media_roots()
    assert roots["downloads"] == tmp_path / "Downloads"
    assert roots["pictures"] != Path("/")
    assert tmp_path not in roots.values()


def test_incomplete_tree_scan_rolls_back_updated_and_new_rows(tmp_path: Path, monkeypatch) -> None:
    """An unreadable subdirectory must not publish a partial index."""
    index, roots = _index(tmp_path)
    root = roots["downloads"]
    prior = root / "original.png"
    prior.write_bytes(b"old")
    subdir = root / "project"
    subdir.mkdir()
    (subdir / "also-old.jpg").write_bytes(b"old")
    assert index.refresh_root("downloads").complete
    before = index.cached_directory(root)
    assert len(before) == 1

    prior.write_bytes(b"changed file with bigger size")
    (root / "new.mp3").write_bytes(b"new audio")
    original_scandir = os.scandir

    def inaccessible(path):
        if Path(path) == subdir:
            raise PermissionError("simulated unreadable directory")
        return original_scandir(path)

    monkeypatch.setattr("videobatch_fast.media_index.os.scandir", inaccessible)
    result = index.refresh_root("downloads")
    assert not result.complete and result.added == result.changed == result.removed == 0
    after = index.cached_directory(root)
    assert after == before
    assert index.cached_directory(subdir)[0].path.name == "also-old.jpg"


def test_index_large_directory_keeps_only_media(tmp_path: Path) -> None:
    index, roots = _index(tmp_path)
    root = roots["downloads"]
    for number in range(1_000):
        suffix = ".png" if number % 4 == 0 else ".py"
        (root / f"entry-{number:04}{suffix}").write_bytes(b"x")
    first = index.refresh_root("downloads")
    assert first.complete and first.added == 250
    second = index.refresh_root("downloads")
    assert second.complete and second.unchanged == 250
    assert (second.added, second.changed, second.removed) == (0, 0, 0)


@pytest.mark.parametrize(
    "error", [
        sqlite3.OperationalError("database is locked"),
        sqlite3.OperationalError("attempt to write a readonly database"),
        sqlite3.OperationalError("database or disk is full"),
    ],
)
def test_noncorruption_database_errors_never_move_existing_index(
    tmp_path: Path, monkeypatch, error: Exception,
) -> None:
    index, roots = _index(tmp_path)
    media = roots["pictures"] / "original.png"
    media.write_bytes(b"original")
    assert index.refresh_root("pictures").complete
    previous = index.database.read_bytes()
    def denied():
        raise error
    monkeypatch.setattr(index, "_open_schema", denied)
    with pytest.raises(sqlite3.DatabaseError):
        index.refresh_root("pictures")
    assert index.database.read_bytes() == previous
    assert list(index.database.parent.glob("*.corrupt-*")) == []
    assert media.read_bytes() == b"original"


def test_cached_directory_read_does_not_initialize_index(tmp_path: Path) -> None:
    index, roots = _index(tmp_path)
    assert index.cached_directory(roots["pictures"]) == []
    assert not index.database.exists()
