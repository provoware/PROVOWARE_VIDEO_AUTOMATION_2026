from __future__ import annotations

import time
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from videobatch_fast.models import BatchOptions, JobResult, MediaInfo, PairJob
from videobatch_fast.resource_estimation import (
    estimate_job_output_bytes,
    estimate_required_by_directory,
    estimate_required_by_filesystem,
)
from videobatch_fast.retry_policy import classify_retry
from videobatch_fast.retry_queue import RetryQueueStore
from videobatch_fast.runner import BatchRunner
from videobatch_fast.runner_process import ProcessExecution
from videobatch_fast.validation import validate_pairs


def _job(
    root: Path,
    *,
    duration: float = 60.0,
    width: int = 1280,
    height: int = 720,
    fast_path: bool = False,
    media_size: int = 0,
    output_dir: Path | None = None,
) -> PairJob:
    audio = root / "audio.wav"
    media = root / "media.mp4"
    audio.write_bytes(b"audio")
    media.write_bytes(b"media")
    target = output_dir or root
    return PairJob(
        index=1,
        audio=audio,
        media=media,
        output=target / "output.mp4",
        audio_info=MediaInfo(audio, "audio", duration=duration, size_bytes=5),
        media_info=MediaInfo(
            media,
            "video",
            duration=duration,
            codec="h264",
            width=width,
            height=height,
            size_bytes=media_size,
        ),
        fast_path=fast_path,
        reason="rc25-test",
    )


def test_storage_estimate_scales_with_resolution_profile_and_fps(tmp_path: Path) -> None:
    job = _job(tmp_path)
    small = BatchOptions(
        output_dir=tmp_path,
        resolution="1280×720",
        profile="turbo",
        fps=25,
    )
    large = BatchOptions(
        output_dir=tmp_path,
        resolution="1920×1080",
        profile="quality",
        fps=50,
    )
    assert estimate_job_output_bytes(job, large) > estimate_job_output_bytes(job, small)


def test_fast_copy_estimate_never_drops_below_known_source_size(tmp_path: Path) -> None:
    source_size = 900 * 1024**2
    job = _job(tmp_path, duration=30.0, fast_path=True, media_size=source_size)
    options = BatchOptions(output_dir=tmp_path)
    assert estimate_job_output_bytes(job, options) > source_size


