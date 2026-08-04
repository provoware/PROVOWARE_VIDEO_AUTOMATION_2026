from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from videobatch_fast.key_archive import create_encrypted_key_archive, verify_key_archive
from videobatch_fast.updates import validate_update_package
from videobatch_fast.visual_approval import (
    approval_fingerprint,
    inspection_manifest_hash,
    sign_visual_approval,
    verify_visual_approval,
)


class StableVisualContractTests(unittest.TestCase):
    def _fixture(self, root: Path) -> Path:
        baseline = root / "tests" / "baselines" / "one.png"
        baseline.parent.mkdir(parents=True)
        baseline.write_bytes(b"baseline")
        report = root / "diagnostics" / "visual_regression_latest.json"
        report.parent.mkdir(parents=True)
        report.write_text(json.dumps({
            "schema_version": 1,
            "passed": True,
            "contract_errors": [],
            "results": [{
                "scenario_id": "one",
                "passed": True,
                "mean_difference": 0.00012,
                "dhash_distance": 1,
                "baseline": "/volatile/a.png",
                "actual": "/volatile/b.png",
            }],
        }), encoding="utf-8")
        manifest = {
            "schema_version": 2,
            "id": "visual",
            "version": "2.8.0",
            "passed": True,
            "summary": {"scenario_count": 1, "passed_count": 1, "failed_count": 0, "contract_error_count": 0},
            "contract_errors": [],
            "links": {"visual_report": "diagnostics/visual_regression_latest.json"},
            "policy": {"maximum_mean_difference": 0.035},
            "runtime": {"generated_at": "one", "visual_report_path": "/absolute/report.json"},
            "scenarios": [{
                "id": "one",
                "group": "dashboard",
                "page": "dashboard",
                "state": "",
                "width": 1280,
                "height": 720,
                "font_scale": 100,
                "required_visible_texts": ["Stable"],
                "required_semantic_colors": ["#e8bd4e"],
                "passed": True,
                "artifacts": {"baseline": "tests/baselines/one.png", "actual": "/volatile/actual.png", "difference": ""},
                "measurements": {"mean_difference": 0.001, "dhash_distance": 1, "message": "ok"},
            }],
        }
        path = root / "VISUAL_INSPECTION_MANIFEST.json"
        path.write_text(json.dumps(manifest), encoding="utf-8")
        return path

    def test_volatile_measurements_do_not_expire_approval(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest_path = self._fixture(root)
            sign_visual_approval(manifest_path, reviewer="Test", build_id="2.8.0", project_root=root, key_dir=root / "keys")
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            before = inspection_manifest_hash(manifest)
            manifest["runtime"]["generated_at"] = "different"
            manifest["runtime"]["visual_report_path"] = "/different/path"
            manifest["scenarios"][0]["artifacts"]["actual"] = "/different/actual.png"
            manifest["scenarios"][0]["measurements"] = {"mean_difference": 0.02, "dhash_distance": 9, "message": "new"}
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            self.assertEqual(inspection_manifest_hash(manifest), before)
            self.assertTrue(verify_visual_approval(manifest, root).valid)

    def test_contract_change_expires_approval(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest_path = self._fixture(root)
            sign_visual_approval(manifest_path, reviewer="Test", build_id="2.8.0", project_root=root, key_dir=root / "keys")
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["scenarios"][0]["required_visible_texts"].append("changed")
            self.assertEqual(verify_visual_approval(manifest, root).status, "expired")


class EncryptedKeyArchiveTests(unittest.TestCase):
    def test_archive_roundtrip_and_wrong_password(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            private = Ed25519PrivateKey.generate()
            private_path = root / "private.pem"
            public_path = root / "public.pem"
            private_path.write_bytes(private.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
            public_path.write_bytes(private.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo))
            archive = root / "backup.pvak"
            passphrase = "correct-horse-battery-staple-2026"
            create_encrypted_key_archive(private_path, public_path, archive, passphrase)
            self.assertTrue(verify_key_archive(archive, passphrase).valid)
            self.assertFalse(verify_key_archive(archive, "wrong-password-that-is-long").valid)
            self.assertEqual(archive.stat().st_mode & 0o777, 0o600)


class StableUpdateBindingTests(unittest.TestCase):
    def test_stable_update_requires_and_accepts_visual_binding(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            visual = {
                "schema_version": 2,
                "id": "visual",
                "version": "2.8.0",
                "passed": True,
                "summary": {"scenario_count": 0, "passed_count": 0, "failed_count": 0, "contract_error_count": 0},
                "contract_errors": [],
                "policy": {},
                "scenarios": [],
                "manual_approval": {
                    "payload": {"build_id": "2.8.0"},
                    "signature": {"algorithm": "ed25519", "signature_base64": "x"},
                },
            }
            visual_bytes = json.dumps(visual).encode("utf-8")
            other = b"stable"
            manifest = {
                "schema_version": 2,
                "version": "2.8.0",
                "channel": "stable",
                "compatible_from": ["2.8.0-rc1"],
                "visual_approval": {
                    "build_id": "2.8.0",
                    "visual_contract_sha256": inspection_manifest_hash(visual),
                    "approval_sha256": approval_fingerprint(visual),
                },
                "files": [
                    {"path": "VISUAL_INSPECTION_MANIFEST.json", "operation": "replace", "sha256": hashlib.sha256(visual_bytes).hexdigest()},
                    {"path": "VERSION.json", "operation": "replace", "sha256": hashlib.sha256(other).hexdigest()},
                ],
            }
            package = root / "stable_update.zip"
            with zipfile.ZipFile(package, "w") as archive:
                archive.writestr("update_manifest.json", json.dumps(manifest))
                archive.writestr("VISUAL_INSPECTION_MANIFEST.json", visual_bytes)
                archive.writestr("VERSION.json", other)
            check = validate_update_package(package, "2.8.0-rc1")
            self.assertTrue(check.valid, check.message)


if __name__ == "__main__":
    unittest.main()
