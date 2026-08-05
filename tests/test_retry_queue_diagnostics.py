from __future__ import annotations

import ast
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

from videobatch_fast.retry_diagnostics import inspect_retry_queue

ROOT = Path(__file__).resolve().parents[1]


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _queue(path: Path, *, audio: Path, media: Path, missing: Path) -> None:
    payload = {
        "schema_version": 1,
        "max_entries": 100,
        "max_attempts": 2,
        "dropped_total": 0,
        "entries": [
            {
                "job_id": "startable",
                "index": 1,
                "state": "failed",
                "attempts": 1,
                "max_attempts": 2,
                "retry_allowed": True,
                "first_error": "ursprünglicher Fehler",
                "latest_error": "letzter Fehler",
                "protection": "Originaldateien geschützt.",
                "failure_kind": "processing",
                "operation_id": "op-1",
                "audio": str(audio),
                "media": str(media),
                "media_sequence": [],
                "output": str(path.parent / "out-1.mp4"),
                "updated_at": "2026-08-05T12:00:00+0200",
            },
            {
                "job_id": "missing-input",
                "index": 2,
                "state": "not_started",
                "attempts": 0,
                "max_attempts": 2,
                "retry_allowed": True,
                "first_error": "Schutzstopp",
                "latest_error": "Schutzstopp",
                "protection": "Auftrag nicht gestartet.",
                "failure_kind": "not_started",
                "operation_id": "op-2",
                "audio": str(audio),
                "media": str(missing),
                "media_sequence": [],
                "output": str(path.parent / "out-2.mp4"),
                "updated_at": "2026-08-05T12:01:00+0200",
            },
            {
                "job_id": "limit",
                "index": 3,
                "state": "limit_reached",
                "attempts": 2,
                "max_attempts": 2,
                "retry_allowed": False,
                "first_error": "erster Fehler",
                "latest_error": "zweiter Fehler",
                "protection": "Keine automatische Wiederholung.",
                "failure_kind": "internal",
                "operation_id": "op-3",
                "audio": str(audio),
                "media": str(media),
                "media_sequence": [],
                "output": str(path.parent / "out-3.mp4"),
                "updated_at": "2026-08-05T12:02:00+0200",
            },
        ],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def test_diagnostic_reports_status_errors_paths_and_startability_without_writing(tmp_path: Path) -> None:
    audio = tmp_path / "audio.wav"
    media = tmp_path / "media.png"
    audio.write_bytes(b"audio")
    media.write_bytes(b"media")
    queue = tmp_path / "retry_queue.json"
    _queue(queue, audio=audio, media=media, missing=tmp_path / "missing.png")
    before = queue.read_bytes()
    before_stat = queue.stat()

    report = inspect_retry_queue(queue)

    assert report.queue_valid is True
    assert report.total == 3
    assert report.startable == 1
    assert report.blocked == 2
    assert report.not_started == 1
    assert report.entries[0].startable is True
    assert report.entries[0].first_error == "ursprünglicher Fehler"
    assert report.entries[0].latest_error == "letzter Fehler"
    assert report.entries[0].protection == "Originaldateien geschützt."
    assert report.entries[1].startable is False
    assert any("Mediendatei fehlt" in item for item in report.entries[1].start_blockers)
    assert report.entries[2].startable is False
    assert any("Versuchslimit" in item for item in report.entries[2].start_blockers)
    assert queue.read_bytes() == before
    assert queue.stat().st_mtime_ns == before_stat.st_mtime_ns


def test_json_cli_is_read_only_and_machine_readable(tmp_path: Path) -> None:
    audio = tmp_path / "audio.wav"
    media = tmp_path / "media.png"
    audio.write_bytes(b"audio")
    media.write_bytes(b"media")
    queue = tmp_path / "retry_queue.json"
    _queue(queue, audio=audio, media=media, missing=tmp_path / "missing.png")
    before_hash = _digest(queue)
    before_mtime = queue.stat().st_mtime_ns
    env = {**os.environ, "PYTHONPATH": str(ROOT / "src")}

    completed = subprocess.run(
        [sys.executable, "-m", "videobatch_fast.retry_diagnostics", "--path", str(queue), "--json"],
        cwd=ROOT,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=20,
    )

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    assert payload["total"] == 3
    assert payload["entries"][0]["startable"] is True
    assert _digest(queue) == before_hash
    assert queue.stat().st_mtime_ns == before_mtime


def test_invalid_json_is_reported_but_never_quarantined_or_changed(tmp_path: Path) -> None:
    queue = tmp_path / "retry_queue.json"
    queue.write_bytes(b"{broken")
    before = queue.read_bytes()
    before_mtime = queue.stat().st_mtime_ns

    report = inspect_retry_queue(queue)

    assert report.queue_valid is False
    assert "Ungültiges JSON" in report.error
    assert queue.read_bytes() == before
    assert queue.stat().st_mtime_ns == before_mtime
    assert list(tmp_path.iterdir()) == [queue]


def test_missing_default_or_selected_queue_is_empty_and_not_created(tmp_path: Path) -> None:
    target = tmp_path / "does-not-exist.json"
    report = inspect_retry_queue(target)
    assert report.queue_valid is True
    assert report.queue_exists is False
    assert report.total == 0
    assert not target.exists()


def test_diagnostic_module_contains_no_mutating_file_calls() -> None:
    path = ROOT / "src" / "videobatch_fast" / "retry_diagnostics.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    forbidden = {
        "write_text", "write_bytes", "unlink", "rename", "replace", "mkdir", "rmdir",
        "remove", "atomic_write_json", "quarantine_file", "record_failure", "record_not_started",
        "record_success",
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


def test_main_shell_exposes_read_only_retry_diagnostic_command() -> None:
    shell = (ROOT / "videobatch.sh").read_text(encoding="utf-8")
    assert "retry-status|wiederanlauf-diagnose)" in shell
    assert "-m videobatch_fast.retry_diagnostics" in shell
