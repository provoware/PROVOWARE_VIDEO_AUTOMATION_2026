"""Regression checks for compact output settings and real render parameters."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from videobatch_fast.command_builder import PROFILES, RESOLUTIONS, build_command, can_use_fast_copy
from videobatch_fast.config import normalize_config
from videobatch_fast.effects import VISUAL_EFFECTS, effect_filter
from videobatch_fast.models import BatchOptions, MediaInfo, PairJob
from videobatch_fast.project_state import normalize_project_state
from videobatch_fast.slideshow import build_slideshow_plan, transition_seconds, valid_transition_preset


@pytest.mark.parametrize("duration", [0.0, 0.1, 1.0, 3.0, 5.0])
def test_manual_fade_is_valid_and_calculated(duration: float) -> None:
    setting = f"{duration:.1f}"
    assert valid_transition_preset(setting)
    assert transition_seconds(setting, audio_duration=120.0, image_count=10) == duration
    plan = build_slideshow_plan(120.0, 10, setting)
    assert plan is not None
    assert plan.crossfade_duration == duration
    assert plan.total_duration == pytest.approx(120.0, abs=0.01)
    assert len(plan.input_durations) == 10


@pytest.mark.parametrize("invalid", ["-0.1", "5.1", "1.25", "nan", "inf", "bad"])
def test_invalid_fade_never_reaches_filter_graph(invalid: str) -> None:
    assert not valid_transition_preset(invalid)
    assert normalize_config({"slideshow_transition": invalid})["slideshow_transition"] == "auto"


def test_manual_fade_is_safely_limited_for_short_scenes() -> None:
    # A 5-second crossfade cannot fit in a series of 1-second scenes.
    assert transition_seconds("5.0", audio_duration=10.0, image_count=10) == 0.9
    assert transition_seconds("5.0", audio_duration=10.0, image_count=1) == 0.0


@pytest.mark.parametrize("effect", [key for key in VISUAL_EFFECTS if key != "none"])
def test_every_effect_has_real_intermediate_strength(effect: str) -> None:
    at_zero = effect_filter(effect, 0)
    at_half = effect_filter(effect, 50)
    at_full = effect_filter(effect, 100)
    assert at_zero is None
    assert at_half and at_full and at_half != at_full
    assert at_full == VISUAL_EFFECTS[effect].filter_expression


def test_config_and_project_keep_custom_values() -> None:
    config = normalize_config({
        "resolution": "3840×2160", "profile": "maximum",
        "visual_effect": "industrial", "effect_intensity": 75,
        "slideshow_transition": "3.5",
    })
    assert config["resolution"] == "3840×2160"
    assert config["profile"] == "maximum"
    assert config["effect_intensity"] == 75
    assert config["slideshow_transition"] == "3.5"
    assert normalize_config({"effect_intensity": 900})["effect_intensity"] == 100
    assert normalize_config({"effect_intensity": -5})["effect_intensity"] == 0
    project = normalize_project_state(config)
    assert project["effect_intensity"] == 75
    assert project["resolution"] == "3840×2160"
    assert project["slideshow_transition"] == "3.5"


def test_output_profiles_are_independent_of_resolution() -> None:
    assert RESOLUTIONS["2560×1440"] == (2560, 1440)
    assert RESOLUTIONS["3840×2160"] == (3840, 2160)
    assert PROFILES["maximum"].crf < PROFILES["quality"].crf


def _example_video() -> PairJob:
    audio = Path("sound.mp3")
    video = Path("movie.mp4")
    return PairJob(
        1, audio, video, Path("out.mp4"),
        MediaInfo(audio, "audio", 20.0, "mp3"),
        MediaInfo(video, "video", 20.0, "h264"), False, "probe",
    )


def test_zero_intensity_preserves_video_fast_copy() -> None:
    option = BatchOptions(Path("."), visual_effect="industrial", effect_intensity=0)
    assert can_use_fast_copy(_example_video(), option)[0]


def test_custom_video_options_reach_ffmpeg_without_automatic_override() -> None:
    option = BatchOptions(
        Path("."), quick_mode="custom", visual_effect="vivid",
        effect_intensity=50, resolution="3840×2160", profile="maximum",
    )
    with patch("videobatch_fast.command_builder.ffmpeg_path", return_value="ffmpeg"):
        command = build_command(_example_video(), option)
    filter_expression = command[command.index("-vf") + 1]
    assert "scale=3840:2160" in filter_expression
    assert "contrast=1.0300" in filter_expression
    assert "saturation=1.0400" in filter_expression
    assert command[command.index("-crf") + 1] == "16"
    assert command[command.index("-preset") + 1] == "slow"


def test_qt_surface_exposes_actual_output_controls() -> None:
    qt = (Path(__file__).resolve().parents[1] / "src" / "videobatch_fast" / "qt_ui.py").read_text(encoding="utf-8")
    parity = (Path(__file__).resolve().parents[1] / "src" / "videobatch_fast" / "qt_legacy_parity.py").read_text(encoding="utf-8")
    slideshow = (Path(__file__).resolve().parents[1] / "src" / "videobatch_fast" / "qt_phase2_components.py").read_text(encoding="utf-8")
    for field in ("quick_resolution", "quick_profile", "quick_effect", "quick_intensity"):
        assert field in qt and field in parity
    assert "setSingleStep(0.1)" in slideshow
    assert "_connect_easy_output_settings(window)" in parity


def test_real_five_second_crossfade_when_ffmpeg_is_available(tmp_path: Path) -> None:
    """Short real render: two images, five-second xfade, twelve-second audio."""
    import shutil
    import struct
    import subprocess
    import wave
    import zlib

    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        pytest.skip("Real FFmpeg tools unavailable in this test environment")

    def make_png(color: tuple[int, int, int]) -> bytes:
        def chunk(kind: bytes, data: bytes) -> bytes:
            return (
                struct.pack(">I", len(data)) + kind + data
                + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
            )
        header = struct.pack(">IIBBBBB", 64, 64, 8, 2, 0, 0, 0)
        pixels = b"".join(b"\\x00" + bytes(color) * 64 for _ in range(64))
        return (
            b"\\x89PNG\\r\\n\\x1a\\n" + chunk(b"IHDR", header)
            + chunk(b"IDAT", zlib.compress(pixels)) + chunk(b"IEND", b"")
        )

    red, blue = tmp_path / "red.png", tmp_path / "blue.png"
    red.write_bytes(make_png((255, 0, 0)))
    blue.write_bytes(make_png((0, 0, 255)))
    audio = tmp_path / "silence.wav"
    with wave.open(str(audio), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(8000)
        wf.writeframes(b"\\x00\\x00" * (12 * 8000))

    plan = build_slideshow_plan(12.0, 2, "5.0")
    assert plan is not None and plan.crossfade_duration == 5.0
    output = tmp_path / "result.mp4"
    job = PairJob(
        1, audio, red, output,
        MediaInfo(audio, "audio", 12.0, "pcm_s16le"),
        MediaInfo(red, "image", None, "png", width=64, height=64),
        False, "integration",
        media_sequence=(red, blue),
        slide_duration=plan.segment_duration,
        slide_transition=plan.crossfade_duration,
        slide_durations=plan.input_durations,
    )
    options = BatchOptions(
        tmp_path, quick_mode="custom", fps=15,
        visual_effect="vivid", effect_intensity=50,
    )
    command = build_command(job, options)
    assert "duration=5.000" in " ".join(command)
    result = subprocess.run(command, capture_output=True, text=True, timeout=90)
    assert result.returncode == 0, result.stderr[-2000:]
    assert output.is_file() and output.stat().st_size > 1000
    probe = subprocess.run(
        [
            "ffprobe", "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=width,height,duration",
            "-of", "json", str(output),
        ],
        capture_output=True, text=True, check=True, timeout=15,
    )
    import json
    stream = json.loads(probe.stdout)["streams"][0]
    assert (stream["width"], stream["height"]) == (64, 64)
    assert abs(float(stream["duration"]) - 12.0) < 0.25
