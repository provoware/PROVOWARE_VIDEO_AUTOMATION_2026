from __future__ import annotations

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from videobatch_fast.command_builder import build_command
from videobatch_fast.models import BatchOptions, MediaInfo, PairJob
from videobatch_fast.verification import verify_output


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "FFmpeg fehlt")
class RealFfmpegTests(unittest.TestCase):
    def test_image_audio_production(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            image = root / "image.png"
            audio = root / "audio.wav"
            output = root / "output.mp4"
            subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i", "color=c=blue:s=320x180:d=1", "-frames:v", "1", str(image)], check=True)
            subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i", "sine=frequency=440:duration=1", str(audio)], check=True)
            job = PairJob(1, audio, image, output, MediaInfo(audio, "audio", 1.0, "pcm_s16le"), MediaInfo(image, "image", None, "png", 320, 180), False, "Bild")
            command = build_command(job, BatchOptions(root, profile="turbo", overwrite=True))
            subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True, check=True)
            valid, message = verify_output(output, job)
            self.assertTrue(valid, message)

    def test_image_audio_with_fast_effect_and_transition(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            image = root / "image.png"
            audio = root / "audio.wav"
            output = root / "effect.mp4"
            subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i", "color=c=orange:s=320x180:d=1", "-frames:v", "1", str(image)], check=True)
            subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i", "sine=frequency=330:duration=1.5", str(audio)], check=True)
            job = PairJob(1, audio, image, output, MediaInfo(audio, "audio", 1.5, "pcm_s16le"), MediaInfo(image, "image", None, "png", 320, 180), False, "Bild")
            options = BatchOptions(root, profile="turbo", overwrite=True, visual_effect="vivid", transition="soft")
            command = build_command(job, options)
            subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True, check=True)
            valid, message = verify_output(output, job)
            self.assertTrue(valid, message)
