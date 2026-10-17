"""Real FFmpeg output proof with synthetic, disposable audio and images.

No downloads, no user media, no release evidence or GUI interaction.
"""
from __future__ import annotations

import hashlib
import json
import math
import shutil
import struct
import subprocess
import wave
from pathlib import Path
from unittest.mock import patch

import pytest
from PIL import Image

from videobatch_fast.command_builder import build_command
from videobatch_fast.models import BatchOptions, MediaInfo, PairJob
from videobatch_fast.probe_render import plan_probe


def _command(binary: str, *args: str, timeout: int = 45) -> subprocess.CompletedProcess:
    return subprocess.run([binary, *args], capture_output=True, text=True,
                          errors="replace", timeout=timeout, check=False)


def _audio(path: Path, seconds: int = 1) -> None:
    rate = 8000
    with wave.open(str(path), "wb") as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(rate)
        frames = b"".join(
            struct.pack("<h", int(10000 * math.sin(2 * math.pi * 440 * tick / rate)))
            for tick in range(rate * seconds)
        )
        out.writeframes(frames)


def _inputs(tmp_path: Path) -> tuple[Path, Path, Path]:
    audio = tmp_path / "test.wav"
    image1 = tmp_path / "first.png"
    image2 = tmp_path / "second.png"
    _audio(audio)
    Image.new("RGB", (160, 90), (10, 100, 170)).save(image1)
    Image.new("RGB", (160, 90), (180, 55, 95)).save(image2)
    return audio, image1, image2


@pytest.mark.parametrize("slideshow", [False, True])
def test_ffmpeg_creates_real_playable_mp4_without_touching_sources(
    tmp_path: Path, slideshow: bool,
) -> None:
    ffmpeg, ffprobe = shutil.which("ffmpeg"), shutil.which("ffprobe")
    if not ffmpeg or not ffprobe:
        pytest.fail("Pflichtwerkzeuge FFmpeg und FFprobe fehlen im Testsystem.")
    audio, image1, image2 = _inputs(tmp_path)
    source_hashes = {
        path: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in (audio, image1, image2)
    }
    output = tmp_path / ("diashow.mp4" if slideshow else "bild_mit_ton.mp4")
    job = PairJob(
        index=1, audio=audio, media=image1, output=output,
        audio_info=MediaInfo(audio, "audio", duration=1.0),
        media_info=MediaInfo(image1, "image", width=160, height=90),
        fast_path=False, reason="Echter Encoding-Test",
        media_sequence=(image1, image2) if slideshow else (),
        slide_durations=(0.5, 0.5) if slideshow else (),
    )
    options = BatchOptions(
        output_dir=tmp_path, resolution="1280×720", profile="turbo",
        visual_effect="none", codec="libx264", fps=12,
        max_threads=2, quick_mode="custom", audio_bitrate="96k",
    )
    command = build_command(job, options)
    result = subprocess.run(command, capture_output=True, text=True,
                            errors="replace", timeout=45, check=False)
    assert result.returncode == 0, result.stderr[-3000:]
    assert output.is_file() and output.stat().st_size > 1024

    probe = _command(
        ffprobe, "-v", "error", "-show_entries",
        "stream=codec_type,width,height:format=duration",
        "-of", "json", str(output)
    )
    assert probe.returncode == 0, probe.stderr
    payload = json.loads(probe.stdout)
    streams = payload["streams"]
    assert any(
        item["codec_type"] == "video" and
        item.get("width") == 1280 and item.get("height") == 720
        for item in streams
    ), streams
    assert any(item["codec_type"] == "audio" for item in streams), streams
    assert float(payload["format"]["duration"]) > 0.4
    assert all(hashlib.sha256(path.read_bytes()).hexdigest() == digest
               for path, digest in source_hashes.items())


