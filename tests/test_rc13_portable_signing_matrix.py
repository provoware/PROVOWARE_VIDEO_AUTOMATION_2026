from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from videobatch_fast.artifact_signing import create_keypair, sign_file, verify_file

ROOT = Path(__file__).resolve().parents[1]


class Rc13PortableSigningMatrixTests(unittest.TestCase):
    def test_portable_builder_never_injects_python_glibc_into_media(self) -> None:
        source = (ROOT / "scripts/build_portable_bundle.py").read_text(encoding="utf-8")
        self.assertIn("env -u LD_LIBRARY_PATH", source)
        self.assertIn("glibc_injection_into_media", source)
        self.assertNotIn("ffmpeg.bin", source)
        self.assertNotIn('exec "$LOADER" --library-path "$LIBS"', source)

    def test_artifact_signature_detects_tampering(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            private = root / "private.pem"; public = root / "public.pem"; artifact = root / "release.zip"
            create_keypair(private, public)
            artifact.write_bytes(b"stable bytes")
            signature = sign_file(artifact, private)
            self.assertTrue(verify_file(artifact, signature, public).valid)
            artifact.write_bytes(b"changed bytes")
            self.assertFalse(verify_file(artifact, signature, public).valid)

    def test_public_release_key_is_bundled_but_private_key_is_not(self) -> None:
        self.assertTrue((ROOT / "resources/signing/release-public-key.pem").is_file())
        private_candidates = list(ROOT.rglob("*Private*Key*.pem")) + list(ROOT.rglob("private-key.pem"))
        self.assertEqual(private_candidates, [])

    def test_kubuntu_matrix_covers_two_required_x11_targets(self) -> None:
        contract = json.loads((ROOT / "KUBUNTU_BUILD_MATRIX.json").read_text(encoding="utf-8"))
        targets = {(item["os"], item["session"]) for item in contract["targets"]}
        self.assertEqual(targets, {
            ("ubuntu-22.04", "x11"),
            ("ubuntu-24.04", "x11"),
        })
        workflow = (ROOT / ".github/workflows/kubuntu-build-matrix.yml").read_text(encoding="utf-8")
        self.assertIn("ubuntu-22.04", workflow); self.assertIn("ubuntu-24.04", workflow)
        self.assertIn("x11", workflow); self.assertNotIn("- wayland", workflow)


if __name__ == "__main__":
    unittest.main()
