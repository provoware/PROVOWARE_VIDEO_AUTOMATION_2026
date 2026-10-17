"""Contract tests: dashboard selections must reach the actual FFmpeg arguments."""
from pathlib import Path

from videobatch_fast.command_builder import PROFILES, RESOLUTIONS, build_command, resolved_options
from videobatch_fast.dashboard_settings import DashboardSettings
from videobatch_fast.models import BatchOptions, MediaInfo, PairJob


def _job(tmp_path):
    audio = tmp_path / "track.wav"
    image = tmp_path / "cover.png"
    return PairJob(
        index=1, audio=audio, media=image, output=tmp_path / "video.mp4",
        audio_info=MediaInfo(path=audio, kind="audio", duration=12.0),
        media_info=MediaInfo(path=image, kind="image", width=1600, height=900),
        fast_path=False, reason="image encoding",
    )


def test_all_global_resolutions_have_ffmpeg_targets():
    assert RESOLUTIONS["Original"] is None
    assert RESOLUTIONS["1280×720"] == (1280, 720)
    assert RESOLUTIONS["1920×1080"] == (1920, 1080)
    assert RESOLUTIONS["2560×1440"] == (2560, 1440)
    assert RESOLUTIONS["3840×2160"] == (3840, 2160)


def test_quality_profile_levels_are_distinct():
    for key in ("turbo", "balanced", "quality", "maximum"):
        assert key in PROFILES
    assert PROFILES["maximum"].crf < PROFILES["quality"].crf


def test_explicit_ffmpeg_resolution_quality_and_effect(tmp_path):
    from videobatch_fast.effects import effect_filter
    job = _job(tmp_path)
    selected = BatchOptions(
        output_dir=tmp_path, quick_mode="custom",
        resolution="2560×1440", profile="maximum", visual_effect="vivid",
    )
    assert resolved_options(job, selected) == selected
    cmd = build_command(job, selected)
    assert "-vf" in cmd
    filter_string = cmd[cmd.index("-vf") + 1]
    assert "scale=2560:1440:" in filter_string
    assert effect_filter("vivid") in filter_string
    assert cmd[cmd.index("-crf") + 1] == str(PROFILES["maximum"].crf)


def test_explicit_output_directory_preserved(tmp_path):
    job = _job(tmp_path)
    settings = BatchOptions(output_dir=Path(tmp_path / "out"), quick_mode="custom")
    assert resolved_options(job, settings).output_dir == settings.output_dir

def test_dashboard_values_survive_preset_and_reach_ffmpeg(tmp_path):
    """A user-selected resolution/profile/effect must reach the final command."""
    from videobatch_fast.effects import effect_filter

    settings = DashboardSettings()
    settings = settings.set_user_value("resolution", "Full HD")
    settings = settings.set_user_value("quality", "Maximum")
    settings = settings.set_user_value("effect", "vivid")
    settings = settings.set_user_value("output_dir", tmp_path / "fertig")
    settings = settings.apply_preset({
        "resolution": "HD", "quality": "Schnell", "effect": "none",
        "output_dir": tmp_path / "falsch",
    })
    options = BatchOptions(
        output_dir=settings.output_dir, resolution=settings.resolution,
        profile=settings.quality, visual_effect=settings.effect,
        transition="none", quick_mode="custom",
    )
    job = _job(tmp_path)
    resolved = resolved_options(job, options)
    command = build_command(job, resolved)
    assert resolved.output_dir == tmp_path / "fertig"
    assert resolved.resolution == "1920×1080"
    assert resolved.profile == "maximum"
    assert "scale=1920:1080:" in command[command.index("-vf") + 1]
    assert effect_filter("vivid") in command[command.index("-vf") + 1]
    assert command[command.index("-crf") + 1] == str(PROFILES["maximum"].crf)
