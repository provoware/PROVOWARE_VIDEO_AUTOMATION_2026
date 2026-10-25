"""Fault injection uses disposable files only; foreign data must always survive."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from videobatch_fast import archive_service, naming


class ArchiveIntegrityTests(unittest.TestCase):
    def test_competing_archive_target_survives_publish_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.wav"
            source.write_bytes(b"original")
            targets = []

            def collision(_source, target):
                target.write_bytes(b"foreign data")
                targets.append(target)
                raise FileExistsError("competing writer")

            with patch.object(archive_service, "_publish_without_overwrite", side_effect=collision):
                with self.assertRaises(FileExistsError):
                    archive_service.archive_file(source, root / "project", "audio")
            self.assertEqual(source.read_bytes(), b"original")
            self.assertEqual(targets[0].read_bytes(), b"foreign data")

    def test_recovery_never_deletes_journal_supplied_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            victim = root / "unrelated.txt"
            victim.write_bytes(b"valuable")
            transactions = root / "project/Verwendet/.transactions"
            transactions.mkdir(parents=True)
            journal = transactions / "tx.json"
            for field in ("temp", "reservation"):
                payload = {
                    "schema_version": 2, "transaction_id": "tx", "state": "copying",
                    "source": str(root / "missing"), "target": str(root / "missing-target"),
                    "expected_size": 1, "expected_hash": "0" * 64, "kind": "audio",
                    field: str(victim),
                }
                journal.write_text(json.dumps(payload))
                result = archive_service.recover_archive_transactions(root / "project")
                self.assertEqual(victim.read_bytes(), b"valuable")
                self.assertEqual(result[0]["status"], "invalid")
                self.assertEqual(json.loads(journal.read_text()), payload)

    def test_malformed_recovery_schema_is_reported_without_mutation(self):
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            transactions = project / "Verwendet/.transactions"
            transactions.mkdir(parents=True)
            journal = transactions / "broken.json"
            for payload in ([], None, {"expected_size": "invalid"}, {"schema_version": 999}):
                journal.write_text(json.dumps(payload))
                before = journal.read_bytes()
                result = archive_service.recover_archive_transactions(project)
                self.assertEqual(result[0]["status"], "invalid")
                self.assertEqual(journal.read_bytes(), before)

    def test_recovery_does_not_follow_journal_symlink(self):
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory) / "project"
            transactions = project / "Verwendet/.transactions"
            transactions.mkdir(parents=True)
            foreign = Path(directory) / "foreign.json"
            foreign.write_text('{"state":"copying"}')
            (transactions / "tx.json").symlink_to(foreign)
            result = archive_service.recover_archive_transactions(project)
            self.assertEqual(result[0]["status"], "invalid")
            self.assertEqual(foreign.read_text(), '{"state":"copying"}')


class ReservationIntegrityTests(unittest.TestCase):
    def test_live_owner_is_not_displaced_by_age(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "out.mp4"
            first = naming.reserve_output_targets([target])[0]
            payload = json.loads(first.marker.read_text())
            payload["created_unix"] = time.time() - 90000
            first.marker.write_text(json.dumps(payload))
            with self.assertRaises(FileExistsError):
                naming.reserve_output_targets([target])
            first.release()

    def test_release_does_not_remove_replacement_owner(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "out.mp4"
            first = naming.reserve_output_targets([target])[0]
            first.marker.unlink()
            second = naming.reserve_output_targets([target])[0]
            first.release()
            self.assertTrue(second.marker.exists())
            second.release()
            self.assertFalse(second.marker.exists())

    def test_other_process_cannot_acquire_a_live_target(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "out.mp4"
            first = naming.reserve_output_targets([target])[0]
            code = (
                "import sys; from pathlib import Path; "
                "from videobatch_fast.naming import reserve_output_targets; "
                "reserve_output_targets([Path(sys.argv[1])])"
            )
            try:
                result = subprocess.run(
                    [sys.executable, "-c", code, str(target)],
                    capture_output=True, text=True, timeout=10,
                )
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("FileExistsError", result.stderr)
                self.assertTrue(first.marker.exists())
            finally:
                first.release()

    def test_dead_owner_can_be_recovered(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "out.mp4"
            marker = naming.reservation_marker(target)
            marker.write_text(json.dumps({"pid": 123456, "created_unix": time.time()}))
            with patch.object(naming, "_pid_is_alive", return_value=False):
                reservation = naming.reserve_output_targets([target])[0]
            self.assertEqual(json.loads(marker.read_text())["pid"], os.getpid())
            reservation.release()

    def test_recent_incomplete_marker_is_not_stolen(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "out.mp4"
            naming.reservation_marker(target).write_bytes(b"")
            with self.assertRaises(FileExistsError):
                naming.reserve_output_targets([target])


if __name__ == "__main__":
    unittest.main()
