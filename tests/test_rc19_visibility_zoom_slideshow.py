from __future__ import annotations

import json
import shutil
import subprocess
import wave
from pathlib import Path
from unittest import mock

import pytest
from PIL import Image

from videobatch_fast.command_builder import build_command
from videobatch_fast.config import normalize_config
from videobatch_fast.jobs import build_jobs
from videobatch_fast.models import BatchOptions, MediaInfo
from videobatch_fast.slideshow import (
    SLIDESHOW_MODE_ALL_IMAGES,
    build_slideshow_plan,
    slideshow_summary,
)

ROOT = Path(__file__).resolve().parents[1]


def _luminance(hex_color: str) -> float:
    value = hex_color.lstrip("#")
    channels = [int(value[index:index + 2], 16) / 255 for index in (0, 2, 4)]
    linear = [channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4 for channel in channels]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def _contrast(first: str, second: str) -> float:
    high, low = sorted((_luminance(first), _luminance(second)), reverse=True)
    return (high + 0.05) / (low + 0.05)


def test_high_visibility_palette_meets_enhanced_contrast() -> None:
    colors = json.loads((ROOT / "resources/themes/dark.json").read_text(encoding="utf-8"))["colors"]
    assert _contrast(colors["text_primary"], colors["background_main"]) >= 7.0
    assert _contrast(colors["text_secondary"], colors["background_surface"]) >= 7.0
    assert _contrast(colors["text_muted"], colors["background_surface"]) >= 7.0
    assert _contrast(colors["action_primary"], colors["action_primary_text"]) >= 7.0
    assert _contrast(colors["text_primary"], colors["state_selected"]) >= 7.0


def test_config_normalizes_slideshow_choices() -> None:
    config = normalize_config({"assignment_mode": "bad", "slideshow_transition": "bad"})
    assert config["assignment_mode"] == "pairwise"
    assert config["slideshow_transition"] == "auto"
    valid = normalize_config({"assignment_mode": SLIDESHOW_MODE_ALL_IMAGES, "slideshow_transition": "soft"})
    assert valid["assignment_mode"] == SLIDESHOW_MODE_ALL_IMAGES
    assert valid["slideshow_transition"] == "soft"


def test_slideshow_plan_matches_audio_duration() -> None:
    plan = build_slideshow_plan(123.456, 17, "auto")
    assert plan is not None
    assert plan.image_count == 17
    assert abs(plan.total_duration - 123.456) < 0.02
    assert plan.visible_duration > 0
    assert "17 Bilder" in slideshow_summary(123.456, 17, "auto")


def test_all_images_are_applied_to_every_audio(tmp_path: Path) -> None:
    audios = [tmp_path / "a.wav", tmp_path / "b.wav"]
    images = [tmp_path / f"i{index}.png" for index in range(3)]
    for path in [*audios, *images]:
        path.write_bytes(b"x")

    def fake_probe(path: Path) -> MediaInfo:
        if path.suffix == ".wav":
            return MediaInfo(path, "audio", duration=30.0, codec="pcm_s16le")
        return MediaInfo(path, "image", width=640, height=360, codec="png")

    options = BatchOptions(
        output_dir=tmp_path / "out",
        assignment_mode=SLIDESHOW_MODE_ALL_IMAGES,
        slideshow_transition="soft",
    )
    with mock.patch("videobatch_fast.jobs.probe_media", side_effect=fake_probe):
        jobs = build_jobs(audios, images, options)
    assert len(jobs) == 2
    assert all(job.media_sequence == tuple(images) for job in jobs)
    assert all(job.is_slideshow for job in jobs)
    assert all(job.slide_duration is not None for job in jobs)
    assert all(job.slide_transition == 0.5 for job in jobs)


def test_slideshow_command_uses_one_filtergraph_and_detected_audio_length(tmp_path: Path) -> None:
    audio = tmp_path / "audio.wav"
    images = tuple(tmp_path / f"image-{index}.png" for index in range(3))
    for path in (audio, *images):
        path.write_bytes(b"x")
    options = BatchOptions(
        output_dir=tmp_path,
        overwrite=True,
        assignment_mode=SLIDESHOW_MODE_ALL_IMAGES,
        slideshow_transition="soft",
    )
    with mock.patch("videobatch_fast.jobs.probe_media") as probe:
        probe.side_effect = lambda path: (
            MediaInfo(path, "audio", duration=12.0, codec="pcm_s16le")
            if path == audio
            else MediaInfo(path, "image", width=640, height=360, codec="png")
        )
        job = build_jobs([audio], list(images), options)[0]
    command = build_command(job, options)
    graph = command[command.index("-filter_complex") + 1]
    assert graph.count("xfade=") == 2
    assert "scale=640:360" in graph
    assert command.count("-loop") == 3
    assert command[command.index("-t", command.index("-c:a")) + 1] == "12.000"
    assert "[xf2]" in command


@pytest.mark.skipif(shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None, reason="FFmpeg fehlt")
def test_real_two_image_slideshow_render(tmp_path: Path) -> None:
    audio = tmp_path / "audio.wav"
    with wave.open(str(audio), "wb") as target:
        target.setnchannels(1)
        target.setsampwidth(2)
        target.setframerate(8000)
        target.writeframes(b"\x00\x00" * 8000 * 2)
    images = [tmp_path / "red.png", tmp_path / "blue.png"]
    Image.new("RGB", (320, 180), "red").save(images[0])
    Image.new("RGB", (320, 180), "blue").save(images[1])
    options = BatchOptions(
        output_dir=tmp_path,
        overwrite=True,
        assignment_mode=SLIDESHOW_MODE_ALL_IMAGES,
        slideshow_transition="soft",
        profile="turbo",
        verification="Schnell",
    )
    jobs = build_jobs([audio], images, options)
    assert len(jobs) == 1
    command = build_command(jobs[0], options)
    result = subprocess.run(command, capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stderr
    output = jobs[0].output
    assert output.is_file() and output.stat().st_size > 1000
    duration = subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(output)
    ], text=True).strip()
    assert 1.85 <= float(duration) <= 2.15

def test_ctrl_mousewheel_and_header_font_controls_are_bound() -> None:
    zoom_source = (ROOT / "src/videobatch_fast/ui_area_zoom_mixin.py").read_text(encoding="utf-8")
    header_source = (ROOT / "src/videobatch_fast/ui_workspace_grid_mixin.py").read_text(encoding="utf-8")
    assert "<Control-MouseWheel>" in zoom_source
    assert "<Control-Button-4>" in zoom_source
    assert "<Control-Button-5>" in zoom_source
    assert "header_font_label" in header_source
    assert "_set_global_zoom" in header_source


def test_dashboard_is_scrollable_on_compact_displays() -> None:
    source = (ROOT / "src/videobatch_fast/ui_workspace_grid_mixin.py").read_text(encoding="utf-8")
    assert "_scrollable_dashboard_body" in source
    assert "scrollregion" in source
    assert "ttk.Scrollbar" in source