def test_storage_estimate_is_grouped_by_real_output_directory(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    first.mkdir()
    second.mkdir()
    first_job = _job(tmp_path, output_dir=first)
    second_job = replace(first_job, index=2, output=second / "output-2.mp4")
    required = estimate_required_by_directory(
        [first_job, second_job], BatchOptions(output_dir=tmp_path)
    )
    assert set(required) == {first, second}
    assert all(value > 512 * 1024**2 for value in required.values())


def test_storage_estimate_combines_directories_on_same_filesystem(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    first.mkdir()
    second.mkdir()
    first_job = _job(tmp_path, output_dir=first)
    second_job = replace(first_job, index=2, output=second / "output-2.mp4")
    options = BatchOptions(output_dir=tmp_path)

    by_directory = estimate_required_by_directory([first_job, second_job], options)
    by_filesystem = estimate_required_by_filesystem([first_job, second_job], options)

    assert len(by_filesystem) == 1
    assert set(by_filesystem[0].directories) == {first, second}
    assert by_filesystem[0].required_bytes == sum(by_directory.values())


def test_validation_blocks_combined_space_shortage_on_same_filesystem(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    first.mkdir()
    second.mkdir()
    first_job = _job(tmp_path, output_dir=first)
    second_job = replace(first_job, index=2, output=second / "output-2.mp4")
    options = BatchOptions(output_dir=tmp_path)
    by_directory = estimate_required_by_directory([first_job, second_job], options)
    simulated_free = max(by_directory.values()) + 1
    assert simulated_free < sum(by_directory.values())

    with (
        patch("videobatch_fast.validation.validate_runtime", return_value=[]),
        patch("videobatch_fast.validation.validate_output_dir", return_value=[]),
        patch("videobatch_fast.validation.ffmpeg_path", return_value=None),
        patch(
            "videobatch_fast.validation.shutil.disk_usage",
            return_value=SimpleNamespace(free=simulated_free),
        ),
    ):
        issues = validate_pairs([first_job, second_job], options)

    disk_issues = [issue for issue in issues if issue.code == "DISK_LOW"]
    assert len(disk_issues) == 1
    assert str(first) in disk_issues[0].message
    assert str(second) in disk_issues[0].message


def test_retry_policy_blocks_environmental_failures(tmp_path: Path) -> None:
    result = JobResult(_job(tmp_path), False, 1, 0.1, "No space left on device")
    decision = classify_retry(result)
    assert decision.category == "environment_blocker"
    assert decision.safe_fallback_allowed is False


def test_transient_failure_stays_manual_and_does_not_allow_fallback(tmp_path: Path) -> None:
    result = JobResult(_job(tmp_path), False, 1, 0.1, "Resource temporarily unavailable")
    decision = classify_retry(result)
    assert decision.category == "transient"
    assert decision.safe_fallback_allowed is False


def test_verification_failure_allows_safe_alternative(tmp_path: Path) -> None:
    result = JobResult(_job(tmp_path), False, 0, 0.1, "Ausgabeprüfung fehlgeschlagen")
    decision = classify_retry(result)
    assert decision.category == "verification_failed"
    assert decision.safe_fallback_allowed is True


def test_retry_queue_keeps_transient_failure_manual_only(tmp_path: Path) -> None:
    job = _job(tmp_path)
    queue = RetryQueueStore(tmp_path / "retry.json", max_attempts=2)
    entry = queue.record_failure(
        JobResult(job, False, 1, 0.1, "Resource temporarily unavailable"),
        operation_id="rc25",
        protection="Originale geschützt.",
    )
    assert entry["retry_allowed"] is True
    assert entry["retry_category"] == "transient"
    assert entry["safe_fallback_allowed"] is False
    assert "automatic_retry_allowed" not in entry
    assert queue.eligible_entries()[0]["job_id"] == entry["job_id"]


def test_ffmpeg_diagnostics_preserve_hard_blocker_before_generic_tail(tmp_path: Path) -> None:
    job = _job(tmp_path)
    execution = ProcessExecution(
        emit=lambda *_args, **_kwargs: None,
        cancelled=lambda: False,
        set_process=lambda _process: None,
        terminate=lambda _process: 1,
        cpu_ticks=lambda _pid: 0,
    )
    result = execution._result(
        ["ffmpeg"],
        job,
        1,
        1,
        1,
        ["No space left on device", "Conversion failed!"],
        time.monotonic(),
    )

    assert "No space left on device" in result.message
    assert result.message.endswith("Conversion failed!")
    assert classify_retry(result).category == "environment_blocker"
    assert classify_retry(result).safe_fallback_allowed is False


def test_runner_does_not_fallback_when_preserved_diagnostic_is_blocking(tmp_path: Path) -> None:
    job = _job(tmp_path, fast_path=False)
    options = BatchOptions(output_dir=tmp_path, quick_mode="techno_clean")
    runner = BatchRunner(lambda _event: None, retry_queue_path=tmp_path / "retry.json")
    failed = JobResult(
        job,
        False,
        1,
        0.1,
        "No space left on device\nConversion failed!",
    )
    with patch.object(runner, "_execute", return_value=failed) as execute:
        result = runner._run_job(job, 1, 1, options)
    assert result.success is False
    assert result.retried is False
    assert execute.call_count == 1


def test_runner_does_not_fallback_or_loop_on_transient_failure(tmp_path: Path) -> None:
    job = _job(tmp_path, fast_path=False)
    options = BatchOptions(output_dir=tmp_path, quick_mode="techno_clean")
    runner = BatchRunner(lambda _event: None, retry_queue_path=tmp_path / "retry.json")
    failed = JobResult(job, False, 1, 0.1, "Resource temporarily unavailable")
    with patch.object(runner, "_execute", return_value=failed) as execute:
        result = runner._run_job(job, 1, 1, options)
    assert result.success is False
    assert result.retried is False
    assert execute.call_count == 1
