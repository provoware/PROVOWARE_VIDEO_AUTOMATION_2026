from __future__ import annotations

from pathlib import Path

from videobatch_fast.models import BatchOptions, JobResult, MediaInfo, PairJob
from videobatch_fast.resource_estimation import (
    estimate_job_output_bytes,
    estimate_required_by_directory,
)
from videobatch_fast.retry_policy import classify_retry


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
    jobs = [
        _job(tmp_path, output_dir=first),
        PairJob(
            **{
                **_job(tmp_path, output_dir=second).__dict__,
            }
        ),
    ]
    required = estimate_required_by_directory(jobs, BatchOptions(output_dir=tmp_path))
    assert set(required) == {first, second}
    assert all(value > 512 * 1024**2 for value in required.values())


def test_retry_policy_blocks_environmental_failures() -> None:
    job = PairJob.__new__(PairJob)
    result = JobResult(job, False, 1, 0.1, "No space left on device")
    decision = classify_retry(result)
    assert decision.category == "environment_blocker"
    assert decision.automatic_retry_allowed is False
    assert decision.safe_fallback_allowed is False


def test_retry_policy_allows_one_transient_retry_class() -> None:
    job = PairJob.__new__(PairJob)
    result = JobResult(job, False, 1, 0.1, "Resource temporarily unavailable")
    decision = classify_retry(result)
    assert decision.category == "transient"
    assert decision.automatic_retry_allowed is True
    assert decision.safe_fallback_allowed is True


def test_verification_failure_allows_safe_alternative_but_not_identical_retry() -> None:
    job = PairJob.__new__(PairJob)
    result = JobResult(job, False, 0, 0.1, "Ausgabeprüfung fehlgeschlagen")
    decision = classify_retry(result)
    assert decision.category == "verification_failed"
    assert decision.automatic_retry_allowed is False
    assert decision.safe_fallback_allowed is True
