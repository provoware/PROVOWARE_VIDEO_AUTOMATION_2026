"""Regression tests for dashboard selection precedence and safe serialization."""
import unittest
import tempfile
from unittest.mock import patch
from pathlib import Path

from videobatch_fast.dashboard_settings import DashboardSettings, load_settings, save_settings


class DashboardSettingsTests(unittest.TestCase):
    def test_defaults_are_valid(self):
        self.assertEqual(DashboardSettings().quality, "balanced")

    def test_user_choices_survive_preset(self):
        settings = DashboardSettings().set_user_value("resolution", "Full HD")
        settings = settings.set_user_value("effect", "hardtechno")
        changed = settings.apply_preset({"resolution": "Original", "effect": "none", "quality": "Hoch"})
        self.assertEqual(changed.resolution, "1920×1080")
        self.assertEqual(changed.effect, "hardtechno")
        self.assertEqual(changed.quality, "quality")

    def test_nonexplicit_preset_may_change(self):
        state = DashboardSettings().apply_preset({"quality": "Schnell"})
        self.assertEqual(state.apply_preset({"quality": "Maximum"}).quality, "maximum")

    def test_roundtrip(self):
        state = DashboardSettings().set_user_value("output_dir", "~/Videos/Test")
        self.assertEqual(DashboardSettings.from_dict(state.to_dict()), state)

    def test_file_roundtrip_and_legacy_migration(self):
        state = DashboardSettings().set_user_value("resolution", "Full HD")
        self.assertEqual(state.resolution, "1920×1080")
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "config" / "settings.json"
            save_settings(state, target)
            self.assertEqual(load_settings(target), state)
        old = DashboardSettings.from_dict({"schema_version": 1, "quality": "Hoch", "resolution": "HD"})
        self.assertEqual((old.quality, old.resolution), ("quality", "1280×720"))

    def test_corrupt_settings_are_rejected_not_silently_rewritten(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "broken.json"
            target.write_text("{defekt", encoding="utf-8")
            with self.assertRaises(ValueError):
                load_settings(target)
            self.assertEqual(target.read_text(encoding="utf-8"), "{defekt")

    def test_failed_write_preserves_previous_settings(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "config" / "settings.json"
            saved = DashboardSettings().set_user_value("resolution", "HD")
            save_settings(saved, target)
            before = target.read_bytes()
            with patch("videobatch_fast.dashboard_settings.atomic_write_json", side_effect=OSError("voll")):
                with self.assertRaises(OSError):
                    save_settings(DashboardSettings().set_user_value("quality", "Maximum"), target)
            self.assertEqual(target.read_bytes(), before)
            self.assertEqual(load_settings(target), saved)

    def test_persistence_uses_shared_atomic_writer(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "settings.json"
            state = DashboardSettings()
            with patch("videobatch_fast.dashboard_settings.atomic_write_json") as writer:
                save_settings(state, target)
            writer.assert_called_once_with(target, state.to_dict())

    def test_unknown_and_invalid_values_rejected(self):
        with self.assertRaises(ValueError):
            DashboardSettings().set_user_value("codec", "h265")
        with self.assertRaises(ValueError):
            DashboardSettings().set_user_value("resolution", "nicht vorhanden")
        with self.assertRaises(ValueError):
            DashboardSettings().apply_preset({"secret_option": True})
        with self.assertRaises(ValueError):
            DashboardSettings.from_dict({"schema_version": 99})
        with self.assertRaises(ValueError):
            DashboardSettings.from_dict({"explicit_fields": "resolution"})

    def test_strength_and_fade_roundtrip_and_invalid_numbers(self):
        state = DashboardSettings().set_user_value("effect_intensity", 75)
        state = state.set_user_value("transition", "cinema")
        state = state.set_user_value("transition_duration", 4.2)
        self.assertEqual((state.effect_intensity, state.transition, state.transition_duration),
                         (75, "cinema", 4.2))
        self.assertEqual(DashboardSettings.from_dict(state.to_dict()), state)
        old = DashboardSettings.from_dict({"schema_version": 1, "quality": "Hoch"})
        self.assertEqual(old.effect_intensity, 100)
        self.assertEqual(old.transition, "none")
        for field, value in (
            ("effect_intensity", -1), ("effect_intensity", 101),
            ("effect_intensity", True), ("effect_intensity", 50.5),
            ("transition_duration", -0.1), ("transition_duration", 6),
            ("transition_duration", float("nan")),
        ):
            with self.subTest(field=field, value=value):
                with self.assertRaises(ValueError):
                    state.set_user_value(field, value)


if __name__ == "__main__":
    unittest.main()
