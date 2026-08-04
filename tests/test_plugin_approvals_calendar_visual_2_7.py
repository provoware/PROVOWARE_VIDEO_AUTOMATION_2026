from __future__ import annotations

import json
import tempfile
import unittest
from dataclasses import replace
from datetime import date
from pathlib import Path

from videobatch_fast.calendar_tasks import collect_calendar_tasks, filter_calendar_tasks
from videobatch_fast.plugin_approvals import (
    build_identity,
    grant_approval,
    load_approvals,
    revoke_approval,
    validate_approval,
)
from videobatch_fast.plugin_permissions import PluginPermissionSummary
from videobatch_fast.registry import load_json, validate_registries
from videobatch_fast.visual_inspection import build_inspection_manifest, write_inspection_html, write_inspection_manifest


PERMISSIONS = PluginPermissionSummary(
    capability="validator",
    title="Prüf-Plugin",
    purpose="Prüft Daten.",
    file_access=("Metadaten",),
    actions=("Validieren",),
    prohibited=("Netzwerk",),
    risk_level="niedrig",
    publisher="Test",
)


class PluginApprovalTests(unittest.TestCase):
    def test_approval_roundtrip_and_revoke(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "approvals.json"
            identity = build_identity(plugin_id="demo", version="1.0.0", payload_sha256="a" * 64, key_id="key", capability="validator", permissions=PERMISSIONS)
            record = grant_approval(identity, PERMISSIONS, path)
            self.assertEqual(record["status"], "active")
            self.assertTrue(validate_approval(identity, path).valid)
            revoked = revoke_approval("demo", path=path)
            self.assertEqual(revoked.status, "revoked")
            self.assertFalse(validate_approval(identity, path).valid)

    def test_plugin_change_expires_approval_automatically(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "approvals.json"
            original = build_identity(plugin_id="demo", version="1.0.0", payload_sha256="a" * 64, key_id="key", capability="validator", permissions=PERMISSIONS)
            grant_approval(original, PERMISSIONS, path)
            changed = build_identity(plugin_id="demo", version="1.0.1", payload_sha256="b" * 64, key_id="key", capability="validator", permissions=PERMISSIONS)
            status = validate_approval(changed, path)
            self.assertEqual(status.status, "expired")
            stored = load_approvals(path)["approvals"]["demo"]
            self.assertEqual(stored["status"], "expired")
            self.assertIn("geändert", stored["reason"])

    def test_permission_change_expires_approval(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "approvals.json"
            original = build_identity(plugin_id="demo", version="1.0.0", payload_sha256="a" * 64, key_id="key", capability="validator", permissions=PERMISSIONS)
            grant_approval(original, PERMISSIONS, path)
            changed_permissions = replace(PERMISSIONS, actions=("Validieren", "Exportieren"))
            changed = build_identity(plugin_id="demo", version="1.0.0", payload_sha256="a" * 64, key_id="key", capability="validator", permissions=changed_permissions)
            self.assertEqual(validate_approval(changed, path).status, "expired")


class CalendarTaskTests(unittest.TestCase):
    def setUp(self):
        self.notes = {
            "2026-08-02": {"note": "Heute prüfen", "entry_type": "task", "color": "active"},
            "2026-08-05": {"note": "Termin", "entry_type": "deadline", "color": "info"},
            "2026-09-01": {"note": "Später", "entry_type": "reminder", "color": "warning"},
            "invalid": {"note": "Ignorieren", "entry_type": "note", "color": "none"},
        }

    def test_collect_is_sorted_and_invalid_dates_are_ignored(self):
        tasks = collect_calendar_tasks(self.notes)
        self.assertEqual([item.date_key for item in tasks], ["2026-08-02", "2026-08-05", "2026-09-01"])

    def test_day_week_month_and_type_filters(self):
        tasks = collect_calendar_tasks(self.notes)
        today = date(2026, 8, 2)
        self.assertEqual(len(filter_calendar_tasks(tasks, "today", today)), 1)
        self.assertEqual(len(filter_calendar_tasks(tasks, "week", today)), 2)
        self.assertEqual(len(filter_calendar_tasks(tasks, "month", today)), 2)
        self.assertEqual(len(filter_calendar_tasks(tasks, "tasks", today)), 1)
        self.assertEqual(len(filter_calendar_tasks(tasks, "appointments", today)), 1)


class VisualInspectionTests(unittest.TestCase):
    def test_visual_regression_has_dialog_scenarios(self):
        registry = load_json("registries/VISUAL_REGRESSION_REGISTRY.json")
        dialogs = [item for item in registry["scenarios"] if item.get("group") == "dialogs"]
        self.assertGreaterEqual(len(dialogs), 6)
        self.assertTrue({"update", "archive", "plugin", "recovery", "approval_manager", "visual_approval"}.issubset({item["state"] for item in dialogs}))

    def test_html_and_manifest_are_linked(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            # Build from project registry/report, write into temporary output.
            manifest_target = root / "VISUAL_INSPECTION_MANIFEST.json"
            write_inspection_manifest(manifest_target)
            manifest = json.loads(manifest_target.read_text(encoding="utf-8"))
            html_target = root / "visual_inspection" / "index.html"
            write_inspection_html(html_target, manifest)
            content = html_target.read_text(encoding="utf-8")
            self.assertIn("VISUAL_INSPECTION_MANIFEST.json", content)
            self.assertIn("manifest-data", content)
            self.assertIn("dialog_plugin_permissions", content)

    def test_new_registry_is_valid(self):
        self.assertEqual(validate_registries(), [])
        config = load_json("registries/VISUAL_INSPECTION_REGISTRY.json")
        self.assertTrue(config["rules"]["offline_first"])


if __name__ == "__main__":
    unittest.main()