def test_short_preview_is_real_mp4_and_uses_only_disposable_destination(
    tmp_path: Path,
) -> None:
    ffmpeg = shutil.which("ffmpeg")
    ffprobe = shutil.which("ffprobe")
    if not ffmpeg or not ffprobe:
        pytest.fail("FFmpeg und FFprobe für den Live-Probelauf erforderlich.")
    audio, image, _ = _inputs(tmp_path)
    originals = {source: hashlib.sha256(source.read_bytes()).hexdigest()
                 for source in (audio, image)}
    normal = tmp_path / "production" / "normal.mp4"
    preview = tmp_path / "cache" / "probe" / "vb-probe-live.mp4"
    preview.parent.mkdir(parents=True)
    job = PairJob(
        index=2, audio=audio, media=image, output=normal,
        audio_info=MediaInfo(path=audio, kind="audio", duration=1.0),
        media_info=MediaInfo(path=image, kind="image", width=160, height=90),
        fast_path=False, reason="preview smoke",
    )
    options = BatchOptions(
        output_dir=normal.parent, resolution="1280×720", profile="turbo",
        visual_effect="none", quick_mode="custom", codec="libx264", fps=12,
        max_threads=2, audio_bitrate="96k",
    )
    short_job, short_options = plan_probe(job, options, preview)
    ffmpeg_command = build_command(short_job, short_options)
    result = subprocess.run(ffmpeg_command, capture_output=True, text=True,
                            errors="replace", timeout=45, check=False)
    assert result.returncode == 0, result.stderr[-2800:]
    assert preview.stat().st_size > 1024
    result = _command(ffprobe, "-v", "error", "-show_entries",
                      "format=duration:stream=codec_type", "-of", "json",
                      str(preview))
    payload = json.loads(result.stdout)
    assert result.returncode == 0
    assert 0.4 < float(payload["format"]["duration"]) <= 1.6
    assert {s["codec_type"] for s in payload["streams"]} >= {"audio", "video"}
    assert not normal.exists()
    assert all(hashlib.sha256(source.read_bytes()).hexdigest() == digest
               for source, digest in originals.items())


@pytest.mark.parametrize("slideshow", [False, True])
@pytest.mark.parametrize("profile,effect", [("turbo", "none"), ("quality", "vivid")])
def test_real_render_matrix_quality_effect_and_slideshow(
    tmp_path: Path, slideshow: bool, profile: str, effect: str,
) -> None:
    """Validate decoded MP4 results, not merely planned encoder arguments."""
    ffmpeg, ffprobe = shutil.which("ffmpeg"), shutil.which("ffprobe")
    if not ffmpeg or not ffprobe:
        pytest.fail("FFmpeg und FFprobe sind für den echten Rendertest notwendig.")
    audio, first, second = _inputs(tmp_path)
    source_hashes = {
        path: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in (audio, first, second)
    }
    output = tmp_path / f"{profile}-{effect}-{'slides' if slideshow else 'image'}.mp4"
    job = PairJob(
        index=1, audio=audio, media=first, output=output,
        audio_info=MediaInfo(audio, "audio", duration=1.0),
        media_info=MediaInfo(first, "image", width=160, height=90),
        fast_path=False, reason="render matrix",
        media_sequence=(first, second) if slideshow else (),
        slide_durations=(0.5, 0.5) if slideshow else (),
    )
    options = BatchOptions(
        output_dir=tmp_path, resolution="Original", profile=profile,
        visual_effect=effect, codec="libx264", fps=12,
        max_threads=2, quick_mode="custom", audio_bitrate="96k",
    )
    command = build_command(job, options)
    assert command[command.index("-crf") + 1] in {"23", "18"}
    encoded = subprocess.run(
        command, capture_output=True, text=True, errors="replace",
        timeout=60, check=False,
    )
    assert encoded.returncode == 0, encoded.stderr[-3000:]
    assert output.is_file() and output.stat().st_size > 1024
    inspected = _command(
        ffprobe, "-v", "error", "-show_entries",
        "stream=codec_type,width,height:format=duration", "-of", "json",
        str(output),
    )
    assert inspected.returncode == 0, inspected.stderr
    payload = json.loads(inspected.stdout)
    assert any(
        s["codec_type"] == "video" and s.get("width") == 160
        and s.get("height") == 90 for s in payload["streams"]
    )
    assert any(s["codec_type"] == "audio" for s in payload["streams"])
    assert 0.4 < float(payload["format"]["duration"]) <= 1.5
    # Decode actual frames and audio: valid metadata alone is insufficient.
    decoded = _command(
        ffmpeg, "-v", "error", "-i", str(output),
        "-map", "0:v:0", "-frames:v", "2", "-f", "null", "-",
        timeout=30,
    )
    assert decoded.returncode == 0, decoded.stderr
    assert all(
        hashlib.sha256(path.read_bytes()).hexdigest() == digest
        for path, digest in source_hashes.items()
    )


