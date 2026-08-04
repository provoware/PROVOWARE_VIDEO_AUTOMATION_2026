from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

from videobatch_fast.command_builder import PROFILES, build_command, can_use_fast_copy
from videobatch_fast.config import normalize_config
from videobatch_fast.effects import TRANSITIONS, VISUAL_EFFECTS
from videobatch_fast.models import BatchOptions, MediaInfo, PairJob
from videobatch_fast.quick_modes import (
    QUICK_MODES,
    automatic_mode_keys,
    fallback_options,
    processing_options_for_job,
    quick_mode_summary,
    validate_quick_modes,
)


class QuickModeContractTests(unittest.TestCase):
    def _job(self, kind: str = "video", codec: str = "h264") -> PairJob:
        audio = Path("track.wav")
        media = Path("media.mp4" if kind == "video" else "cover.png")
        return PairJob(
            1,
            audio,
            media,
            Path("out.mp4"),
            MediaInfo(audio, "audio", 10.0, "pcm_s16le"),
            MediaInfo(media, kind, 12.0 if kind == "video" else None, codec),
            False,
            "test",
        )

    def test_at_least_ten_automatic_modes_exist(self):
        self.assertGreaterEqual(len(automatic_mode_keys()), 10)
        self.assertIn("smart_auto", automatic_mode_keys())
        self.assertIn("hardtechno_impact", automatic_mode_keys())

    def test_registry_is_complete_and_consistent(self):
        self.assertEqual(validate_quick_modes(VISUAL_EFFECTS, TRANSITIONS, PROFILES), [])
        for key in automatic_mode_keys():
            spec = QUICK_MODES[key]
            self.assertTrue(spec.description)
            self.assertIn(spec.visual_effect, VISUAL_EFFECTS)
            self.assertIn(spec.transition, TRANSITIONS)
            self.assertIn(spec.profile, PROFILES)
            self.assertIn(spec.fallback_mode, QUICK_MODES)

    def test_smart_auto_keeps_video_copy_and_styles_images(self):
        video = self._job("video")
        image = self._job("image", "png")
        options = BatchOptions(Path("."), quick_mode="smart_auto")
        video_options = processing_options_for_job(video, options)
        image_options = processing_options_for_job(image, options)
        self.assertEqual((video_options.visual_effect, video_options.transition), ("none", "none"))
        self.assertNotEqual(image_options.visual_effect, "none")
        allowed, _ = can_use_fast_copy(video, options)
        self.assertTrue(allowed)

    def test_effect_modes_use_one_filter_chain(self):
        job = self._job("image", "png")
        for key in automatic_mode_keys():
            options = BatchOptions(Path("."), quick_mode=key)
            with patch("videobatch_fast.command_builder.ffmpeg_path", return_value="ffmpeg"):
                command = build_command(job, options)
            self.assertLessEqual(command.count("-vf"), 1, key)
            self.assertIn("-progress", command)

    def test_every_nontrivial_mode_has_safe_fallback(self):
        for key in automatic_mode_keys():
            options = BatchOptions(Path("."), quick_mode=key)
            fallback = fallback_options(options)
            if key == "maximum_speed":
                self.assertIsNone(fallback)
            else:
                self.assertIsNotNone(fallback, key)
                self.assertEqual(fallback.quick_mode, "maximum_speed")

    def test_config_normalizes_mode(self):
        self.assertEqual(normalize_config({"quick_mode": "bad"})["quick_mode"], "smart_auto")
        self.assertEqual(normalize_config({"quick_mode": "acid_neon"})["quick_mode"], "acid_neon")

    def test_summary_uses_simple_language(self):
        summary = quick_mode_summary("hardtechno_impact")
        self.assertIn("HardTechno", summary)
        self.assertIn("automatische sichere Einstellungen", summary)

    def test_ui_exposes_mode_tiles_and_automatic_start(self):
        source = (Path(__file__).parents[1] / "src" / "videobatch_fast" / "ui.py").read_text(encoding="utf-8")
        self.assertIn("QuickMode.TButton", source)
        self.assertIn("Automatisch prüfen und Videos erstellen", source)
        self.assertIn("Schnellmodi", source)


class AutomaticFallbackTests(unittest.TestCase):
    def test_failed_effect_gets_exactly_one_safe_fallback(self):
        from videobatch_fast.models import JobResult
        from videobatch_fast.runner import BatchRunner

        audio = Path("track.wav")
        image = Path("cover.png")
        output = Path("out.mp4")
        job = PairJob(
            1, audio, image, output,
            MediaInfo(audio, "audio", 10.0, "pcm_s16le"),
            MediaInfo(image, "image", None, "png"),
            False, "test",
        )
        runner = BatchRunner(lambda *_args: None)
        calls = []

        def fake_execute(command, current_job, position, total):
            calls.append(command)
            return JobResult(current_job, len(calls) == 2, 1 if len(calls) == 1 else 0, 0.1, "first failed" if len(calls) == 1 else "ok", command=command)

        with patch.object(runner, "_execute", side_effect=fake_execute), patch("videobatch_fast.runner.verify_output", return_value=(True, "gültig")):
            result = runner._run_job(job, 1, 1, BatchOptions(Path("."), quick_mode="hardtechno_impact"))
        self.assertEqual(len(calls), 2)
        self.assertTrue(result.success)
        self.assertEqual(result.fallback_mode, "Maximale Geschwindigkeit")



if __name__ == "__main__":
    unittest.main()
