"""Regressionstests für Archiv-Zielkollisionen und sichere Wiederherstellung."""
from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from videobatch_fast import archive_service

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

    def test_valid_recovery_preserves_original_and_target(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project = root / "project"
            destination = project / "Verwendet/Audio"
            transactions = project / "Verwendet/.transactions"
            destination.mkdir(parents=True)
            transactions.mkdir(parents=True)
            source = root / "input.wav"
            source.write_bytes(b"original-media")
            target = destination / "input__verwendet.wav"
            target.write_bytes(source.read_bytes())
            journal = transactions / "tx.json"
            payload = {
                "schema_version": 2, "transaction_id": "tx", "state": "verified_target",
                "source": str(source), "target": str(target), "temp": "",
                "reservation": "", "expected_size": source.stat().st_size,
                "expected_hash": hashlib.sha256(source.read_bytes()).hexdigest(), "kind": "audio",
            }
            journal.write_text(json.dumps(payload), encoding="utf-8")
            results = archive_service.recover_archive_transactions(project)
            self.assertEqual(results[0]["status"], "source_retained")
            self.assertEqual(source.read_bytes(), b"original-media")
            self.assertEqual(target.read_bytes(), b"original-media")
            self.assertEqual(json.loads(journal.read_text())["state"], "source_retained")

    def test_symlink_archive_target_rejected_without_side_effect(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project = root / "project"
            target_dir = project / "Verwendet/Audio"
            journal_dir = project / "Verwendet/.transactions"
            target_dir.mkdir(parents=True)
            journal_dir.mkdir(parents=True)
            foreign = root / "foreign.wav"
            foreign.write_bytes(b"foreign")
            target = target_dir / "linked.wav"
            target.symlink_to(foreign)
            payload = {
                "schema_version": 2, "transaction_id": "tx", "state": "published",
                "source": str(root / "missing.wav"), "target": str(target),
                "expected_size": 7, "expected_hash": hashlib.sha256(b"foreign").hexdigest(),
                "kind": "audio",
            }
            journal = journal_dir / "tx.json"
            journal.write_text(json.dumps(payload), encoding="utf-8")
            self.assertEqual(archive_service.recover_archive_transactions(project)[0]["status"], "invalid")
            self.assertEqual(foreign.read_bytes(), b"foreign")
            self.assertEqual(json.loads(journal.read_text()), payload)


if __name__ == "__main__":
    unittest.main()
