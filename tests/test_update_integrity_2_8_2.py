from __future__ import annotations

import hashlib
import json
import os
import tempfile
import unittest
import warnings
import zipfile
from pathlib import Path
from unittest.mock import patch

from videobatch_fast.updates import apply_update_package, validate_update_package


def _release_manifest(files: dict[str, tuple[bytes, int]]) -> bytes:
    payload = {
        "schema_version": 2,
        "file_count": len(files),
        "files": [
            {
                "path": path,
                "size": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
                "mode": oct(mode),
            }
            for path, (data, mode) in sorted(files.items())
        ],
    }
    return (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode()


def _write_update(package: Path, version_data: bytes, release_data: bytes) -> None:
    entries = {
        "version.txt": (version_data, 0o644),
        "RELEASE_MANIFEST.json": (release_data, 0o644),
    }
    manifest = {
        "schema_version": 3,
        "version": "2.8.2-rc1",
        "channel": "release-candidate",
        "compatible_from": ["2.8.1-rc1"],
        "files": [
            {
                "path": path,
                "operation": "replace" if path == "version.txt" else "add",
                "sha256": hashlib.sha256(data).hexdigest(),
                "mode": oct(mode),
            }
            for path, (data, mode) in entries.items()
        ],
    }
    with zipfile.ZipFile(package, "w") as archive:
        archive.writestr("update_manifest.json", json.dumps(manifest))
        for path, (data, _mode) in entries.items():
            archive.writestr(path, data)


class UpdateIntegrityTests(unittest.TestCase):
    def test_duplicate_zip_names_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            package = Path(tmp) / "bad.zip"
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                with zipfile.ZipFile(package, "w") as archive:
                    archive.writestr("update_manifest.json", "{}")
                    archive.writestr("update_manifest.json", "{}")
            self.assertFalse(validate_update_package(package, "2.8.1-rc1").valid)

    def test_self_test_that_mutates_manifested_file_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp, patch("videobatch_fast.paths.state_dir", return_value=Path(tmp) / "state"):
            root = Path(tmp)
            install = root / "install"
            install.mkdir()
            old_version = b"old"
            new_version = b"new"
            test_script = b"#!/usr/bin/env bash\nset -e\necho changed > version.txt\n"
            (install / "version.txt").write_bytes(old_version)
            (install / "test.sh").write_bytes(test_script)
            os.chmod(install / "test.sh", 0o755)
            release = _release_manifest({"test.sh": (test_script, 0o755), "version.txt": (new_version, 0o644)})
            package = root / "update.zip"
            _write_update(package, new_version, release)
            result = apply_update_package(package, install, "2.8.1-rc1", timeout=20)
            self.assertFalse(result.success)
            self.assertIn("verändert", result.message)
            self.assertEqual((install / "version.txt").read_bytes(), old_version)

    def test_read_only_self_test_preserves_candidate_and_activates(self):
        with tempfile.TemporaryDirectory() as tmp, patch("videobatch_fast.paths.state_dir", return_value=Path(tmp) / "state"):
            root = Path(tmp)
            install = root / "install"
            install.mkdir()
            old_version = b"old"
            new_version = b"new"
            test_script = b"#!/usr/bin/env bash\nset -e\ntest \"$(cat version.txt)\" = new\n"
            (install / "version.txt").write_bytes(old_version)
            (install / "test.sh").write_bytes(test_script)
            os.chmod(install / "test.sh", 0o755)
            release = _release_manifest({"test.sh": (test_script, 0o755), "version.txt": (new_version, 0o644)})
            package = root / "update.zip"
            _write_update(package, new_version, release)
            result = apply_update_package(package, install, "2.8.1-rc1", timeout=20)
            self.assertTrue(result.success, result.message)
            self.assertEqual((install / "version.txt").read_bytes(), new_version)


    def _working_update(self, root: Path) -> tuple[Path, Path]:
        install = root / "install"
        install.mkdir()
        script = b'#!/usr/bin/env bash\\nset -e\\ntest "$(cat version.txt)" = new\\n'
        (install / "version.txt").write_bytes(b"old")
        (install / "test.sh").write_bytes(script)
        (install / "test.sh").chmod(0o755)
        package = root / "update.zip"
        manifest = _release_manifest({
            "test.sh": (script, 0o755),
            "version.txt": (b"new", 0o644),
        })
        _write_update(package, b"new", manifest)
        return install, package

    def test_existing_backup_cannot_be_overwritten_on_name_collision(self):
        class FixedUUID:
            hex = "fixeduniqueid"

        with tempfile.TemporaryDirectory() as temp, patch(
            "videobatch_fast.paths.state_dir", return_value=Path(temp) / "state"
        ):
            root = Path(temp)
            install, package = self._working_update(root)
            previous_backup = root / "install.backup_20261020_153000_fixeduniqueid"
            previous_backup.mkdir()
            (previous_backup / "important.txt").write_text("Behalten!", encoding="utf-8")
            with patch("videobatch_fast.updates.uuid.uuid4", return_value=FixedUUID()), patch(
                "videobatch_fast.updates.time.strftime", return_value="20261020_153000"
            ):
                result = apply_update_package(package, install, "2.8.1-rc1", timeout=20)
            self.assertFalse(result.success)
            self.assertIn("bereits vorhanden", result.message)
            self.assertEqual((install / "version.txt").read_bytes(), b"old")
            self.assertEqual((previous_backup / "important.txt").read_text(encoding="utf-8"), "Behalten!")

    def test_failed_activation_rolls_back_previous_installation(self):
        with tempfile.TemporaryDirectory() as temp, patch(
            "videobatch_fast.paths.state_dir", return_value=Path(temp) / "state"
        ):
            root = Path(temp)
            install, package = self._working_update(root)
            real_replace = os.replace

            def simulated_failure(source, destination):
                if Path(source).name == "candidate" and Path(destination) == install:
                    raise OSError("Abbruch bei der Kandidatenaktivierung")
                return real_replace(source, destination)

            with patch("videobatch_fast.updates.os.replace", side_effect=simulated_failure):
                result = apply_update_package(package, install, "2.8.1-rc1", timeout=20)
            self.assertFalse(result.success)
            self.assertEqual((install / "version.txt").read_bytes(), b"old")
            self.assertFalse(list(root.glob("install.backup_*")))

    def test_fsync_failure_after_activation_restores_previous_installation(self):
        with tempfile.TemporaryDirectory() as temp, patch(
            "videobatch_fast.paths.state_dir", return_value=Path(temp) / "state"
        ):
            root = Path(temp)
            install, package = self._working_update(root)
            calls = 0

            def simulated_sync(_parent):
                nonlocal calls
                calls += 1
                if calls == 2:
                    raise OSError("Datenträger-Synchronisation ausgefallen")

            with patch("videobatch_fast.updates._fsync_directory", side_effect=simulated_sync):
                result = apply_update_package(package, install, "2.8.1-rc1", timeout=20)
            self.assertFalse(result.success)
            self.assertGreaterEqual(calls, 3)
            self.assertEqual((install / "version.txt").read_bytes(), b"old")
            self.assertFalse(list(root.glob("install.backup_*")))



if __name__ == "__main__":
    unittest.main()
