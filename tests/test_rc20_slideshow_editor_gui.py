from __future__ import annotations

import os
from pathlib import Path
from types import SimpleNamespace

import pytest
from PIL import Image

from videobatch_fast.audio_waveform import SceneMarker, WaveformAnalysis


pytestmark = pytest.mark.skipif(not os.environ.get("DISPLAY"), reason="GUI display required")


def test_thumbnail_strip_drag_selection_and_anchors(tmp_path: Path) -> None:
    from tkinter import Tk
    from videobatch_fast.slideshow_editor import ThumbnailOrderStrip

    root = Tk()
    root.geometry("700x240")
    moves: list[tuple[int, int]] = []
    selections: list[Path | None] = []
    try:
        strip = ThumbnailOrderStrip(root, on_move=lambda source, target: moves.append((source, target)), on_select=selections.append)
        strip.pack(fill="both", expand=True)
        strip.set_items([])
        paths = []
        for index, color in enumerate(("red", "green", "blue")):
            path = tmp_path / f"image-{index}.png"
            Image.new("RGB", (200, 120), color).save(path)
            paths.append(path)
        strip.set_items(paths, start=paths[0], end=paths[-1])
        root.update_idletasks()
        strip._press(SimpleNamespace(x=180, y=30))
        assert strip.selected_path == paths[1]
        assert selections[-1] == paths[1]
        strip._motion(SimpleNamespace(x=330, y=30))
        strip._release(SimpleNamespace(x=330, y=30))
        assert moves == [(1, 2)]
        assert strip._horizontal_wheel(SimpleNamespace(delta=120)) == "break"
        strip._press(SimpleNamespace(x=9999, y=10))
        assert strip.selected_path is None
        strip.set_items([tmp_path / "missing.png"])
        root.update_idletasks()
    finally:
        root.destroy()


def test_waveform_scene_view_draws_markers() -> None:
    from tkinter import Tk
    from videobatch_fast.slideshow_editor import WaveformSceneView

    root = Tk()
    root.geometry("800x320")
    try:
        view = WaveformSceneView(root)
        view.pack(fill="both", expand=True)
        view.set_analysis(None)
        analysis = WaveformAnalysis(
            path=Path("audio.wav"),
            duration=60.0,
            peaks=tuple((index % 10) / 10 for index in range(100)),
            markers=(
                SceneMarker("Intro", 0.0, "intro"),
                SceneMarker("Beat", 10.0, "beat"),
                SceneMarker("Ruhe", 25.0, "quiet"),
                SceneMarker("Drop", 40.0, "drop"),
                SceneMarker("Outro", 55.0, "outro"),
            ),
            sample_rate=1000,
        )
        view.set_analysis(analysis)
        root.update_idletasks()
        view.redraw()
        assert len(view.canvas.find_all()) >= 10
    finally:
        root.destroy()
