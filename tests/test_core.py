from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from videobatch_fast.command_builder import build_command, can_use_fast_copy
from videobatch_fast.effects import speed_summary
from videobatch_fast.config import normalize_config
from videobatch_fast.models import BatchOptions, MediaInfo, PairJob
from videobatch_fast.naming import safe_stem, unique_output_path
from videobatch_fast.probe import classify_extension


class NamingTests(unittest.TestCase):
    def test_safe_stem_removes_unsafe_characters(self):
        self.assertEqual(safe_stem("Track:/? 01"), "Track___ 01")

    def test_unique_output_does_not_overwrite(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            with patch("videobatch_fast.naming.timestamp", return_value="20260101_120000"):
                first = unique_output_path(directory, Path("song.mp3"))
                first.touch()
                second = unique_output_path(directory, Path("song.mp3"))
            self.assertNotEqual(first, second)
            self.assertTrue(second.name.endswith("_2.mp4"))


class ProbeTests(unittest.TestCase):
    def test_extension_classification(self):
        self.assertEqual(classify_extension(Path("a.wav")), "audio")
        self.assertEqual(classify_extension(Path("a.png")), "image")
        self.assertEqual(classify_extension(Path("a.mp4")), "video")


class CommandTests(unittest.TestCase):
    def _job(self, kind="video", codec="h264", video_duration=20.0, audio_duration=10.0, fast=True):
        audio = Path("audio.mp3")
        media = Path("media.mp4" if kind == "video" else "image.png")
        return PairJob(1, audio, media, Path("out.mp4"), MediaInfo(audio, "audio", audio_duration, "mp3"), MediaInfo(media, kind, video_duration, codec), fast, "test")

    def test_copy_fast_path_for_compatible_video(self):
        options = BatchOptions(Path("."))
        allowed, _ = can_use_fast_copy(self._job(), options)
        self.assertTrue(allowed)

    def test_scaling_disables_copy(self):
        options = BatchOptions(Path("."), resolution="1920×1080")
        allowed, _ = can_use_fast_copy(self._job(), options)
        self.assertFalse(allowed)

    def test_copy_command_contains_progress_and_copy(self):
        with patch("videobatch_fast.command_builder.ffmpeg_path", return_value="ffmpeg"):
            command = build_command(self._job(), BatchOptions(Path(".")))
        self.assertIn("copy", command)
        self.assertIn("-progress", command)
        self.assertNotIn("-vf", command)

    def test_image_command_uses_fast_preset(self):
        job = self._job(kind="image", codec="png", video_duration=None, fast=False)
        with patch("videobatch_fast.command_builder.ffmpeg_path", return_value="ffmpeg"):
            command = build_command(job, BatchOptions(Path("."), profile="fast"))
        self.assertIn("veryfast", command)
        self.assertIn("stillimage", command)
        self.assertIn("yuv420p", command)



    def test_effect_disables_direct_copy_and_uses_single_filter_chain(self):
        options = BatchOptions(Path("."), visual_effect="vivid", transition="soft")
        allowed, reason = can_use_fast_copy(self._job(), options)
        self.assertFalse(allowed)
        self.assertIn("Bildeffekt", reason)
        with patch("videobatch_fast.command_builder.ffmpeg_path", return_value="ffmpeg"):
            command = build_command(self._job(fast=False), options)
        self.assertIn("-vf", command)
        filter_chain = command[command.index("-vf") + 1]
        self.assertIn("eq=", filter_chain)
        self.assertIn("fade=t=in", filter_chain)
        self.assertIn("fade=t=out", filter_chain)
        self.assertEqual(command.count("-vf"), 1)

    def test_transition_only_disables_copy(self):
        options = BatchOptions(Path("."), transition="cinema")
        allowed, reason = can_use_fast_copy(self._job(), options)
        self.assertFalse(allowed)
        self.assertIn("Ein-/Ausblendung", reason)

    def test_effect_speed_summary_is_clear(self):
        self.assertIn("Direktkopie", speed_summary("none", "none"))
        self.assertIn("1-Pass", speed_summary("vignette", "soft"))

    def test_x265_image_command_avoids_unsupported_stillimage_tune(self):
        job = self._job(kind="image", codec="png", video_duration=None, fast=False)
        with patch("videobatch_fast.command_builder.ffmpeg_path", return_value="ffmpeg"):
            command = build_command(job, BatchOptions(Path("."), profile="fast", codec="libx265"))
        self.assertNotIn("stillimage", command)

    def test_short_video_uses_loop_when_encoding(self):
        job = self._job(video_duration=5.0, audio_duration=20.0, fast=False)
        with patch("videobatch_fast.command_builder.ffmpeg_path", return_value="ffmpeg"):
            command = build_command(job, BatchOptions(Path(".")))
        self.assertIn("-stream_loop", command)


class ConfigTests(unittest.TestCase):
    def test_config_normalizes_unknown_values(self):
        cfg = normalize_config({"profile": "slowest", "font_scale": 900, "codec": "bad"})
        self.assertEqual(cfg["profile"], "fast")
        self.assertEqual(cfg["font_scale"], 160)
        self.assertEqual(cfg["codec"], "libx264")
        cfg2 = normalize_config({"visual_effect": "unknown", "transition": "bad"})
        self.assertEqual(cfg2["visual_effect"], "none")
        self.assertEqual(cfg2["transition"], "none")


if __name__ == "__main__":
    unittest.main()
