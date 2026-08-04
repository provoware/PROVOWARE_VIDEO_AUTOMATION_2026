from __future__ import annotations

import threading
import time
from pathlib import Path
from types import SimpleNamespace

import pytest
from PIL import Image

from videobatch_fast.preview_service import PreviewError, load_preview_bitmap
from videobatch_fast.selection_preview_controller import (
    SelectionPreviewController,
    resolve_tree_selection,
)


class FakeTree:
    def __init__(self, selected: tuple[str, ...], focus: str) -> None:
        self._selected = selected
        self._focus = focus

    def selection(self) -> tuple[str, ...]:
        return self._selected

    def focus(self) -> str:
        return self._focus


def test_resolve_tree_selection_prefers_clicked_focus() -> None:
    mapping = {
        "media:0": Path("/tmp/first.png"),
        "media:1": Path("/tmp/second.png"),
        "media:2": Path("/tmp/third.png"),
    }
    tree = FakeTree(("media:0", "media:1", "media:2"), "media:1")
    assert resolve_tree_selection(tree, mapping) == mapping["media:1"]

    fallback = FakeTree(("media:0", "media:2"), "")
    assert resolve_tree_selection(fallback, mapping) == mapping["media:2"]
    assert resolve_tree_selection(FakeTree((), ""), mapping) is None


def test_selection_preview_controller_serializes_and_coalesces(tmp_path: Path) -> None:
    paths = [tmp_path / f"image-{index}.png" for index in range(8)]
    for path in paths:
        Image.new("RGB", (48, 32), (20, 60, 120)).save(path)

    events: list[tuple[str, dict]] = []
    active = 0
    maximum_active = 0
    lock = threading.Lock()
    first_started = threading.Event()
    release_first = threading.Event()

    def builder(path: Path, _width: int) -> Path:
        nonlocal active, maximum_active
        with lock:
            active += 1
            maximum_active = max(maximum_active, active)
        try:
            if path == paths[0]:
                first_started.set()
                assert release_first.wait(timeout=3)
            time.sleep(0.01)
            return path
        finally:
            with lock:
                active -= 1

    def prober(path: Path):
        return SimpleNamespace(
            path=path,
            kind="image",
            duration=None,
            codec="png",
            width=48,
            height=32,
            size_bytes=path.stat().st_size,
        )

    controller = SelectionPreviewController(
        events.append,
        preview_builder=builder,
        media_prober=prober,
    )
    controller.request(paths[0], 800, include_image=True)
    assert first_started.wait(timeout=2)
    for path in paths[1:]:
        controller.request(path, 800, include_image=True)
    release_first.set()

    deadline = time.monotonic() + 4
    while not events and time.monotonic() < deadline:
        time.sleep(0.01)

    assert events
    assert events[-1][0] == "selection_preview_ready"
    assert events[-1][1]["path"] == paths[-1]
    assert all(payload["path"] != paths[0] for _, payload in events)
    assert maximum_active == 1
    assert controller.shutdown()


def test_selection_preview_controller_drops_stale_failure(tmp_path: Path) -> None:
    broken = tmp_path / "broken.png"
    valid = tmp_path / "valid.png"
    broken.write_bytes(b"broken")
    Image.new("RGB", (20, 20), "white").save(valid)
    events: list[tuple[str, dict]] = []
    started = threading.Event()
    release = threading.Event()

    def builder(path: Path, _width: int) -> Path:
        if path == broken:
            started.set()
            assert release.wait(timeout=3)
            raise RuntimeError("old failure")
        return path

    controller = SelectionPreviewController(
        events.append,
        preview_builder=builder,
        media_prober=lambda path: SimpleNamespace(
            path=path,
            kind="image",
            duration=None,
            codec="png",
            width=20,
            height=20,
            size_bytes=path.stat().st_size,
        ),
    )
    controller.request(broken, 600, include_image=True)
    assert started.wait(timeout=2)
    controller.request(valid, 600, include_image=True)
    release.set()

    deadline = time.monotonic() + 3
    while not events and time.monotonic() < deadline:
        time.sleep(0.01)

    assert [name for name, _ in events] == ["selection_preview_ready"]
    assert events[0][1]["path"] == valid
    assert controller.shutdown()


def test_load_preview_bitmap_rejects_broken_and_huge_inputs(tmp_path: Path) -> None:
    valid = tmp_path / "valid.png"
    Image.new("RGB", (640, 360), "white").save(valid)
    image = load_preview_bitmap(valid, max_width=320, max_height=240)
    assert image.width <= 320
    assert image.height <= 240

    broken = tmp_path / "broken.png"
    broken.write_bytes(b"not-a-png")
    with pytest.raises(PreviewError):
        load_preview_bitmap(broken, max_width=320, max_height=240)


def test_main_selected_media_list_rapid_clicks_remain_stable(
    tmp_path: Path,
    monkeypatch,
) -> None:
    from tkinter import Tk

    import videobatch_fast.config as config_module
    from videobatch_fast.ui import VideoBatchFastUI

    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    project_file = tmp_path / "state" / "VideoBatchFast" / "projects" / "current.vbfast.json"
    monkeypatch.setitem(config_module.DEFAULT_CONFIG, "current_project_file", str(project_file))
    monkeypatch.setitem(config_module.DEFAULT_CONFIG, "output_dir", str(home / "Videos" / "VideoBatchFast"))
    monkeypatch.setitem(config_module.DEFAULT_CONFIG, "last_audio_dir", str(home / "Downloads"))
    monkeypatch.setitem(config_module.DEFAULT_CONFIG, "last_media_dir", str(home / "Downloads"))

    images: list[Path] = []
    for index in range(6):
        path = tmp_path / f"selected-{index}.png"
        Image.new("RGB", (320 + index, 180), (30 * index, 70, 150)).save(path)
        images.append(path)

    root = Tk()
    root.geometry("1280x820+0+0")
    app = VideoBatchFastUI(root)
    app._append_paths(images, audio=False)
    root.update_idletasks()

    children = app.media_tree.get_children()
    assert len(children) == len(images)
    for index in range(120):
        chosen = children[index % len(children)]
        app.media_tree.selection_set(chosen)
        app.media_tree.focus(chosen)
        app.media_tree.event_generate("<<TreeviewSelect>>")
        root.update()
        time.sleep(0.002)

    deadline = time.monotonic() + 6
    while time.monotonic() < deadline:
        root.update()
        if (
            app.preview_status.get() == "Vorschau bereit"
            and app.events.qsize() == 0
        ):
            break
        time.sleep(0.01)

    assert app.preview_source == images[-1]
    assert app.preview_status.get() == "Vorschau bereit"
    assert app.preview_photo is not None

    app._cancel_pending_selection_preview()
    assert app.selection_previews.shutdown(timeout=3)
    app.tasks.shutdown(timeout=3)
    root.destroy()


def test_architecture_audit_creates_missing_diagnostics_parents(tmp_path: Path) -> None:
    import os
    import subprocess
    import sys

    project_root = Path(__file__).resolve().parents[1]
    diagnostics = tmp_path / "missing" / "nested" / "diagnostics"
    env = {
        **os.environ,
        "PYTHONPATH": str(project_root / "src"),
        "VIDEOBATCH_DIAGNOSTICS_DIR": str(diagnostics),
    }
    completed = subprocess.run(
        [sys.executable, str(project_root / "scripts" / "architecture_audit.py")],
        cwd=project_root,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
        timeout=60,
    )
    assert completed.returncode == 0, completed.stdout
    assert (diagnostics / "architecture_audit_latest.json").is_file()