def test_real_ffmpeg_cancel_persists_retry_across_runner_restart(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Cancel a genuine live encoder, reopen its retry state, and render again."""
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        pytest.fail("FFmpeg und FFprobe sind für den Wiederanlauftest erforderlich.")
    from videobatch_fast.runner import BatchRunner
    from videobatch_fast.retry_queue import RetryQueueStore, job_identity
    from videobatch_fast import runner as runner_module

    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    audio, image, _ = _inputs(tmp_path)
    _audio(audio, seconds=8)
    originals = {
        source: hashlib.sha256(source.read_bytes()).hexdigest()
        for source in (audio, image)
    }
    output = tmp_path / "interrupted.mp4"
    job = PairJob(
        index=1, audio=audio, media=image, output=output,
        audio_info=MediaInfo(audio, "audio", duration=8.0),
        media_info=MediaInfo(image, "image", width=160, height=90),
        fast_path=False, reason="live cancellation",
    )
    options = BatchOptions(
        output_dir=tmp_path, resolution="Original", profile="turbo",
        visual_effect="none", codec="libx264", fps=12,
        max_threads=2, quick_mode="custom", audio_bitrate="96k",
    )
    retry_path = tmp_path / "retry_queue.json"
    runner = BatchRunner(lambda _event: None, retry_queue_path=retry_path)
    ordinary_command = runner_module.build_command

    def paced_command(actual_job, actual_options, **kwargs):
        command = ordinary_command(actual_job, actual_options, **kwargs)
        command.insert(command.index("-i"), "-re")
        return command

    # -re throttles the live source. No fake FFmpeg process is used.
    with patch.object(runner_module, "build_command", side_effect=paced_command):
        runner.start([job], options)
        deadline = __import__("time").monotonic() + 8.0
        try:
            while __import__("time").monotonic() < deadline:
                process = runner._process
                if process is not None and process.poll() is None:
                    break
                __import__("time").sleep(0.05)
            else:
                pytest.fail("Kein laufender FFmpeg-Prozess zum Abbrechen gefunden.")
            runner.cancel()
            assert runner.wait(timeout=20), "Abbruch beendete den Stapel nicht."
        finally:
            if runner.running:
                runner.cancel()
                runner.wait(timeout=10)

    # Simulate a fresh process: do not reuse the previous in-memory queue.
    persisted = RetryQueueStore(retry_path)
    entries = persisted.eligible_entries()
    assert len(entries) == 1
    assert entries[0]["job_id"] == job_identity(job)
    assert entries[0]["attempts"] == 1
    assert entries[0]["output"] == str(output)
    assert all(
        hashlib.sha256(path.read_bytes()).hexdigest() == digest
        for path, digest in originals.items()
    )

    # A resumed job must use a fresh destination; never overwrite originals.
    resumed = PairJob(
        index=2, audio=audio, media=image, output=tmp_path / "resumed.mp4",
        audio_info=job.audio_info, media_info=job.media_info,
        fast_path=False, reason="new validated destination",
    )
    completed = subprocess.run(
        build_command(resumed, options), capture_output=True, text=True,
        errors="replace", timeout=60, check=False,
    )
    assert completed.returncode == 0, completed.stderr[-3000:]
    probe = _command(shutil.which("ffprobe"), "-v", "error", "-show_entries",
                     "stream=codec_type:format=duration", "-of", "json",
                     str(resumed.output))
    assert probe.returncode == 0, probe.stderr
    payload = json.loads(probe.stdout)
    assert {stream["codec_type"] for stream in payload["streams"]} >= {"audio", "video"}
    assert float(payload["format"]["duration"]) > 7.0
    assert all(
        hashlib.sha256(path.read_bytes()).hexdigest() == digest
        for path, digest in originals.items()
    )


def test_real_mp4_effect_changes_decoded_pixels(tmp_path: Path) -> None:
    """Measure actual decoded frame differences, not just effect arguments."""
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg or not shutil.which("ffprobe"):
        pytest.fail("FFmpeg und FFprobe erforderlich.")
    audio, source, _ = _inputs(tmp_path)
    frames = []
    for effect in ("none", "vivid"):
        target = tmp_path / f"effect-{effect}.mp4"
        job = PairJob(
            index=1, audio=audio, media=source, output=target,
            audio_info=MediaInfo(audio, "audio", duration=1.0),
            media_info=MediaInfo(source, "image", width=160, height=90),
            fast_path=False, reason="decoded effect comparison",
        )
        options = BatchOptions(
            output_dir=tmp_path, profile="turbo", resolution="Original",
            visual_effect=effect, quick_mode="custom", codec="libx264",
            fps=12, max_threads=2, audio_bitrate="96k",
        )
        result = _command(ffmpeg, *build_command(job, options)[1:], timeout=60)
        assert result.returncode == 0, result.stderr[-2500:]
        decoded = subprocess.run(
            [ffmpeg, "-v", "error", "-i", str(target), "-map", "0:v:0",
             "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
            capture_output=True, timeout=30, check=False,
        )
        assert decoded.returncode == 0, decoded.stderr[-2000:]
        assert len(decoded.stdout) == 160 * 90 * 3
        frames.append(decoded.stdout)
    differences = sum(a != b for a, b in zip(*frames))
    assert differences > len(frames[0]) // 100, (
        f"Der Effekt verändert nur {differences} der {len(frames[0])} Farbwerte."
    )
