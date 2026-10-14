"""Regression tests for dashboard selection precedence and safe serialization."""
import unittest
from pathlib import Path

from videobatch_fast.dashboard_settings import DashboardSettings


class DashboardSettingsTests(unittest.TestCase):
    def test_defaults_are_valid(self):
        self.assertEqual(DashboardSettings().quality, "Ausgewogen")

    def test_user_choices_survive_preset(self):
        settings = DashboardSettings().set_user_value("resolution", "Full HD")
        settings = settings.set_user_value("effect", "hardtechno")
        changed = settings.apply_preset({"resolution": "Original", "effect": "none", "quality": "Hoch"})
        self.assertEqual(changed.resolution, "Full HD")
        self.assertEqual(changed.effect, "hardtechno")
        self.assertEqual(changed.quality, "Hoch")

    def test_nonexplicit_preset_may_change(self):
        state = DashboardSettings().apply_preset({"quality": "Schnell"})
        self.assertEqual(state.apply_preset({"quality": "Maximum"}).quality, "Maximum")

    def test_roundtrip(self):
        state = DashboardSettings().set_user_value("output_dir", "~/Videos/Test")
        self.assertEqual(DashboardSettings.from_dict(state.to_dict()), state)

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
