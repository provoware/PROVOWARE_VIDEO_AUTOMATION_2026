"""Regression checks for Qt output controls and FFmpeg parameter propagation."""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from videobatch_fast.command_builder import build_command, PROFILES, RESOLUTIONS
from videobatch_fast.effects import VISUAL_EFFECTS, effect_filter, transition_filters
from videobatch_fast.models import BatchOptions, MediaInfo, PairJob
from videobatch_fast.project_state import normalize_project_state
from videobatch_fast.slideshow import build_slideshow_plan, slideshow_summary, transition_seconds


def _picture_job() -> PairJob:
    return PairJob(
        index=1,
        audio=Path("sound.wav"),
        media=Path("picture.png"),
        output=Path("result.mp4"),
        audio_info=MediaInfo(Path("sound.wav"), "audio", duration=30.0),
        media_info=MediaInfo(Path("picture.png"), "image", width=1920, height=1080),
        fast_path=False,
        reason="test",
    )


def test_effect_strength_zero_and_default_legacy() -> None:
    for key, effect in VISUAL_EFFECTS.items():
        assert effect_filter(key, 100) == effect.filter_expression
        assert effect_filter(key, 0) is None
    assert "contrast=1.0800" in str(effect_filter("industrial", 50))
    assert effect_filter("industrial", 50) != effect_filter("industrial", 100)


def test_fade_duration_override_is_bounded() -> None:
    assert transition_filters("none", 25.0, 3.5) == []
    assert any("d=3.500" in part for part in transition_filters("cinema", 25.0, 3.5))
    assert any("d=5.000" in part for part in transition_filters("cinema", 25.0, 12.0))
    assert any("d=1.000" in part for part in transition_filters("cinema", 2.0, 5.0))
    assert transition_filters("cinema", 20.0, 0.0) == []


def test_slideshow_manual_zero_and_five_seconds() -> None:
    no_fade = build_slideshow_plan(120.0, 4, "custom", custom_seconds=0.0)
    long_fade = build_slideshow_plan(120.0, 4, "custom", custom_seconds=5.0)
    assert no_fade is not None and long_fade is not None
    assert no_fade.crossfade_duration == 0.0
    assert long_fade.crossfade_duration == 5.0
    assert abs(long_fade.total_duration - 120.0) < 0.01


def test_slideshow_impossible_request_reports_effective_duration() -> None:
    assert transition_seconds("custom", audio_duration=4.0, image_count=4, custom_seconds=5.0) < 5.0
    summary = slideshow_summary(4.0, 4, "custom", custom_seconds=5.0)
    assert "Wunsch 5.0s gekürzt" in summary


def test_ffmpeg_command_uses_intensity_quality_fade_and_resolution() -> None:
    options = BatchOptions(
        output_dir=Path("."), quick_mode="custom", resolution="2560×1440",
        profile="maximum", visual_effect="industrial", effect_intensity=50,
        transition="cinema", transition_duration=3.5,
    )
    command = build_command(_picture_job(), options)
    assert command[command.index("-crf") + 1] == str(PROFILES["maximum"].crf)
    filters = command[command.index("-vf") + 1]
    assert "scale=2560:1440:" in filters
    assert "contrast=1.0800" in filters
    assert "d=3.500" in filters
    assert RESOLUTIONS["3840×2160"] == (3840, 2160)


def test_project_settings_roundtrip_validation() -> None:
    normalized = normalize_project_state({
        "quick_mode": "custom",
        "resolution": "3840×2160",
        "profile": "maximum",
        "visual_effect": "industrial",
        "effect_intensity": 65,
        "transition": "cinema",
        "transition_duration": 3.5,
        "slideshow_transition": "custom",
        "slideshow_transition_seconds": 4.7,
        "verification": "Vollständig",
    })
    assert normalized["resolution"] == "3840×2160"
    assert normalized["effect_intensity"] == 65
    assert normalized["transition_duration"] == 3.5
    assert normalized["slideshow_transition_seconds"] == 4.7
    assert normalize_project_state({"effect_intensity": -3})["effect_intensity"] == 100


def test_qt_custom_mode_controls_follow_video_options() -> None:
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    pytest.importorskip("PySide6")
    from PySide6.QtWidgets import QApplication
    from videobatch_fast.qt_ui import VideoBatchQtWindow

    app = QApplication.instance() or QApplication([])
    window = VideoBatchQtWindow()
    try:
        window.mode.setCurrentIndex(window.mode.findData("custom"))
        window.resolution.setCurrentIndex(window.resolution.findData("3840×2160"))
        window.quality.setCurrentIndex(window.quality.findData("maximum"))
        window.effect_choice.setCurrentIndex(window.effect_choice.findData("industrial"))
        window.effect_intensity.setValue(75)
        window.fade_choice.setCurrentIndex(window.fade_choice.findData("cinema"))
        window.fade_seconds.setValue(4.0)
        selected = window._options()
        assert selected.quick_mode == "custom"
        assert selected.resolution == "3840×2160"
        assert selected.profile == "maximum"
        assert selected.effect_intensity == 75
        assert selected.transition_duration == 4.0
    finally:
        window.close()
