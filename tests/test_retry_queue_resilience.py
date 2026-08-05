from __future__ import annotations

import json
import time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from videobatch_fast.app_events import AppEvent
from videobatch_fast.models import BatchOptions, JobResult, MediaInfo, PairJob
from videobatch_fast.retry_queue import RetryQueueStore, job_identity
from videobatch_fast.runner import BatchRunner
from videobatch_fast.task_manager import TaskManager
from videobatch_fast.ui_event_handlers_mixin import UiEventHandlersMixin


def _job(root: Path, index: int) -> PairJob:
    audio = root / f"audio-{index}.wav"
    media = root / f"media-{index}.png"
    audio.write_bytes(b"audio")
    media.write_bytes(b"media")
    return PairJob(
        index=index,
        audio=audio,
        media=media,
        output=root / f"output-{index}.mp4",
        audio_info=MediaInfo(audio, "audio", duration=1.0, size_bytes=5),
        media_info=MediaInfo(media, "image", width=320, height=180, size_bytes=5),
        fast_path=False,
        reason="retry-test",
    )


def _failed(job: PairJob, message: str = "simulierter Fehler") -> JobResult:
    return JobResult(job, False, 70, 0.1, message)


def _success(job: PairJob) -> JobResult:
    return JobResult(job, True, 0, 0.1, "fertig")


def test_retry_queue_preserves_original_error_and_blocks_after_limit(tmp_path: Path) -> None:
    queue_path = tmp_path / "retry.json"
    job = _job(tmp_path, 1)

    first = RetryQueueStore(queue_path, max_entries=10, max_attempts=2)
    entry_one = first.record_failure(
        _failed(job, "erster Fehler"),
        operation_id="run-1",
        protection="Ausgabe entfernt; Originale geschützt.",
    )
    assert entry_one["attempts"] == 1
    assert entry_one["retry_allowed"] is True
    assert entry_one["first_error"] == "erster Fehler"

    second = RetryQueueStore(queue_path, max_entries=10, max_attempts=2)
    entry_two = second.record_failure(
        _failed(job, "zweiter Fehler"),
        operation_id="run-2",
        protection="Prozessgruppe beendet.",
    )
    assert entry_two["attempts"] == 2
    assert entry_two["retry_allowed"] is False
    assert entry_two["state"] == "limit_reached"
    assert entry_two["first_error"] == "erster Fehler"
    assert entry_two["latest_error"] == "zweiter Fehler"
    assert entry_two["protection"] == "Prozessgruppe beendet."
    assert second.eligible_entries() == ()
    assert queue_path.stat().st_mode & 0o777 == 0o600


def test_not_started_job_is_preserved_without_consuming_attempt(tmp_path: Path) -> None:
    queue = RetryQueueStore(tmp_path / "retry.json", max_entries=10, max_attempts=2)
    job = _job(tmp_path, 1)
    entry = queue.record_not_started(
        job,
        operation_id="run-1",
        reason="Schutzstopp nach vorherigem Auftrag.",
        protection="Dieser Auftrag wurde nicht gestartet; Eingaben blieben unverändert.",
    )
    assert entry["state"] == "not_started"
    assert entry["attempts"] == 0
    assert entry["retry_allowed"] is True
    assert entry["first_error"] == "Schutzstopp nach vorherigem Auftrag."


def test_retry_queue_is_bounded_and_reports_dropped_entries(tmp_path: Path) -> None:
    queue = RetryQueueStore(tmp_path / "retry.json", max_entries=3, max_attempts=2)
    jobs = [_job(tmp_path, index) for index in range(1, 6)]
    for job in jobs:
        queue.record_failure(
            _failed(job, f"Fehler {job.index}"),
            operation_id="bounded",
            protection="Originale geschützt.",
        )
    entries = queue.entries()
    assert len(entries) == 3
    assert {item["job_id"] for item in entries} == {job_identity(job) for job in jobs[-3:]}
    summary = queue.summary()
    assert summary.total == 3
    assert summary.dropped_total == 2


def test_success_removes_previous_retry_entry(tmp_path: Path) -> None:
    queue = RetryQueueStore(tmp_path / "retry.json")
    job = _job(tmp_path, 1)
    queue.record_failure(_failed(job), operation_id="run-1", protection="geschützt")
    assert queue.summary().total == 1
    assert queue.record_success(job) is True
    assert queue.summary().total == 0


def test_corrupt_retry_queue_is_quarantined_and_rebuilt(tmp_path: Path) -> None:
    queue_path = tmp_path / "retry.json"
    queue_path.write_text("{kaputt", encoding="utf-8")
    queue = RetryQueueStore(queue_path)
    assert queue.entries() == ()
    quarantined = list(tmp_path.glob("retry.retry-queue-corrupt.*.json"))
    assert len(quarantined) == 1
    job = _job(tmp_path, 1)
    queue.record_failure(_failed(job), operation_id="new", protection="geschützt")
    assert json.loads(queue_path.read_text(encoding="utf-8"))["entries"]


