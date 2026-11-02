"""Isolierte Tests des festen Notizspeichers."""
import fcntl
import os
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

from videobatch_fast import quick_notes
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


    def test_control_characters_at_edges_and_c1_separators_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / NOTE_FILENAME
            append_quick_note("Vorhanden", target=target)
            original = target.read_bytes()
            for value in (
                "\nNotiz", "Notiz\n", "\rNotiz", "Notiz\t",
                "Notiz\x85Fortsetzung", "Notiz\u2028Fortsetzung", "Notiz\u2029Fortsetzung",
            ):
                with self.subTest(value=repr(value)), self.assertRaises(ValueError):
                    append_quick_note(value, target=target)
                self.assertEqual(target.read_bytes(), original)

    def test_unicode_note_remains_valid(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / NOTE_FILENAME
            append_quick_note("ÄÖÜ 🧑‍💻", target=target)
            self.assertIn("ÄÖÜ 🧑‍💻".encode("utf-8"), target.read_bytes())




    def test_exclusive_lock_is_held_before_capacity_check(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / NOTE_FILENAME
            original_fstat = os.fstat

            def check_lock(descriptor):
                competing = os.open(target, os.O_WRONLY)
                try:
                    with self.assertRaises(BlockingIOError):
                        fcntl.flock(competing, fcntl.LOCK_EX | fcntl.LOCK_NB)
                finally:
                    os.close(competing)
                return original_fstat(descriptor)

            with patch.object(quick_notes.os, "fstat", side_effect=check_lock):
                append_quick_note("Sicher", target=target)

    def test_busy_lock_times_out_without_changing_existing_notes(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / NOTE_FILENAME
            append_quick_note("Vorhanden", target=target)
            before = target.read_bytes()
            with (
                patch.object(quick_notes.fcntl, "flock", side_effect=BlockingIOError),
                patch.object(quick_notes.time, "monotonic", side_effect=[0.0, 3.0]),
            ):
                with self.assertRaisesRegex(TimeoutError, "belegt"):
                    append_quick_note("Zweite", target=target)
            self.assertEqual(target.read_bytes(), before)

    def test_capacity_limit_keeps_existing_notes_intact(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / NOTE_FILENAME
            with patch.object(quick_notes, "MAX_FILE_BYTES", 100):
                append_quick_note("x" * 60, target=target)
                before = target.read_bytes()
                with self.assertRaises(ValueError):
                    append_quick_note("z" * 60, target=target)
                self.assertEqual(target.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
