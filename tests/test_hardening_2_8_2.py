from __future__ import annotations

import json
import shutil
import signal
import subprocess
import sys
import time
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from videobatch_fast.app_events import AppEvent
from videobatch_fast.archive_service import archive_file, file_hash, recover_archive_transactions
from videobatch_fast.event_logging import EventLogger
from videobatch_fast.jobs import build_jobs
from videobatch_fast.media_library import sort_paths
from videobatch_fast.models import BatchOptions, MediaInfo, PairJob
from videobatch_fast.naming import release_output_reservations, reserve_output_targets, unique_output_path
from videobatch_fast.plugin_runtime import run_plugin_in_sandbox
from videobatch_fast.os_sandbox import probe_sandbox_support
from videobatch_fast.project_state import load_project_state, save_project_state
from videobatch_fast.registry import load_json
from videobatch_fast.runner import BatchRunner, terminate_process_group


def _job(root: Path, output: Path | None = None) -> PairJob:
    audio = root / "audio.wav"
    media = root / "image.png"
    audio.write_bytes(b"audio")
    media.write_bytes(b"image")
    return PairJob(
        index=1,
        audio=audio,
        media=media,
        output=output or root / "out.mp4",
        audio_info=MediaInfo(audio, "audio", duration=1.0, size_bytes=5),
        media_info=MediaInfo(media, "image", width=320, height=180, size_bytes=5),
        fast_path=False,
        reason="test",
    )


