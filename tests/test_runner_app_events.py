from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from videobatch_fast.app_events import AppEvent, TypedEventPayload
from videobatch_fast.models import BatchOptions, JobResult, MediaInfo, PairJob
from videobatch_fast.runner import BatchRunner
from videobatch_fast.runner_events import (
    BatchFailedInternalPayload,
    BatchFinishedPayload,
    BatchStartedPayload,
    JobFinishedPayload,
    JobStartedPayload,
)


def _job(root: Path, index: int = 1) -> PairJob:
    audio = root / f"audio-{index}.wav"
    medium = root / f"image-{index}.png"
    output = root / f"output-{index}.mp4"
    audio.write_bytes(b"audio")
    medium.write_bytes(b"image")
    return PairJob(
        index=index,
        audio=audio,
        media=medium,
        output=output,
        audio_info=MediaInfo(audio, "audio", duration=2.0),
        media_info=MediaInfo(medium, "image"),
        fast_path=False,
        reason="test",
    )


def test_runner_emits_typed_core_payloads_directly(tmp_path: Path) -> None:
    events: list[AppEvent] = []
    runner = BatchRunner(events.append, retry_queue_path=tmp_path / "retry.json")
    runner.operation_id = "typed-success"
    runner._prepare_retry_queue()
    job = _job(tmp_path)
    success = JobResult(job, True, 0, 0.25, "ok")

    with patch.object(runner, "_run_job", return_value=success):
        runner._run_batch([job], BatchOptions(output_dir=tmp_path))

    by_name = {event.name: event for event in events}
    assert isinstance(by_name["batch_started"].payload, BatchStartedPayload)
    assert isinstance(by_name["job_finished"].payload, JobFinishedPayload)
    assert isinstance(by_name["batch_finished"].payload, BatchFinishedPayload)
    assert all(isinstance(event, AppEvent) for event in events)
    assert all(event.operation_id == "typed-success" for event in events)


def test_runner_job_started_payload_is_typed(tmp_path: Path) -> None:
    events: list[AppEvent] = []
    runner = BatchRunner(events.append)
    runner.operation_id = "typed-start"
    job = _job(tmp_path)

    with patch.object(runner, "_execute", return_value=JobResult(job, True, 0, 0.1, "ok")), patch(
        "videobatch_fast.runner.verify_output", return_value=(True, "valid")
    ):
        runner._run_job(job, 1, 1, BatchOptions(output_dir=tmp_path))

    started = next(event for event in events if event.name == "job_started")
    assert isinstance(started.payload, JobStartedPayload)
    assert started.payload["job"] is job


def test_runner_internal_failure_payload_is_typed_and_complete(tmp_path: Path) -> None:
    events: list[AppEvent] = []
    runner = BatchRunner(
        events.append,
        max_consecutive_internal_failures=1,
        retry_queue_path=tmp_path / "retry.json",
    )
    runner.operation_id = "typed-failure"
    runner._prepare_retry_queue()
    job = _job(tmp_path)

    with patch.object(runner, "_run_job", side_effect=RuntimeError("boom")):
        runner._run_batch([job], BatchOptions(output_dir=tmp_path))

    failed = next(event for event in events if event.name == "batch_failed_internal")
    assert isinstance(failed.payload, BatchFailedInternalPayload)
    assert failed.payload["job"] is job
    assert failed.payload["position"] == 1
    assert failed.payload["total"] == 1
    assert failed.payload["message"]
    assert failed.payload["protection"]
    assert isinstance(events[-1].payload, BatchFinishedPayload)


def test_all_core_payloads_are_read_only_mappings(tmp_path: Path) -> None:
    job = _job(tmp_path)
    result = JobResult(job, True, 0, 0.1, "ok")
    payloads: tuple[TypedEventPayload, ...] = (
        BatchStartedPayload(total=1),
        JobStartedPayload(job=job, position=1, total=1),
        JobFinishedPayload(result=result, position=1, total=1),
        BatchFailedInternalPayload(
            job=job,
            position=1,
            total=1,
            message="failure",
            traceback="trace",
            protection="protected",
        ),
        BatchFinishedPayload(
            terminal_event="batch_finished",
            cancelled=False,
            successes=1,
            failures=0,
            unprocessed=0,
            total=1,
            elapsed=0.1,
            results=(result,),
            internal_error="",
            callback_errors=(),
            retry_queue={"total": 0},
        ),
    )

    assert all(dict(payload) for payload in payloads)