def test_runner_continues_and_persists_failed_job(tmp_path: Path) -> None:
    events: list[AppEvent] = []
    runner = BatchRunner(
        events.append,
        retry_queue_path=tmp_path / "retry.json",
    )
    runner.operation_id = "continue-run"
    runner._prepare_retry_queue()
    jobs = [_job(tmp_path, 1), _job(tmp_path, 2)]

    def run_job(job: PairJob, _position: int, _total: int, _options: BatchOptions) -> JobResult:
        if job.index == 1:
            raise RuntimeError("kaputter Einzelauftrag")
        return _success(job)

    with patch.object(runner, "_run_job", side_effect=run_job):
        runner._run_batch(jobs, BatchOptions(output_dir=tmp_path))

    final = dict(events[-1].payload)
    assert final["terminal_event"] == "batch_completed_with_internal_failures"
    assert final["successes"] == 1
    assert final["failures"] == 1
    assert final["unprocessed"] == 0
    assert final["retry_queue"]["retryable"] == 1
    stored = RetryQueueStore(tmp_path / "retry.json").entries()
    assert len(stored) == 1
    assert stored[0]["index"] == 1
    assert stored[0]["first_error"].endswith("kaputter Einzelauftrag")
    assert stored[0]["protection"]


def test_runner_protection_stop_preserves_unstarted_jobs(tmp_path: Path) -> None:
    events: list[AppEvent] = []
    runner = BatchRunner(
        events.append,
        max_consecutive_internal_failures=2,
        retry_queue_path=tmp_path / "retry.json",
    )
    runner.operation_id = "stop-run"
    runner._prepare_retry_queue()
    jobs = [_job(tmp_path, index) for index in range(1, 4)]

    with patch.object(runner, "_run_job", side_effect=RuntimeError("immer kaputt")):
        runner._run_batch(jobs, BatchOptions(output_dir=tmp_path))

    final = dict(events[-1].payload)
    assert final["terminal_event"] == "batch_failed_internal"
    assert final["failures"] == 2
    assert final["unprocessed"] == 1
    entries = RetryQueueStore(tmp_path / "retry.json").entries()
    assert len(entries) == 3
    by_index = {int(item["index"]): item for item in entries}
    assert by_index[1]["state"] == "failed"
    assert by_index[2]["state"] == "failed"
    assert by_index[3]["state"] == "not_started"
    assert by_index[3]["attempts"] == 0
    assert "Schutzschwelle" in by_index[3]["latest_error"]


class _Value:
    def __init__(self) -> None:
        self.value = ""

    def set(self, value: str) -> None:
        self.value = value


class _Logger:
    def __init__(self) -> None:
        self.calls: list[tuple[tuple, dict]] = []

    def write(self, *args, **kwargs) -> None:
        self.calls.append((args, kwargs))


class _FaultyUi(UiEventHandlersMixin):
    def __init__(self) -> None:
        self.current_operation_id = "ui-test"
        self._ui_event_errors: list[str] = []
        self.status_text = _Value()
        self.guidance_text = _Value()
        self.logger = _Logger()
        self.handled: list[str] = []

    def _dispatch_event(self, name: str, payload: dict) -> None:
        if name == "broken":
            raise RuntimeError("Anzeige defekt")
        self.handled.append(name)


def test_ui_event_failure_is_visible_and_next_event_still_runs() -> None:
    ui = _FaultyUi()
    assert ui._handle_event_safely("broken", {"operation_id": "op-1"}) is False
    assert ui._handle_event_safely("next", {}) is True
    assert ui.handled == ["next"]
    assert ui._ui_event_errors == ["broken: RuntimeError: Anzeige defekt"]
    assert "Bedienfehler" in ui.status_text.value
    assert "Andere Funktionen" in ui.guidance_text.value
    assert ui.logger.calls
    assert ui.logger.calls[0][1]["operation_id"] == "op-1"


def test_background_task_error_is_reported_and_manager_remains_usable() -> None:
    errors: list[tuple[str, str]] = []
    manager = TaskManager(on_error=lambda name, exc, _detail: errors.append((name, str(exc))))
    assert manager.start("broken", lambda: (_ for _ in ()).throw(RuntimeError("boom")))
    deadline = time.monotonic() + 2
    while manager.active_names() and time.monotonic() < deadline:
        time.sleep(0.01)
    completed: list[str] = []
    assert manager.start("next", lambda: completed.append("ok"))
    deadline = time.monotonic() + 2
    while manager.active_names() and time.monotonic() < deadline:
        time.sleep(0.01)
    assert errors == [("broken", "boom")]
    assert completed == ["ok"]
    assert manager.errors() == ("broken: RuntimeError: boom",)
