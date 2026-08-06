from __future__ import annotations

from videobatch_fast.canonical_kpi import build_kpi_snapshots


def _snapshots(**overrides):
    values = {
        "audio_count": 0,
        "media_count": 0,
        "missing_sources": 0,
        "job_count": 0,
        "completed_jobs": 0,
        "failed_jobs": 0,
        "active_tasks": (),
        "visual_effect": "none",
        "transition": "none",
        "quick_mode": "smart_auto",
    }
    values.update(overrides)
    return build_kpi_snapshots(**values)


def test_media_kpi_distinguishes_empty_warning_error_loading_and_success() -> None:
    assert _snapshots()["media"].state == "empty"
    assert _snapshots(audio_count=1)["media"].state == "warning"
    assert _snapshots(audio_count=1, media_count=1, missing_sources=1)["media"].state == "error"
    assert _snapshots(audio_count=1, media_count=1, active_tasks=("selection-preview",))["media"].state == "loading"
    ready = _snapshots(audio_count=2, media_count=3)["media"]
    assert ready.state == "success"
    assert ready.value == "5"


def test_queue_kpi_distinguishes_ready_running_failure_and_completion() -> None:
    assert _snapshots(job_count=2)["queue"].state == "ready"
    assert _snapshots(job_count=2, active_tasks=("batch-render",))["queue"].state == "loading"
    assert _snapshots(job_count=2, completed_jobs=2, failed_jobs=1)["queue"].state == "error"
    assert _snapshots(job_count=2, completed_jobs=2)["queue"].state == "success"


def test_effect_and_scheduler_contract_remains_honest() -> None:
    neutral = _snapshots()
    assert neutral["effects"].state == "empty"
    active = _snapshots(visual_effect="ken_burns", transition="fade")
    assert active["effects"].state == "success"
    scheduler = neutral["scheduler"]
    assert scheduler.state == "disabled"
    assert scheduler.action_enabled is False
    assert "Checkpoint 5" in scheduler.detail
