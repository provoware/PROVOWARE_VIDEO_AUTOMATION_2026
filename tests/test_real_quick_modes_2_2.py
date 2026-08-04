from __future__ import annotations

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from videobatch_fast.command_builder import build_command
from videobatch_fast.models import BatchOptions, MediaInfo, PairJob
from videobatch_fast.quick_modes import automatic_mode_keys
from videobatch_fast.verification import verify_output


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "FFmpeg fehlt")
class RealQuickModeMatrixTests(unittest.TestCase):
    def test_all_automatic_modes_render_a_small_valid_file(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            image = root / "image.png"
            audio = root / "audio.wav"
            subprocess.run(
                ["ffmpeg", "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i", "color=c=0x182020:s=160x90:d=1", "-frames:v", "1", str(image)],
                check=True,
            )
            subprocess.run(
                ["ffmpeg", "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i", "sine=frequency=110:duration=0.7", str(audio)],
                check=True,
            )
            for index, key in enumerate(automatic_mode_keys(), start=1):
                output = root / f"{index:02d}_{key}.mp4"
                job = PairJob(
                    index,
                    audio,
                    image,
                    output,
                    MediaInfo(audio, "audio", 0.7, "pcm_s16le"),
                    MediaInfo(image, "image", None, "png", 160, 90),
                    False,
                    key,
                )
                options = BatchOptions(root, overwrite=True, quick_mode=key)
                command = build_command(job, options)
                result = subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True, timeout=30)
                self.assertEqual(result.returncode, 0, f"{key}: {result.stderr[-1000:]}")
                valid, message = verify_output(output, job, "Schnell")
                self.assertTrue(valid, f"{key}: {message}")


if __name__ == "__main__":
    unittest.main()
