#!/usr/bin/env python3
from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import time
from pathlib import Path


def timed(command: list[str]) -> float:
    started = time.monotonic()
    subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    return time.monotonic() - started


def main() -> int:
    if not shutil.which("ffmpeg"):
        print("FFmpeg fehlt.")
        return 2
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        video = root / "source.mp4"
        audio = root / "audio.wav"
        copied = root / "copy.mp4"
        encoded = root / "encode.mp4"
        effected = root / "effect.mp4"
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i", "testsrc2=s=1280x720:r=25:d=6", "-c:v", "libx264", "-preset", "ultrafast", str(video)], check=True)
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i", "sine=frequency=440:duration=6", str(audio)], check=True)
        copy_time = timed(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(video), "-i", str(audio), "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", "-c:a", "aac", "-shortest", str(copied)])
        encode_time = timed(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(video), "-i", str(audio), "-map", "0:v:0", "-map", "1:a:0", "-c:v", "libx264", "-preset", "veryfast", "-crf", "21", "-c:a", "aac", "-shortest", str(encoded)])
        effect_time = timed(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(video), "-i", str(audio), "-map", "0:v:0", "-map", "1:a:0", "-vf", "eq=contrast=1.06:saturation=1.08,fade=t=in:st=0:d=0.35,fade=t=out:st=5.65:d=0.35", "-c:v", "libx264", "-preset", "veryfast", "-crf", "21", "-c:a", "aac", "-shortest", str(effected)])
        result = {
            "direct_copy_seconds": round(copy_time, 3),
            "reencode_seconds": round(encode_time, 3),
            "one_pass_effect_seconds": round(effect_time, 3),
            "direct_copy_speedup_vs_reencode": round(encode_time / max(copy_time, 0.001), 1),
            "effect_overhead_vs_reencode_percent": round((effect_time / max(encode_time, 0.001) - 1) * 100, 1),
        }
        print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
