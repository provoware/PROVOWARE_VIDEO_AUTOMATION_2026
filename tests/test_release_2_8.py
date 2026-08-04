from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from videobatch_fast.diagnostics_service import write_diagnostic_report
from videobatch_fast.plugin_approval_manager import PluginApprovalRow, filter_approval_rows, synchronize_plugin_approvals
from videobatch_fast.plugin_approvals import build_identity, grant_approval
from videobatch_fast.plugin_permissions import permission_summary
from videobatch_fast.plugins import PluginCheck
from videobatch_fast.registry import load_json, validate_registries
from videobatch_fast.versioning import build_label
from videobatch_fast.visual_approval import sign_visual_approval, verify_visual_approval
from videobatch_fast.visual_inspection import write_inspection_html, write_inspection_manifest


class PluginApprovalManagerTests(unittest.TestCase):
    def test_filter_supports_status_search_and_hash(self):
        rows = [
            PluginApprovalRow("alpha", "active", "1.0", "a" * 64, "validator", "Provoware", "2026", "2026", "ok", True),
            PluginApprovalRow("beta", "revoked", "2.0", "b" * 64, "exporter", "Andere", "2025", "2026", "widerrufen", False),
        ]
        self.assertEqual([row.plugin_id for row in filter_approval_rows(rows, "aaaa", "active")], ["alpha"])
        self.assertEqual([row.plugin_id for row in filter_approval_rows(rows, "andere", "all")], ["beta"])

    def test_opening_management_synchronizes_and_expires_changed_plugin(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "approvals.json"
            permissions = permission_summary("validator", "")
            identity = build_identity(
                plugin_id="demo",
                version="1.0.0",
                payload_sha256="a" * 64,
                key_id="",
                capability="validator",
                permissions=permissions,
            )
            grant_approval(identity, permissions, path)
            original = PluginCheck(Path(tmp), True, "demo", "ok", True, "", "validator", "", "1.0.0", "a" * 64)
            self.assertEqual(synchronize_plugin_approvals(path, [original])[0].status, "active")
            changed = PluginCheck(Path(tmp), True, "demo", "ok", True, "", "validator", "", "1.0.1", "b" * 64)
            self.assertEqual(synchronize_plugin_approvals(path, [changed])[0].status, "expired")


class VisualApprovalTests(unittest.TestCase):
    def _fixture(self, root: Path) -> Path:
        baseline = root / "tests" / "baselines" / "one.png"
        baseline.parent.mkdir(parents=True)
        baseline.write_bytes(b"baseline-image")
        report = root / "diagnostics" / "visual_regression_latest.json"
        report.parent.mkdir(parents=True)
        report.write_text(json.dumps({"results": [{"scenario_id": "one", "passed": True}]}), encoding="utf-8")
        manifest = {
            "schema_version": 1,
            "id": "visual",
            "version": "2.8.0",
            "passed": True,
            "summary": {"scenario_count": 1, "passed_count": 1, "failed_count": 0, "contract_error_count": 0},
            "links": {"visual_report": "diagnostics/visual_regression_latest.json"},
            "scenarios": [{"id": "one", "baseline": "tests/baselines/one.png", "passed": True}],
        }
        target = root / "VISUAL_INSPECTION_MANIFEST.json"
        target.write_text(json.dumps(manifest), encoding="utf-8")
        return target

    def test_sign_verify_and_invalidate_visual_approval(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest_path = self._fixture(root)
            approval = sign_visual_approval(
                manifest_path,
                reviewer="Testprüfer",
                build_id="2.8.0",
                project_root=root,
                key_dir=root / "keys",
            )
            self.assertEqual(approval["payload"]["reviewer"], "Testprüfer")
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertTrue(verify_visual_approval(manifest, root).valid)
            private_key = root / "keys" / "desktop_approval_ed25519_private.pem"
            self.assertEqual(private_key.stat().st_mode & 0o777, 0o600)
            (root / "tests" / "baselines" / "one.png").write_bytes(b"changed")
            self.assertEqual(verify_visual_approval(manifest, root).status, "expired")


    def test_rebuilding_identical_manifest_preserves_valid_approval(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest_path = self._fixture(root)
            sign_visual_approval(manifest_path, reviewer="Prüfer", build_id="2.8.0", project_root=root, key_dir=root / "keys")
            signed = json.loads(manifest_path.read_text(encoding="utf-8"))
            signed["generated_at"] = "old"
            manifest_path.write_text(json.dumps(signed), encoding="utf-8")
            # Die echte Buildfunktion wird hier isoliert ersetzt, damit nur
            # der Erhalt des Abnahmevermerks geprüft wird.
            from unittest.mock import patch
            rebuilt = {key: value for key, value in signed.items() if key not in {"manual_approval", "generated_at"}}
            rebuilt["generated_at"] = "new"
            with patch("videobatch_fast.visual_inspection.build_inspection_manifest", return_value=rebuilt):
                write_inspection_manifest(manifest_path, root)
            result = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertIn("manual_approval", result)
            self.assertTrue(verify_visual_approval(result, root).valid)

    def test_html_shows_manual_approval_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest_path = self._fixture(root)
            sign_visual_approval(manifest_path, reviewer="Prüfer", build_id="2.8.0", project_root=root, key_dir=root / "keys")
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            html_path = root / "visual_inspection" / "index.html"
            write_inspection_html(html_path, manifest)
            content = html_path.read_text(encoding="utf-8")
            self.assertIn("Desktop-Freigabe signiert", content)
            self.assertIn("Prüfer", content)


class DebugAndArchitectureTests(unittest.TestCase):
    def test_diagnostic_report_is_private_and_structured(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project = root / "project.json"; project.write_text("{}")
            human = root / "human.log"; human.write_text("ok")
            machine = root / "machine.jsonl"; machine.write_text("{}\n")
            from unittest.mock import patch
            with patch("videobatch_fast.diagnostics_service.state_dir", return_value=root / "state"):
                report = write_diagnostic_report(session_id="abc", project_file=project, human_log=human, machine_log=machine)
            payload = json.loads(report.read_text(encoding="utf-8"))
            self.assertEqual(payload["tool"], "provoware - videoautomation - 2026")
            self.assertEqual(report.stat().st_mode & 0o777, 0o600)

    def test_new_registries_and_version_are_consistent(self):
        self.assertEqual(validate_registries(), [])
        approval = load_json("registries/VISUAL_APPROVAL_REGISTRY.json")
        self.assertTrue(approval["rules"]["signature_invalidates_on_baseline_change"])
        self.assertEqual(build_label(), load_json("VERSION.json")["build"])

    def test_workspace_contract_is_registered_in_source(self):
        root = Path(__file__).parents[1] / "src" / "videobatch_fast"
        source = (root / "ui_workspace_grid_mixin.py").read_text(encoding="utf-8")
        self.assertIn("ui.workspace_grid.mittiger_hauptarbeitsbereich_flexibles_22_raster", source)
        texts = json.loads((Path(__file__).parents[1] / "resources" / "texts" / "de.json").read_text(encoding="utf-8"))
        self.assertTrue(any("flexibles 2×2-Raster" in value for value in texts.values() if isinstance(value, str)))
        self.assertIn("Profi-Debugging & Profilogging", texts.values())


if __name__ == "__main__":
    unittest.main()
