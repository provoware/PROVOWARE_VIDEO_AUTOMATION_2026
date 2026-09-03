from __future__ import annotations

from videobatch_fast.canonical_kpi import build_kpi_snapshots
from videobatch_fast.canonical_kpi_detail_mixin import CanonicalKpiDetailMixin
from videobatch_fast.canonical_kpi_state import merge_kpi_history, normalize_kpi_history


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
    missing = _snapshots(
        audio_count=1,
        media_count=1,
        missing_sources=1,
        missing_source_names=("verschwunden.png",),
    )["media"]
    assert missing.state == "error"
    assert "verschwunden.png" in missing.cause
    assert missing.recovery_action == "remove_missing_sources"
    assert _snapshots(audio_count=1, media_count=1, active_tasks=("selection-preview",))["media"].state == "loading"
    ready = _snapshots(audio_count=2, media_count=3)["media"]
    assert ready.state == "success"
    assert ready.value == "5"


def test_queue_kpi_distinguishes_ready_running_failure_and_completion() -> None:
    empty = _snapshots()["queue"]
    assert empty.state == "empty"
    assert empty.action_label == "Zuordnung öffnen"
    assert empty.recovery_action == "open_media"
    assert _snapshots(job_count=2)["queue"].state == "ready"
    assert _snapshots(job_count=2, active_tasks=("batch-render",))["queue"].state == "loading"
    failed = _snapshots(
        job_count=2,
        completed_jobs=2,
        failed_jobs=1,
        retryable_jobs=1,
        queue_failure_reasons=("Encoder meldet Fehlercode 1",),
    )["queue"]
    assert failed.state == "error"
    assert failed.recovery_action == "reload_retry_queue"
    assert "Encoder" in failed.cause
    assert _snapshots(job_count=2, completed_jobs=2)["queue"].state == "success"


def test_effect_and_scheduler_contract_remains_honest() -> None:
    neutral = _snapshots()
    assert neutral["effects"].state == "empty"
    active = _snapshots(visual_effect="hardtechno", transition="soft")
    assert active["effects"].state == "success"
    invalid = _snapshots(visual_effect="unbekannt", effect_valid=False)["effects"]
    assert invalid.state == "error"
    assert invalid.recovery_action == "reset_effects"
    scheduler = neutral["scheduler"]
    assert scheduler.state == "disabled"
    assert scheduler.action_enabled is False
    assert "Checkpoint 5" in scheduler.detail


def test_persistent_history_keeps_timestamp_until_a_detail_really_changes() -> None:
    first, changed = merge_kpi_history({}, _snapshots(), now="2026-08-06T17:00:00+02:00")
    assert changed is True
    stable, changed = merge_kpi_history(first, _snapshots(), now="2026-08-06T17:01:00+02:00")
    assert changed is False
    assert stable["media"]["updated_at"] == "2026-08-06T17:00:00+02:00"
    updated, changed = merge_kpi_history(
        stable,
        _snapshots(audio_count=1),
        now="2026-08-06T17:02:00+02:00",
    )
    assert changed is True
    assert updated["media"]["updated_at"] == "2026-08-06T17:02:00+02:00"
    assert updated["queue"]["updated_at"] == "2026-08-06T17:00:00+02:00"


def test_persistent_history_rejects_unknown_or_malformed_records() -> None:
    normalized = normalize_kpi_history(
        {
            "media": {"state": "error", "updated_at": "not-a-date", "cause": "x"},
            "queue": {"state": "invented"},
            "unknown": {"state": "success"},
        }
    )
    assert set(normalized) == {"media"}
    assert normalized["media"]["updated_at"] == ""


def test_rapid_import_loss_queue_error_and_effect_changes_remain_deterministic() -> None:
    observed = []
    for index in range(240):
        phase = index % 4
        if phase == 0:
            snapshots = _snapshots(audio_count=1, media_count=1, job_count=1)
        elif phase == 1:
            snapshots = _snapshots(
                audio_count=1,
                media_count=1,
                missing_sources=1,
                missing_source_names=(f"missing-{index}.png",),
            )
        elif phase == 2:
            snapshots = _snapshots(
                audio_count=1,
                media_count=1,
                job_count=1,
                failed_jobs=1,
                retryable_jobs=1,
                queue_failure_reasons=("Kontrollierter Testfehler",),
            )
        else:
            snapshots = _snapshots(
                audio_count=1,
                media_count=1,
                visual_effect="invalid",
                effect_valid=False,
            )
        observed.append((snapshots["media"].state, snapshots["queue"].state, snapshots["effects"].state))
    assert observed[0] == ("success", "ready", "empty")
    assert observed[1][0] == "error"
    assert observed[2][1] == "error"
    assert observed[3][2] == "error"
    assert hasattr(CanonicalKpiDetailMixin, "_kpi_remove_missing_sources")
    assert hasattr(CanonicalKpiDetailMixin, "_kpi_load_retry_queue")
    assert hasattr(CanonicalKpiDetailMixin, "_kpi_reset_effects")
