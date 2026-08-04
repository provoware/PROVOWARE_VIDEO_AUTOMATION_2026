from __future__ import annotations

import base64
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from PIL import Image

from videobatch_fast.plugin_signing import quarantine_plugin, sign_plugin_directory, verify_plugin_signature
from videobatch_fast.plugins import validate_plugin
from videobatch_fast.registry import PROJECT_ROOT, load_json
from videobatch_fast.visual_regression import compare_visual, validate_reference_palette, validate_semantic_colors


def trust_for(private: Ed25519PrivateKey) -> dict:
    public_raw = private.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    return {
        "schema_version": 1,
        "policy": {"algorithm": "ed25519", "maximum_files": 128, "maximum_total_size": 5242880},
        "trusted_keys": {
            "test-key": {
                "algorithm": "ed25519",
                "public_key_base64": base64.b64encode(public_raw).decode("ascii"),
                "status": "active",
            }
        },
        "revoked_keys": [],
    }


class PluginSigningTests(unittest.TestCase):
    def _plugin(self, root: Path) -> None:
        (root / "plugin.json").write_text(json.dumps({"id": "signed", "api_version": 1, "capability": "validator"}), encoding="utf-8")
        (root / "plugin.py").write_text("def validate(payload):\n    return True\n", encoding="utf-8")

    def test_unsigned_plugin_is_blocked(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._plugin(root)
            self.assertFalse(validate_plugin(root).valid)

    def test_signed_plugin_is_accepted(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._plugin(root)
            private = Ed25519PrivateKey.generate()
            trust = trust_for(private)
            with patch("videobatch_fast.plugin_signing.load_json", return_value=trust):
                sign_plugin_directory(root, private, "test-key")
                check = verify_plugin_signature(root, trust)
                self.assertTrue(check.valid, check.message)
                self.assertTrue(validate_plugin(root).valid)

    def test_modified_plugin_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._plugin(root)
            private = Ed25519PrivateKey.generate()
            trust = trust_for(private)
            with patch("videobatch_fast.plugin_signing.load_json", return_value=trust):
                sign_plugin_directory(root, private, "test-key")
                (root / "plugin.py").write_text("def validate(payload):\n    return False\n", encoding="utf-8")
                check = verify_plugin_signature(root, trust)
                self.assertFalse(check.valid)
                self.assertIn("verändert", check.message)

    def test_quarantine_preserves_invalid_plugin_and_reason(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            plugin = base / "bad"
            plugin.mkdir()
            self._plugin(plugin)
            target = quarantine_plugin(plugin, "Signatur ungültig", base / "quarantine")
            self.assertFalse(plugin.exists())
            self.assertTrue((target / "plugin.py").is_file())
            self.assertIn("Signatur ungültig", (target / "QUARANTINE_REASON.txt").read_text())


class VisualRegressionTests(unittest.TestCase):
    def test_reference_palette_contract(self):
        self.assertEqual(validate_reference_palette(), [])

    def test_all_visual_baselines_exist(self):
        registry = load_json("registries/VISUAL_REGRESSION_REGISTRY.json")
        for scenario in registry["scenarios"]:
            baseline = PROJECT_ROOT / "tests" / "baselines" / f"{scenario['id']}.png"
            self.assertTrue(baseline.is_file(), baseline)
            required = scenario.get("required_semantic_colors", [])
            if required:
                self.assertEqual(validate_semantic_colors(baseline, expected_colors=required), [])

    def test_identical_image_comparison_passes(self):
        baseline = PROJECT_ROOT / "tests" / "baselines" / "dashboard_1280x720_100.png"
        result = compare_visual("same", baseline, baseline)
        self.assertTrue(result.passed)
        self.assertEqual(result.dhash_distance, 0)

    def test_clear_visual_change_is_detected(self):
        baseline = PROJECT_ROOT / "tests" / "baselines" / "dashboard_1280x720_100.png"
        with tempfile.TemporaryDirectory() as tmp:
            changed = Path(tmp) / "changed.png"
            with Image.open(baseline) as image:
                Image.new("RGB", image.size, "white").save(changed)
            result = compare_visual("changed", baseline, changed)
            self.assertFalse(result.passed)


if __name__ == "__main__":
    unittest.main()
