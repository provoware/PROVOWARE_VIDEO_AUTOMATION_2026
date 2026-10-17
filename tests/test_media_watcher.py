"""Real Linux inotify checks: only media changes under the configured roots."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

from videobatch_fast.media_watcher import MediaWatcher


@pytest.mark.skipif(not sys.platform.startswith("linux"), reason="Linux only")
def test_watcher_ignores_programming_files_but_not_media(tmp_path: Path) -> None:
    roots = {name: tmp_path / name for name in ("videos", "downloads", "pictures")}
    for root in roots.values():
        root.mkdir()
    with MediaWatcher(roots) as watcher:
        assert not watcher.coverage_limited
        (roots["downloads"] / "script.py").write_bytes(b"code")
        assert watcher.changed(timeout=0.3) == set()
        (roots["downloads"] / "song.mp3").write_bytes(b"sound")
        assert "downloads" in watcher.changed(timeout=1.0)


@pytest.mark.skipif(not sys.platform.startswith("linux"), reason="Linux only")
def test_watcher_adds_new_subdirectory_after_refresh(tmp_path: Path) -> None:
    roots = {name: tmp_path / name for name in ("videos", "downloads", "pictures")}
    for root in roots.values():
        root.mkdir()
    with MediaWatcher(roots) as watcher:
        nested = roots["pictures"] / "new"
        nested.mkdir()
        assert "pictures" in watcher.changed(timeout=1.0)
        assert watcher.topology_changed
        watcher.reset()
        (nested / "photo.png").write_bytes(b"image")
        assert "pictures" in watcher.changed(timeout=1.0)


@pytest.mark.skipif(not sys.platform.startswith("linux"), reason="Linux only")
def test_watcher_excludes_code_project_and_respects_capacity(tmp_path: Path) -> None:
    roots = {name: tmp_path / name for name in ("videos", "downloads", "pictures")}
    for root in roots.values():
        root.mkdir()
    project = roots["downloads"] / "Coding"
    project.mkdir()
    with MediaWatcher(roots, excluded_paths=frozenset({project})) as watcher:
        assert not watcher.coverage_limited
        (project / "image.png").write_bytes(b"x")
        assert watcher.changed(timeout=0.3) == set()
    with MediaWatcher(roots, max_watches=1) as watcher:
        assert watcher.coverage_limited
