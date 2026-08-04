from __future__ import annotations

import base64
import hashlib
import json
import os
import subprocess
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from videobatch_fast.archive_service import append_manifest, archive_file, used_name
from videobatch_fast.assurance import run_scenarios
from videobatch_fast.config import load_config, normalize_config
from videobatch_fast.event_logging import EventLogger, safe_text
from videobatch_fast.media_library import SORT_KEYS, sort_paths
from videobatch_fast.plugin_signing import sign_plugin_directory
from videobatch_fast.plugins import validate_plugin
from videobatch_fast.preview_service import build_preview
from videobatch_fast.registry import load_json, validate_registries
from videobatch_fast.updates import apply_update_package, validate_update_package


class RegistryAndTextTests(unittest.TestCase):
    def test_all_global_registries_are_valid(self):
        self.assertEqual(validate_registries(), [])

    def test_error_registry_has_solution_and_actions(self):
        errors = load_json("registries/ERROR_REGISTRY.json")["errors"]
        self.assertGreaterEqual(len(errors), 8)
        for item in errors.values():
            self.assertTrue(item["solution"])
            self.assertTrue(item["alternative"])
            self.assertTrue(item["actions"])

    def test_function_registry_links_tests(self):
        functions = load_json("registries/FUNCTION_REGISTRY.json")["functions"]
        self.assertGreaterEqual(len(functions), 8)
        self.assertTrue(all(item["tests"] for item in functions))


class ConfigAndLoggingTests(unittest.TestCase):
    def test_new_config_fields_are_normalized(self):
        result = normalize_config({"audio_sort": "bad", "preview_zoom": 9000, "archive_suffix": "unsafe"})
        self.assertEqual(result["audio_sort"], "import")
        self.assertEqual(result["preview_zoom"], 800)
        self.assertEqual(result["archive_suffix"], "__verwendet")
        self.assertEqual(result["schema_version"], 3)


    def test_corrupt_config_is_quarantined_and_healed(self):
        with tempfile.TemporaryDirectory() as tmp, patch("videobatch_fast.config.config_file", return_value=Path(tmp) / "config.json"):
            path = Path(tmp) / "config.json"
            path.write_text("{broken", encoding="utf-8")
            result = load_config()
            self.assertEqual(result["schema_version"], 3)
            self.assertTrue(path.is_file())
            self.assertTrue(list(Path(tmp).glob("config.corrupt.*.json")))

    def test_safe_text_redacts_home_ansi_and_secrets(self):
        value = safe_text(f"\x1b[31m{Path.home()}/x token=abc\x1b[0m")
        self.assertNotIn(str(Path.home()), value)
        self.assertNotIn("abc", value)
        self.assertNotIn("\x1b", value)

    def test_event_logger_writes_structured_and_human_logs(self):
        with tempfile.TemporaryDirectory() as tmp, patch("videobatch_fast.event_logging.state_dir", return_value=Path(tmp)):
            logger = EventLogger("sessiontest")
            record = logger.write("TEST_EVENT", "Test", "Meldung", solution="Lösung", level="success")
            self.assertEqual(record.event_id, "TEST_EVENT")
            self.assertTrue(logger.jsonl_path.is_file())
            self.assertTrue(logger.human_path.is_file())
            payload = json.loads(logger.jsonl_path.read_text().splitlines()[0])
            self.assertEqual(payload["solution"], "Lösung")


class MediaSortingTests(unittest.TestCase):
    def test_all_sort_modes_are_registered(self):
        self.assertGreaterEqual(len(SORT_KEYS), 10)

    def test_sorting_changes_view_not_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            a = Path(tmp) / "b.wav"; b = Path(tmp) / "a.wav"
            a.write_bytes(b"1"); b.write_bytes(b"22")
            original = [a, b]
            view = sort_paths(original, "name_asc")
            self.assertEqual([p.name for p in view], ["a.wav", "b.wav"])
            self.assertEqual([p.name for p in original], ["b.wav", "a.wav"])

    def test_size_sort_is_stable(self):
        with tempfile.TemporaryDirectory() as tmp:
            a = Path(tmp) / "a.wav"; b = Path(tmp) / "b.wav"
            a.write_bytes(b"x"); b.write_bytes(b"x")
            self.assertEqual(sort_paths([b, a], "size_asc"), [b, a])


