"""Bounded and advisory input checks must never mutate original media."""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from videobatch_fast import probe
from videobatch_fast import validation
from videobatch_fast.models import BatchOptions, MediaInfo, PairJob


def test_peak_sample_uses_null_sink_and_timeout(monkeypatch) -> None:
    calls = []
    monkeypatch.setattr(probe, "ffmpeg_path", lambda: "/usr/bin/ffmpeg")

    def fake_run(args, **kwargs):
        calls.append((args, kwargs))
        return SimpleNamespace(
            returncode=0, stderr="[Parsed_volumedetect_0] max_volume: -0.2 dB"
        )
    monkeypatch.setattr(probe.subprocess, "run", fake_run)
    probe.sample_audio_peak.cache_clear()
    peak = probe.sample_audio_peak("/tmp/track.wav", 1, 100)
    assert peak == -0.2
    assert calls[0][0][-2:] == ["null", "-"]
    assert calls[0][1]["timeout"] == 12
    assert "-nostdin" in calls[0][0]


def test_variable_frame_rate_and_flash_are_advisory(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(validation, "validate_runtime", lambda: [])
    monkeypatch.setattr(validation, "validate_output_dir", lambda _p: [])
    monkeypatch.setattr(validation, "read_ffmpeg_capabilities", lambda _p: None)
    monkeypatch.setattr(validation, "ffmpeg_path", lambda: "")
    monkeypatch.setattr(validation, "estimate_required_by_filesystem", lambda *_: ())
    audio = tmp_path / "sound.wav"
    image = tmp_path / "clip.mp4"
    audio.write_bytes(b"test")
    image.write_bytes(b"test")
    job = PairJob(
        index=1, audio=audio, media=image, output=tmp_path / "out.mp4",
        audio_info=MediaInfo(audio, "audio", duration=2),
        media_info=MediaInfo(image, "video", duration=2,
                             variable_frame_rate=True),
        fast_path=False, reason="test",
    )
    options = BatchOptions(output_dir=tmp_path, quick_mode="custom",
                           visual_effect="strobe_safe")
    issues = validation.validate_pairs([job], options)
    assert {notice.code for notice in issues} >= {
        "FLASHING_EFFECT", "VIDEO_FRAME_RATE_MAY_VARY"
    }
    assert all(not i.blocking for i in issues)


def test_peak_nonzero_error_is_not_reported_as_safe(monkeypatch) -> None:
    monkeypatch.setattr(probe, "ffmpeg_path", lambda: "/usr/bin/ffmpeg")
    monkeypatch.setattr(probe.subprocess, "run", lambda *_a, **_kw:
                        SimpleNamespace(returncode=1, stderr="max_volume: 0.0 dB"))
    probe.sample_audio_peak.cache_clear()
    assert probe.sample_audio_peak("/tmp/bad.wav", 2, 200) is None
