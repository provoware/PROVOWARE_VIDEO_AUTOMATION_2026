from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from videobatch_fast.config import normalize_config
from videobatch_fast.plugin_runtime import run_plugin_in_sandbox
from videobatch_fast.os_sandbox import probe_sandbox_support
from videobatch_fast.project_state import default_project_file, load_project_state, save_project_state
from videobatch_fast.registry import load_json, validate_registries


class ProjectStateTests(unittest.TestCase):
    def test_default_project_file_is_inside_state_projects(self):
        self.assertIn("projects", str(default_project_file()))
        self.assertTrue(str(default_project_file()).endswith(".vbfast.json"))

    def test_project_state_save_and_load_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "demo.vbfast.json"
            save_project_state(target, {
                "project_name": "Demo",
                "quick_note": "Merker",
                "audio_paths": ["/tmp/a.wav"],
                "calendar_marks": {"2026-08-02": "success"},
            })
            path, state, healed = load_project_state(target)
            self.assertEqual(path, target)
            self.assertFalse(healed)
            self.assertEqual(state["project_name"], "Demo")
            self.assertEqual(state["quick_note"], "Merker")
            self.assertEqual(state["calendar_marks"]["2026-08-02"], "success")

    def test_corrupt_project_state_is_quarantined_and_healed(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "broken.vbfast.json"
            target.write_text("{broken", encoding="utf-8")
            path, state, healed = load_project_state(target)
            self.assertEqual(path, target)
            self.assertTrue(healed)
            self.assertEqual(state["project_name"], "Neues Projekt")
            self.assertTrue(list(Path(tmp).glob("broken.vbfast.corrupt.*.json")))


class ConfigAndBlueprintTests(unittest.TestCase):
    def test_config_tracks_current_project_file(self):
        result = normalize_config({"current_project_file": "~/x/demo.vbfast.json"})
        self.assertTrue(result["current_project_file"].endswith("demo.vbfast.json"))

    def test_ui_blueprint_is_registered_and_structured(self):
        blueprint = load_json("registries/UI_BLUEPRINT.json")
        self.assertEqual(blueprint["name"], "Laienmodus Einfach")
        self.assertEqual(len(blueprint["action_tiles"]), 4)
        self.assertIn("header", blueprint["layout"])
        self.assertEqual(validate_registries(), [])


class PluginSandboxTests(unittest.TestCase):
    def test_validator_plugin_runs_in_subprocess(self):
        with tempfile.TemporaryDirectory() as tmp:
            plugin_dir = Path(tmp)
            (plugin_dir / "plugin.json").write_text(json.dumps({"id": "ok", "api_version": 1, "capability": "validator"}), encoding="utf-8")
            (plugin_dir / "plugin.py").write_text("def validate(payload):\n    return payload.get('probe') is True\n", encoding="utf-8")
            result = run_plugin_in_sandbox(plugin_dir, "validator", {"probe": True})
            if not probe_sandbox_support().available:
                self.assertFalse(result.success)
                self.assertIn("blockiert", result.message.lower())
                return
            self.assertTrue(result.success, result.message)
            self.assertTrue(result.result)


if __name__ == "__main__":
    unittest.main()
