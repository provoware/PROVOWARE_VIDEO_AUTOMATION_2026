"""Preview runs one original pair for <=10 seconds and never rewrites sources."""
from dataclasses import replace
from pathlib import Path

import pytest

from videobatch_fast.models import BatchOptions, MediaInfo, PairJob
from videobatch_fast.probe_render import plan_probe, prune_probes


def _pair(tmp_path: Path, *, duration: float = 110.0) -> PairJob:
    audio = tmp_path / "track.wav"
    media = tmp_path / "cover.png"
    audio.write_bytes(b"original audio")
    media.write_bytes(b"original image")
    return PairJob(
        index=4, audio=audio, media=media,
        output=tmp_path / "production" / "full.mp4",
        audio_info=MediaInfo(path=audio, kind="audio", duration=duration),
        media_info=MediaInfo(path=media, kind="image", width=1080, height=1080),
        fast_path=True, reason="test",
    )


def test_preview_shortens_only_job_metadata_and_preserves_render_choices(tmp_path: Path):
    job = _pair(tmp_path)
    options = BatchOptions(
        output_dir=tmp_path / "production", resolution="1920×1080",
        profile="maximum", visual_effect="vivid", quick_mode="custom",
    )
    probe_path = tmp_path / "cache" / "vb-probe-example.mp4"
    short, preview_options = plan_probe(job, options, probe_path)
    assert short.index == 1
    assert short.output == probe_path
    assert short.audio_info.duration == 10.0
    assert short.fast_path is False
    assert short.audio == job.audio and short.media == job.media
    assert job.audio_info.duration == 110.0 and job.fast_path
    assert preview_options.output_dir == probe_path.parent
    assert preview_options.profile == "maximum"
    assert preview_options.visual_effect == "vivid"
    assert preview_options.resolution == "1920×1080"
    assert options.output_dir == tmp_path / "production"
    assert job.audio.read_bytes() == b"original audio"
    assert job.media.read_bytes() == b"original image"


def test_preview_rejects_unsupported_slideshows_or_unknown_duration(tmp_path: Path):
    job = _pair(tmp_path)
    options = BatchOptions(output_dir=tmp_path)
    with pytest.raises(ValueError):
        plan_probe(replace(job, media_sequence=(job.media,)), options,
                   tmp_path / "probe.mp4")
    with pytest.raises(ValueError):
        plan_probe(replace(job, audio_info=replace(job.audio_info, duration=None)),
                   options, tmp_path / "probe.mp4")


def test_preview_never_runs_longer_than_short_audio(tmp_path: Path):
    job = _pair(tmp_path, duration=3.2)
    short, _ = plan_probe(job, BatchOptions(output_dir=tmp_path),
                          tmp_path / "probe.mp4")
    assert short.audio_info.duration == 3.2


def test_preview_cleanup_keeps_foreign_files_and_symlinks(tmp_path: Path):
    directory = tmp_path / "probes"
    directory.mkdir()
    images = [directory / f"vb-probe-{i}.mp4" for i in range(6)]
    for path in images:
        path.write_bytes(b"probe")
    foreign = directory / "family.mp4"
    foreign.write_bytes(b"precious")
    symlink = directory / "vb-probe-link.mp4"
    symlink.symlink_to(foreign)
    assert prune_probes(directory, keep=2) == 4
    assert len([f for f in images if f.exists()]) == 2
    assert symlink.is_symlink() and foreign.read_bytes() == b"precious"
