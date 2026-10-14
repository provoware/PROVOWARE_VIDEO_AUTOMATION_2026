"""Regression tests for dashboard selection precedence and safe serialization."""
import unittest
import tempfile
from pathlib import Path

from videobatch_fast.dashboard_settings import DashboardSettings, load_settings, save_settings


class DashboardSettingsTests(unittest.TestCase):
    def test_defaults_are_valid(self):
        self.assertEqual(DashboardSettings().quality, "balanced")

    def test_user_choices_survive_preset(self):
        settings = DashboardSettings().set_user_value("resolution", "Full HD")
        settings = settings.set_user_value("effect", "hardtechno")
        changed = settings.apply_preset({"resolution": "Original", "effect": "none", "quality": "Hoch"})
        self.assertEqual(changed.resolution, "Full HD")
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


if __name__ == "__main__":
    unittest.main()
