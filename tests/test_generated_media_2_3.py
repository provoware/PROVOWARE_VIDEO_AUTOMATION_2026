from __future__ import annotations

import json
import unittest
from pathlib import Path

from videobatch_fast.probe import probe_media

ROOT = Path(__file__).resolve().parents[1]
MEDIA = ROOT / "tests" / "generated_media"


class GeneratedMediaContractTests(unittest.TestCase):
    def test_manifest_and_all_test_files_exist(self):
        manifest = json.loads((MEDIA / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["schema_version"], 1)
        self.assertGreaterEqual(len(manifest["files"]), 6)
        for relative in manifest["files"].values():
            self.assertTrue((ROOT / relative).is_file(), relative)

    def test_valid_test_media_are_classified(self):
        self.assertEqual(probe_media(MEDIA / "audio_kurz.wav").kind, "audio")
        self.assertEqual(probe_media(MEDIA / "bild_querformat.png").kind, "image")
        self.assertEqual(probe_media(MEDIA / "video_kompatibel.mp4").kind, "video")

    def test_corrupt_media_is_not_treated_as_valid_video(self):
        self.assertNotEqual(probe_media(MEDIA / "medium_beschaedigt.mp4").kind, "video")

    def test_unicode_filename_is_supported(self):
        path = MEDIA / "bühne_äöü_测试.png"
        self.assertTrue(path.is_file())
        self.assertEqual(probe_media(path).kind, "image")


if __name__ == "__main__":
    unittest.main()
