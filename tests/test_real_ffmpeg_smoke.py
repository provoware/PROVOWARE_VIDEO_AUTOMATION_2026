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

import pytest
from PIL import Image

from videobatch_fast.command_builder import build_command
from videobatch_fast.models import BatchOptions, MediaInfo, PairJob


def _command(binary: str, *args: str, timeout: int = 45) -> subprocess.CompletedProcess:
    return subprocess.run([binary, *args], capture_output=True, text=True,
                          errors="replace", timeout=timeout, check=False)


def _audio(path: Path) -> None:
    rate = 8000
    with wave.open(str(path), "wb") as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(rate)
        frames = b"".join(
            struct.pack("<h", int(10000 * math.sin(2 * math.pi * 440 * tick / rate)))
            for tick in range(rate)
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