class MissingProjectPathTests(unittest.TestCase):
    def test_missing_paths_survive_project_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "project.vbfast.json"
            missing_audio = Path(tmp) / "offline" / "track.wav"
            missing_media = Path(tmp) / "offline" / "cover.png"
            save_project_state(project, {
                "audio_paths": [str(missing_audio)],
                "media_paths": [str(missing_media)],
                "playlist_paths": [str(missing_audio)],
            })
            _path, state, healed = load_project_state(project)
            self.assertFalse(healed)
            self.assertEqual(state["audio_paths"], [str(missing_audio)])
            self.assertEqual(state["media_paths"], [str(missing_media)])
            self.assertEqual(state["playlist_paths"], [str(missing_audio)])

    def test_sorting_retains_missing_entries(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            present = root / "present.wav"
            missing = root / "missing.wav"
            present.write_bytes(b"x")
            ordered = sort_paths([missing, present], "name_asc")
            self.assertCountEqual(ordered, [missing, present])
            self.assertEqual(ordered[-1], missing)


class OutputReservationTests(unittest.TestCase):
    def test_generated_paths_are_unique_even_with_identical_timestamp(self):
        with tempfile.TemporaryDirectory() as tmp, patch("videobatch_fast.naming.timestamp", return_value="20260802_000000_000000"):
            root = Path(tmp)
            audio = root / "same.wav"
            reserved: set[Path] = set()
            first = unique_output_path(root, audio, reserved=reserved, index=1)
            second = unique_output_path(root, audio, reserved=reserved, index=1)
            self.assertNotEqual(first, second)

    def test_duplicate_targets_are_rejected_before_processing(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "output.mp4"
            with self.assertRaises(FileExistsError):
                reserve_output_targets([target, target])
            self.assertFalse(any(Path(tmp).glob("*.videobatch.reserve")))

    def test_reservation_markers_are_private_and_released(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "output.mp4"
            reservations = reserve_output_targets([target])
            marker = reservations[0].marker
            self.assertTrue(marker.is_file())
            self.assertEqual(marker.stat().st_mode & 0o777, 0o600)
            release_output_reservations(reservations)
            self.assertFalse(marker.exists())


class RunnerTerminalEventTests(unittest.TestCase):
    def test_unexpected_job_exception_still_emits_batch_finished(self):
        with tempfile.TemporaryDirectory() as tmp:
            events: list[AppEvent] = []
            runner = BatchRunner(events.append)
            runner.operation_id = "test-operation"
            job = _job(Path(tmp))
            with patch.object(runner, "_run_job", side_effect=RuntimeError("boom")):
                runner._run_batch([job], BatchOptions(output_dir=Path(tmp)))
            names = [event.name for event in events]
            self.assertIn("job_failed_internal", names)
            self.assertNotIn("batch_failed_internal", names)
            self.assertEqual(names[-1], "batch_finished")
            final = dict(events[-1].payload)
            self.assertEqual(final["terminal_event"], "batch_completed_with_internal_failures")
            self.assertEqual(final["failures"], 1)
            self.assertEqual(final["unprocessed"], 0)


class ArchiveJournalTests(unittest.TestCase):
    def test_archive_is_journaled_and_committed_after_target_verification(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "track.wav"
            source.write_bytes(b"audio-data")
            expected = file_hash(source)
            record = archive_file(source, root / "project", "audio")
            target = Path(record.target)
            journal = root / "project" / "Verwendet" / ".transactions" / f"{record.transaction_id}.json"
            payload = json.loads(journal.read_text(encoding="utf-8"))
            self.assertFalse(source.exists())
            self.assertTrue(target.is_file())
            self.assertEqual(file_hash(target), expected)
            self.assertEqual(payload["state"], "committed")

    def test_recovery_never_deletes_source_when_both_copies_exist(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project = root / "project"
            tx_dir = project / "Verwendet" / ".transactions"
            tx_dir.mkdir(parents=True)
            source = root / "source.wav"
            target = project / "Verwendet" / "Audio" / "target.wav"
            target.parent.mkdir(parents=True)
            source.write_bytes(b"safe")
            target.write_bytes(b"safe")
            journal = tx_dir / "tx.json"
            journal.write_text(json.dumps({
                "schema_version": 2,
                "transaction_id": "tx",
                "source": str(source),
                "target": str(target),
                "temp": "",
                "reservation": "",
                "expected_size": 4,
                "expected_hash": file_hash(source),
                "kind": "audio",
                "state": "published",
            }), encoding="utf-8")
            results = recover_archive_transactions(project)
            self.assertTrue(source.exists())
            self.assertEqual(results[0]["status"], "source_retained")


class PluginIsolationTests(unittest.TestCase):
    def test_registry_exposes_only_implemented_capability(self):
        policy = load_json("registries/PLUGIN_REGISTRY.json")
        self.assertEqual(policy["allowed_capabilities"], ["validator"])
        self.assertEqual(policy["implemented_capabilities"], ["validator"])

    @unittest.skipUnless(probe_sandbox_support().available, "Linux namespaces unavailable")
    def test_validator_runs_in_os_isolation(self):
        with tempfile.TemporaryDirectory() as tmp:
            plugin = Path(tmp)
            (plugin / "plugin.py").write_text("def validate(payload):\n    return payload.get('probe') is True\n", encoding="utf-8")
            result = run_plugin_in_sandbox(plugin, "validator", {"probe": True})
            self.assertTrue(result.success, result.message)
            self.assertTrue(result.isolated)
            self.assertTrue(result.result)

    @unittest.skipUnless(probe_sandbox_support().available, "Linux namespaces unavailable")
    def test_plugin_cannot_open_arbitrary_host_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            plugin = Path(tmp) / "plugin"
            plugin.mkdir()
            secret = Path(tmp) / "secret.txt"
            secret.write_text("secret", encoding="utf-8")
            (plugin / "plugin.py").write_text(
                f"def validate(payload):\n    return open({str(secret)!r}).read() == 'secret'\n",
                encoding="utf-8",
            )
            result = run_plugin_in_sandbox(plugin, "validator", {"probe": True})
            self.assertFalse(result.success)


class LoggingHardeningTests(unittest.TestCase):
    def test_event_logs_are_private_and_keep_correlation_id(self):
        with tempfile.TemporaryDirectory() as tmp, patch("videobatch_fast.event_logging.state_dir", return_value=Path(tmp)):
            logger = EventLogger("hardening")
            record = logger.write("TEST", "Test", "Meldung", operation_id="job-123")
            self.assertEqual(record.operation_id, "job-123")
            self.assertEqual(logger.jsonl_path.stat().st_mode & 0o777, 0o600)
            self.assertEqual(logger.human_path.stat().st_mode & 0o777, 0o600)


class ProcessTerminationTests(unittest.TestCase):
    @unittest.skipUnless(sys.platform.startswith("linux"), "POSIX process groups required")
    def test_sigterm_is_escalated_and_bounded(self):
        process = subprocess.Popen(
            [sys.executable, "-c", "import signal,time; signal.signal(signal.SIGTERM, signal.SIG_IGN); time.sleep(60)"],
            start_new_session=True,
        )
        started = time.monotonic()
        returncode = terminate_process_group(process, term_timeout=0.1, kill_timeout=1.0)
        self.assertLess(time.monotonic() - started, 2.0)
        self.assertIsNotNone(process.poll())
        self.assertNotEqual(returncode, 0)


class QualityContractTests(unittest.TestCase):
    def test_dependency_locks_are_exact(self):
        root = Path(__file__).resolve().parents[1]
        for name in ("requirements.lock", "requirements-quality.lock"):
            lines = [line.strip() for line in (root / name).read_text(encoding="utf-8").splitlines()]
            requirements = [line for line in lines if line and not line.startswith("#")]
            self.assertTrue(requirements)
            self.assertTrue(all("==" in line for line in requirements))

    def test_quality_registry_requires_all_named_gates(self):
        policy = load_json("registries/CODE_QUALITY_REGISTRY.json")
        gates = set(policy["required_gates"])
        self.assertTrue({"ruff", "mypy", "pytest_cov", "bandit", "pip_audit"} <= gates)


if __name__ == "__main__":
    unittest.main()
