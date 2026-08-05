from __future__ import annotations

import ast
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

from videobatch_fast.recovery_consistency import inspect_recovery_consistency

ROOT = Path(__file__).resolve().parents[1]


def _job(audio: Path, media: Path, output: Path, *, state: str) -> dict:
    return {
        "index": 1,
        "audio": str(audio),
        "media": str(media),
        "media_sequence": [],
        "output": str(output),
        "state": state,
        "attempt": 1,
    }


def _job_id(item: dict) -> str:
    stable = {key: item[key] for key in ("audio", "media", "media_sequence", "output")}
    return hashlib.sha256(json.dumps(stable, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _retry(path: Path, item: dict, *, operation: str = "op-1", state: str = "failed", allowed: bool = True) -> str:
    job_id = _job_id(item)
    _write(
        path,
        {
            "schema_version": 1,
            "max_entries": 100,
            "max_attempts": 2,
            "dropped_total": 0,
            "entries": [
                {
                    "job_id": job_id,
                    **{key: item[key] for key in ("index", "audio", "media", "media_sequence", "output")},
                    "state": state,
                    "attempts": 1,
                    "max_attempts": 2,
                    "retry_allowed": allowed,
                    "operation_id": operation,
                    "first_error": "first",
                    "latest_error": "latest",
                    "protection": "protected",
                }
            ],
        },
    )
    return job_id


def _journal(path: Path, item: dict, *, operation: str, state: str) -> None:
    _write(
        path,
        {
            "schema_version": 2,
            "operation_id": operation,
            "state": state,
            "jobs": [item],
            "options": {},
            "terminal_event": "batch_finished" if path.parent.name == "history" else "",
        },
    )


def test_consistent_failed_history_and_retry_entry_are_green_and_read_only(tmp_path: Path) -> None:
    jobs = tmp_path / "jobs"
    audio, media = tmp_path / "a.wav", tmp_path / "m.png"
    audio.write_bytes(b"a")
    media.write_bytes(b"m")
    item = _job(audio, media, tmp_path / "out.mp4", state="failed")
    retry = jobs / "retry_queue.json"
    _retry(retry, item)
    history = jobs / "history" / "op-1.json"
    _journal(history, item, operation="op-1", state="completed_with_failures")
    before = {path: (path.read_bytes(), path.stat().st_mtime_ns) for path in (retry, history)}

    report = inspect_recovery_consistency(jobs)

    assert report.status == "green"
    assert report.findings == ()
    for path, (content, mtime) in before.items():
        assert path.read_bytes() == content
        assert path.stat().st_mtime_ns == mtime


def test_duplicate_ids_and_active_history_conflict_are_reported(tmp_path: Path) -> None:
    jobs = tmp_path / "jobs"
    audio, media = tmp_path / "a.wav", tmp_path / "m.png"
    audio.write_bytes(b"a")
    media.write_bytes(b"m")
    item = _job(audio, media, tmp_path / "out.mp4", state="running")
    retry = jobs / "retry_queue.json"
    _retry(retry, item)
    payload = json.loads(retry.read_text())
    payload["entries"].append(dict(payload["entries"][0]))
    _write(retry, payload)
    _journal(jobs / "active" / "same.json", item, operation="same", state="running")
    _journal(jobs / "history" / "same.json", item, operation="same", state="running")

    report = inspect_recovery_consistency(jobs)
    codes = {item.code for item in report.findings}

    assert report.status == "red"
    assert "duplicate_retry_job_id" in codes
    assert "operation_active_and_history" in codes
    assert "history_running_state" in codes


def test_completed_job_in_retry_queue_is_contradiction(tmp_path: Path) -> None:
    jobs = tmp_path / "jobs"
    audio, media = tmp_path / "a.wav", tmp_path / "m.png"
    audio.write_bytes(b"a")
    media.write_bytes(b"m")
    retry_item = _job(audio, media, tmp_path / "out.mp4", state="failed")
    completed = dict(retry_item, state="completed")
    _retry(jobs / "retry_queue.json", retry_item)
    _journal(jobs / "history" / "op-1.json", completed, operation="op-1", state="completed")

    report = inspect_recovery_consistency(jobs)
    assert "retry_for_completed_job" in {item.code for item in report.findings}


def test_missing_inputs_and_orphan_retry_are_reported(tmp_path: Path) -> None:
    jobs = tmp_path / "jobs"
    item = _job(tmp_path / "missing.wav", tmp_path / "missing.png", tmp_path / "out.mp4", state="failed")
    _retry(jobs / "retry_queue.json", item, operation="orphan")

    report = inspect_recovery_consistency(jobs)
    codes = [item.code for item in report.findings]
    assert codes.count("missing_retry_input") == 2
    assert "orphan_retry_entry" in codes
    assert report.status == "yellow"


def test_failed_journal_without_retry_is_reported(tmp_path: Path) -> None:
    jobs = tmp_path / "jobs"
    audio, media = tmp_path / "a.wav", tmp_path / "m.png"
    audio.write_bytes(b"a")
    media.write_bytes(b"m")
    item = _job(audio, media, tmp_path / "out.mp4", state="failed")
    _journal(jobs / "history" / "op.json", item, operation="op", state="completed_with_failures")

    report = inspect_recovery_consistency(jobs)
    assert "unfinished_journal_without_retry" in {item.code for item in report.findings}


def test_invalid_source_returns_red_without_quarantine_or_change(tmp_path: Path) -> None:
    jobs = tmp_path / "jobs"
    queue = jobs / "retry_queue.json"
    queue.parent.mkdir(parents=True)
    queue.write_bytes(b"{broken")
    before = queue.read_bytes(), queue.stat().st_mtime_ns

    report = inspect_recovery_consistency(jobs)

    assert report.status == "red"
    assert report.invalid_sources == 1
    assert queue.read_bytes() == before[0]
    assert queue.stat().st_mtime_ns == before[1]
    assert list(jobs.iterdir()) == [queue]


def test_json_cli_and_shell_entrypoint(tmp_path: Path) -> None:
    jobs = tmp_path / "jobs"
    env = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
    completed = subprocess.run(
        [sys.executable, "-m", "videobatch_fast.recovery_consistency", "--jobs-root", str(jobs), "--json"],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        timeout=20,
        check=False,
    )
    assert completed.returncode == 0
    assert json.loads(completed.stdout)["status"] == "green"
    shell = (ROOT / "videobatch.sh").read_text(encoding="utf-8")
    assert "recovery-check|wiederanlauf-konsistenz)" in shell
    assert "-m videobatch_fast.recovery_consistency" in shell


def test_module_has_no_mutating_file_operations() -> None:
    path = ROOT / "src" / "videobatch_fast" / "recovery_consistency.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    forbidden = {
        "write_text", "write_bytes", "unlink", "rename", "replace", "mkdir", "rmdir", "remove",
        "atomic_write_json", "quarantine_file", "record_failure", "record_not_started", "record_success",
    }
    calls = {
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    }
    names = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    assert forbidden.isdisjoint(calls | names)
    source = path.read_text(encoding="utf-8")
    assert "RetryQueueStore" not in source
    assert "BatchJournal" not in source
