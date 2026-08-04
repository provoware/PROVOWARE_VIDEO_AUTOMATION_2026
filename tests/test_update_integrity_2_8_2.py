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


if __name__ == "__main__":
    unittest.main()
