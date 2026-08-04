from __future__ import annotations

import unittest

from videobatch_fast.plugin_permissions import permission_summary
from videobatch_fast.project_state import normalize_project_state
from videobatch_fast.registry import PROJECT_ROOT, load_json, validate_registries


class CalendarNoteContractTests(unittest.TestCase):
    def test_calendar_note_roundtrip_is_normalized(self):
        state = normalize_project_state({
            "calendar_marks": {"2026-08-02": "warning"},
            "calendar_notes": {
                "2026-08-02": {"note": "Release prüfen", "entry_type": "deadline", "color": "warning"}
            },
        })
        self.assertEqual(state["schema_version"], 3)
        self.assertEqual(state["calendar_notes"]["2026-08-02"]["note"], "Release prüfen")
        self.assertEqual(state["calendar_notes"]["2026-08-02"]["entry_type"], "deadline")
        self.assertEqual(state["calendar_marks"]["2026-08-02"], "warning")

    def test_invalid_calendar_note_values_are_safely_normalized(self):
        state = normalize_project_state({
            "calendar_notes": {
                "2026-08-03": {"note": "x" * 800, "entry_type": "shell", "color": "pink"}
            }
        })
        entry = state["calendar_notes"]["2026-08-03"]
        self.assertEqual(len(entry["note"]), 500)
        self.assertEqual(entry["entry_type"], "note")
        self.assertEqual(entry["color"], "none")


class PluginPermissionTests(unittest.TestCase):
    def test_every_capability_has_plain_permission_profile(self):
        registry = load_json("registries/PLUGIN_REGISTRY.json")
        profiles = registry["permission_profiles"]
        for capability in registry["allowed_capabilities"]:
            self.assertIn(capability, profiles)
            summary = permission_summary(capability, "videobatch-official-2026")
            plain = summary.plain_text("demo", "videobatch-official-2026")
            self.assertTrue(summary.file_access)
            self.assertTrue(summary.actions)
            self.assertTrue(summary.prohibited)
            self.assertIn("Darf auf folgende Daten zugreifen", plain)
            self.assertIn("Bleibt ausdrücklich verboten", plain)
            self.assertNotEqual(summary.risk_level, "unbekannt")


class WorkspaceVisualRegistryTests(unittest.TestCase):
    def test_workspace_reference_scenarios_are_registered(self):
        registry = load_json("registries/VISUAL_REGRESSION_REGISTRY.json")
        workspace = [item for item in registry["scenarios"] if item.get("page") == "workspace"]
        self.assertTrue({"files", "preview", "playlist", "monitor", "debug_machine"}.issubset({item["state"] for item in workspace}))
        for item in workspace:
            self.assertTrue(item["required_visible_texts"])

    def test_all_eight_baselines_exist(self):
        registry = load_json("registries/VISUAL_REGRESSION_REGISTRY.json")
        self.assertGreaterEqual(len(registry["scenarios"]), 8)
        for scenario in registry["scenarios"]:
            path = PROJECT_ROOT / "tests" / "baselines" / f"{scenario['id']}.png"
            self.assertTrue(path.is_file(), path)

    def test_registries_remain_consistent(self):
        self.assertEqual(validate_registries(), [])


if __name__ == "__main__":
    unittest.main()
