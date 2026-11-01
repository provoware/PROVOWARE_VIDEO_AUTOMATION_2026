"""Isolierte Tests des festen Notizspeichers."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from videobatch_fast.quick_notes import append_quick_note, NOTE_FILENAME


class QuickNoteTests(unittest.TestCase):
    def test_append_preserves_previous_entries(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / NOTE_FILENAME
            append_quick_note("Erste Notiz", target=target)
            old = target.read_bytes()
            append_quick_note("Zweite Notiz", target=target)
            data = target.read_bytes()
            self.assertTrue(data.startswith(old))
            self.assertEqual(len(data.splitlines()), 2)

    def test_empty_multiline_and_oversized_rejected_without_changes(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / NOTE_FILENAME
            append_quick_note("Gültig", target=target)
            old = target.read_bytes()
            for text in (" ", "Zeile 1\nZeile 2", "a" * 1025):
                with self.assertRaises(ValueError):
                    append_quick_note(text, target=target)
            self.assertEqual(target.read_bytes(), old)

    def test_symlink_target_is_not_modified(self):
        with tempfile.TemporaryDirectory() as directory:
            original = Path(directory) / "original.txt"
            original.write_text("geschützt", encoding="utf-8")
            linked = Path(directory) / NOTE_FILENAME
            linked.symlink_to(original)
            with self.assertRaises(ValueError):
                append_quick_note("kein Zugriff", target=linked)
            self.assertEqual(original.read_text(encoding="utf-8"), "geschützt")


if __name__ == "__main__":
    unittest.main()
