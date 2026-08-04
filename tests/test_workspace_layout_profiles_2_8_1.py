from __future__ import annotations

import copy
import unittest

from videobatch_fast.layout_profiles import (
    contract_version,
    display_profile_key,
    empty_layout_store,
    normalize_layout_store,
    resolve_layout_profile,
    tested_default_ratios as default_ratios,
    update_layout_profile,
    validate_ratios,
)
from videobatch_fast.project_state import normalize_project_state


DIMENSIONS = {
    "root_vertical": 700,
    "grid_vertical": 520,
    "top_horizontal": 1200,
    "bottom_horizontal": 1200,
}


class WorkspaceLayoutProfileTests(unittest.TestCase):
    def test_profile_key_separates_resolution_and_zoom(self):
        self.assertNotEqual(display_profile_key(1920, 1080, 100), display_profile_key(1920, 1080, 140))
        self.assertNotEqual(display_profile_key(1920, 1080, 100), display_profile_key(1366, 768, 100))

    def test_zoom_gets_separate_profile_with_same_tested_defaults(self):
        normal = default_ratios(1920, 1080, 100)
        zoomed = default_ratios(1920, 1080, 160)
        self.assertEqual(zoomed, normal)
        self.assertNotEqual(display_profile_key(1920, 1080, 100), display_profile_key(1920, 1080, 160))

    def test_valid_profile_roundtrip_is_restored(self):
        saved = update_layout_profile(
            empty_layout_store(),
            screen_width=1920,
            screen_height=1080,
            ui_zoom=100,
            ratios={
                "root_vertical": 0.74,
                "grid_vertical": 0.46,
                "top_horizontal": 0.44,
                "bottom_horizontal": 0.56,
            },
            dimensions=DIMENSIONS,
        )
        self.assertEqual(saved.status, "saved")
        restored = resolve_layout_profile(
            saved.store,
            screen_width=1920,
            screen_height=1080,
            ui_zoom=100,
            dimensions=DIMENSIONS,
        )
        self.assertEqual(restored.status, "restored")
        self.assertAlmostEqual(restored.ratios["top_horizontal"], 0.44, places=5)

    def test_invalid_collapsed_profile_is_self_healed(self):
        store = empty_layout_store()
        key = display_profile_key(1920, 1080, 100)
        store["profiles"][key] = {
            "screen_width": 1920,
            "screen_height": 1080,
            "ui_zoom": 100,
            "contract_version": contract_version(),
            "ratios": {
                "root_vertical": 0.99,
                "grid_vertical": 0.01,
                "top_horizontal": 0.95,
                "bottom_horizontal": 0.05,
            },
            "updated_at": "2026-08-02T00:00:00+0200",
            "source": "user",
        }
        result = resolve_layout_profile(
            store,
            screen_width=1920,
            screen_height=1080,
            ui_zoom=100,
            dimensions=DIMENSIONS,
        )
        self.assertEqual(result.status, "healed")
        valid, _reason = validate_ratios(result.ratios, DIMENSIONS)
        self.assertTrue(valid)
        self.assertIn("Unbrauchbarer Rasterzustand", result.reason)

    def test_contract_change_expires_old_profile(self):
        store = empty_layout_store()
        key = display_profile_key(1366, 768, 100)
        store["profiles"][key] = {
            "screen_width": 1366,
            "screen_height": 768,
            "ui_zoom": 100,
            "contract_version": "old-contract",
            "ratios": default_ratios(1366, 768, 100),
            "updated_at": "2026-08-02T00:00:00+0200",
            "source": "user",
        }
        result = resolve_layout_profile(
            store,
            screen_width=1366,
            screen_height=768,
            ui_zoom=100,
            dimensions=DIMENSIONS,
        )
        self.assertEqual(result.status, "healed")
        self.assertIn("veraltet", result.reason)
        self.assertEqual(result.store["profiles"][key]["contract_version"], contract_version())

    def test_malformed_profiles_are_removed_during_normalization(self):
        store = {
            "schema_version": 999,
            "profiles": {
                "wrong-key": {"screen_width": 1920, "screen_height": 1080, "ui_zoom": 100, "ratios": {}},
                "1920x1080@100": {"screen_width": 1920, "screen_height": 1080, "ui_zoom": 100, "ratios": {"root_vertical": "bad"}},
            },
        }
        normalized = normalize_layout_store(store)
        self.assertEqual(normalized["profiles"], {})

    def test_project_state_migrates_and_preserves_layout_store(self):
        saved = update_layout_profile(
            empty_layout_store(),
            screen_width=2560,
            screen_height=1440,
            ui_zoom=140,
            ratios=default_ratios(2560, 1440, 140),
            dimensions=DIMENSIONS,
        )
        state = normalize_project_state({"workspace_layout_profiles": copy.deepcopy(saved.store)})
        self.assertEqual(state["schema_version"], 3)
        self.assertIn(display_profile_key(2560, 1440, 140), state["workspace_layout_profiles"]["profiles"])


if __name__ == "__main__":
    unittest.main()
