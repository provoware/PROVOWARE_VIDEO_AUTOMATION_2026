#!/usr/bin/env python3
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "tests" / "generated_media"


def run(command: list[str]) -> None:
    subprocess.run(command, check=True, capture_output=True, text=True, errors="replace")


def main() -> int:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        print("TESTMEDIEN BLOCKIERT · FFmpeg fehlt")
        return 2
    TARGET.mkdir(parents=True, exist_ok=True)
    files = {
        "audio_short": TARGET / "audio_kurz.wav",
        "image_landscape": TARGET / "bild_querformat.png",
        "video_compatible": TARGET / "video_kompatibel.mp4",
        "video_short": TARGET / "video_zu_kurz.mp4",
        "corrupt_media": TARGET / "medium_beschaedigt.mp4",
        "unicode_image": TARGET / "bühne_äöü_测试.png",
    }
    run([ffmpeg, "-v", "error", "-y", "-f", "lavfi", "-i", "sine=frequency=220:duration=2", str(files["audio_short"])])
    run([ffmpeg, "-v", "error", "-y", "-f", "lavfi", "-i", "color=c=0x123456:s=640x360", "-frames:v", "1", str(files["image_landscape"])])
    run([ffmpeg, "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=s=640x360:r=25:d=2", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(files["video_compatible"])])
    run([ffmpeg, "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=s=320x180:r=25:d=0.5", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(files["video_short"])])
    files["corrupt_media"].write_bytes(b"not a real media file")
    shutil.copy2(files["image_landscape"], files["unicode_image"])
    manifest = {"schema_version": 1, "files": {key: str(path.relative_to(ROOT)) for key, path in files.items()}}
    (TARGET / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"TESTMEDIEN ERZEUGT · {len(files)} Dateien · {TARGET}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
