"""Regression checks: content probing and odd-dimension output safety."""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from videobatch_fast import probe
from videobatch_fast.command_builder import build_command
from videobatch_fast.models import BatchOptions, MediaInfo, PairJob
from videobatch_fast.resource_estimation import estimate_job_output_bytes


def test_unreadable_stream_is_never_accepted_by_extension(monkeypatch) -> None:
    probe.probe_media_cached.cache_clear()
    monkeypatch.setattr(probe, "ffprobe_path", lambda: "/usr/bin/ffprobe")
    monkeypatch.setattr(probe.subprocess, "run", lambda *_a, **_kw: SimpleNamespace(
        stdout=json.dumps({"streams": [], "format": {"duration": "4"}})
    ))
    image = probe.probe_media_cached("/tmp/suspicious.png", 5, 100)
    assert image.kind == "unknown"
    assert image.duration == 4.0


def test_variable_video_frame_rate_is_an_advisory_flag(monkeypatch) -> None:
    probe.probe_media_cached.cache_clear()
    monkeypatch.setattr(probe, "ffprobe_path", lambda: "/usr/bin/ffprobe")
    monkeypatch.setattr(probe.subprocess, "run", lambda *_a, **_kw: SimpleNamespace(
        stdout=json.dumps({"streams": [{"codec_type": "video",
                           "codec_name": "h264", "width": 641, "height": 479,
                           "r_frame_rate": "30/1", "avg_frame_rate": "20/1"}],
                           "format": {"duration": "6"}})
    ))
    info = probe.probe_media_cached("/tmp/capture.mp4", 4, 123)
    assert info.kind == "video"
    assert info.variable_frame_rate is True


def test_odd_source_is_padded_only_when_encoding() -> None:
    audio = MediaInfo(Path("a.wav"), "audio", duration=5.0)
    image = MediaInfo(Path("a.png"), "image", width=641, height=479)
    job = PairJob(1, Path("a.wav"), Path("a.png"), Path("out.mp4"),
                  audio, image, False, "test")
    options = BatchOptions(output_dir=Path("."), quick_mode="custom")
    command = build_command(job, options)
    assert "pad=ceil(iw/2)*2:ceil(ih/2)*2" in command[command.index("-vf") + 1]

    video = MediaInfo(Path("a.mp4"), "video", duration=5.0, codec="h264")
    copy_job = PairJob(1, Path("a.wav"), Path("a.mp4"), Path("out.mp4"),
                       audio, video, True, "copy")
    copied = build_command(copy_job, options)
    assert copied[copied.index("-c:v") + 1] == "copy"
    assert "-vf" not in copied


def test_nonfinite_audio_duration_uses_safe_disk_reserve() -> None:
    audio = Path("track.wav")
    image = Path("cover.png")
    media = MediaInfo(image, "image", width=1280, height=720)
    options = BatchOptions(output_dir=Path("."), quick_mode="custom")

    def estimate(duration: float | None) -> int:
        job = PairJob(
            1, audio, image, Path("output.mp4"),
            MediaInfo(audio, "audio", duration=duration), media, False, "test",
        )
        return estimate_job_output_bytes(job, options)

    unknown_duration_reserve = estimate(None)
    for invalid_duration in (float("nan"), float("inf"), float("-inf")):
        assert estimate(invalid_duration) == unknown_duration_reserve
    # Ordinary finite durations retain their existing size estimate.
    assert estimate(10.0) < unknown_duration_reserve