class ArchiveTests(unittest.TestCase):
    def test_used_name_never_duplicates_suffix(self):
        self.assertEqual(used_name(Path("track__verwendet.wav")), "track__verwendet.wav")
        self.assertEqual(used_name(Path("track.wav")), "track__verwendet.wav")

    def test_same_device_move_is_verified_and_manifested(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "song.wav"
            source.write_bytes(b"audio-data")
            record = archive_file(source, root / "project", "audio")
            self.assertFalse(source.exists())
            target = Path(record.target)
            self.assertTrue(target.is_file())
            manifest = append_manifest(root / "project", [record])
            payload = json.loads(manifest.read_text())
            self.assertEqual(payload["records"][0]["status"], "moved")

    def test_collision_gets_unique_target(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project = root / "project"
            first = root / "track.wav"; first.write_bytes(b"1")
            second_dir = root / "other"; second_dir.mkdir()
            second = second_dir / "track.wav"; second.write_bytes(b"2")
            one = archive_file(first, project, "audio")
            two = archive_file(second, project, "audio")
            self.assertNotEqual(one.target, two.target)


class PluginAndUpdateTests(unittest.TestCase):
    def test_valid_plugin_contract(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "plugin.json").write_text(json.dumps({"id":"sample","api_version":1,"capability":"validator"}))
            (root / "plugin.py").write_text("def validate(value):\n    return True\n")
            private = Ed25519PrivateKey.generate()
            public_raw = private.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
            trust = {
                "schema_version": 1,
                "policy": {"algorithm": "ed25519", "maximum_files": 128, "maximum_total_size": 5242880},
                "trusted_keys": {"test-key": {"algorithm": "ed25519", "public_key_base64": base64.b64encode(public_raw).decode(), "status": "active"}},
                "revoked_keys": []
            }
            with patch("videobatch_fast.plugin_signing.load_json", return_value=trust):
                sign_plugin_directory(root, private, "test-key")
                self.assertTrue(validate_plugin(root).valid)

    def test_plugin_with_forbidden_import_is_blocked(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "plugin.json").write_text(json.dumps({"id":"bad","api_version":1,"capability":"validator"}))
            (root / "plugin.py").write_text("import subprocess\n")
            self.assertFalse(validate_plugin(root).valid)

    def test_valid_update_package_is_accepted(self):
        with tempfile.TemporaryDirectory() as tmp:
            package = Path(tmp) / "update.zip"
            content = b"new data"
            manifest = {"schema_version":1,"version":"2.3.1","compatible_from":["2.3.0"],"files":[{"path":"src/new.txt","operation":"add","sha256":hashlib.sha256(content).hexdigest()}]}
            with zipfile.ZipFile(package, "w") as zf:
                zf.writestr("update_manifest.json", json.dumps(manifest))
                zf.writestr("src/new.txt", content)
            check = validate_update_package(package, "2.3.0")
            self.assertTrue(check.valid, check.message)


    def test_update_candidate_selftest_and_atomic_swap(self):
        with tempfile.TemporaryDirectory() as tmp, patch("videobatch_fast.paths.state_dir", return_value=Path(tmp) / "state"):
            root = Path(tmp)
            install = root / "install"
            install.mkdir()
            (install / "version.txt").write_text("old", encoding="utf-8")
            (install / "test.sh").write_text("#!/usr/bin/env bash\nset -e\ntest \"$(cat version.txt)\" = new\n", encoding="utf-8")
            os.chmod(install / "test.sh", 0o755)
            package = root / "update.zip"
            content = b"new"
            test_bytes = (install / "test.sh").read_bytes()
            release_payload = {
                "schema_version": 2,
                "file_count": 2,
                "files": [
                    {"path": "test.sh", "size": len(test_bytes), "sha256": hashlib.sha256(test_bytes).hexdigest(), "mode": "0o755"},
                    {"path": "version.txt", "size": len(content), "sha256": hashlib.sha256(content).hexdigest(), "mode": "0o644"},
                ],
            }
            release_bytes = (json.dumps(release_payload, indent=2) + "\n").encode()
            manifest = {
                "schema_version": 3,
                "version": "2.3.1",
                "compatible_from": ["2.3.0"],
                "files": [
                    {"path": "version.txt", "operation": "replace", "sha256": hashlib.sha256(content).hexdigest(), "mode": "0o644"},
                    {"path": "RELEASE_MANIFEST.json", "operation": "add", "sha256": hashlib.sha256(release_bytes).hexdigest(), "mode": "0o644"},
                ],
            }
            with zipfile.ZipFile(package, "w") as zf:
                zf.writestr("update_manifest.json", json.dumps(manifest))
                zf.writestr("version.txt", content)
                zf.writestr("RELEASE_MANIFEST.json", release_bytes)
            result = apply_update_package(package, install, "2.3.0", timeout=30)
            self.assertTrue(result.success, result.message)
            self.assertEqual((install / "version.txt").read_text(), "new")
            self.assertTrue(Path(result.backup).is_dir())

    def test_update_path_traversal_is_blocked(self):
        with tempfile.TemporaryDirectory() as tmp:
            package = Path(tmp) / "bad.zip"
            content = b"x"
            manifest = {"schema_version":1,"version":"2.3.1","compatible_from":["2.3.0"],"files":[{"path":"../evil","operation":"add","sha256":hashlib.sha256(content).hexdigest()}]}
            with zipfile.ZipFile(package, "w") as zf:
                zf.writestr("update_manifest.json", json.dumps(manifest))
                zf.writestr("../evil", content)
            self.assertFalse(validate_update_package(package, "2.3.0").valid)


class AssuranceTests(unittest.TestCase):
    def test_all_scenarios_have_expected_safe_result(self):
        results = run_scenarios()
        self.assertEqual(len(results), 12)
        bad = [r for r in results if r.status == "failed"]
        self.assertEqual(bad, [], bad)

    def test_each_scenario_has_plain_solution(self):
        self.assertTrue(all(result.solution for result in run_scenarios()))


class PreviewTests(unittest.TestCase):
    @unittest.skipUnless(__import__("shutil").which("ffmpeg"), "FFmpeg fehlt")
    def test_real_preview_is_generated(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "source.png"
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "color=c=blue:s=320x180", "-frames:v", "1", str(source)], check=True)
            with patch("videobatch_fast.preview_service.cache_dir", return_value=Path(tmp) / "cache"):
                preview = build_preview(source, 640)
            self.assertTrue(preview.is_file())
            self.assertGreater(preview.stat().st_size, 100)


if __name__ == "__main__":
    unittest.main()
