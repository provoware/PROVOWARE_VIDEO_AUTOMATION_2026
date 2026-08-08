from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from zipfile import ZipFile

from videobatch_fast.scheduler_calibration import (
    append_forecast_observation,
    build_forecast_quality_report,
    list_forecast_observations,
)
from videobatch_fast.scheduler_environment import (
    compare_environment_profiles,
    current_epoch,
    environment_fingerprint,
    list_environment_epochs,
    maybe_rebaseline_environment,
)
from videobatch_fast.scheduler_forecast import estimate_schedule

NOW = datetime(2026, 8, 8, 12, 0, tzinfo=timezone.utc)


def _record(tmp_path: Path) -> dict:
    project = tmp_path / "project.json"
    project.write_text(json.dumps({"audio_paths": ["a.wav"], "media_paths": ["i.png"]}), encoding="utf-8")
    return {
        "schedule_id": "0123456789abcdef",
        "project_path": str(project),
        "sources": ["a.wav", "i.png"],
        "occurrences_completed": 0,
        "recurrence": {"max_occurrences": 1},
        "options": {
            "output_dir": str(tmp_path / "out"),
            "codec": "h264",
            "profile": "fast",
            "resolution": "1920x1080",
            "fps": 30,
            "assignment_mode": "pair",
            "quick_mode": "",
            "max_threads": 4,
        },
    }


def _environment(identifier: str, epoch: str = "ep-1", **overrides) -> dict:
    base = {
        "schema_version": 1,
        "machine": "x86_64",
        "cpu_model": "Unit Test CPU",
        "cpu_count": 8,
        "thread_limit": 4,
        "ffmpeg_version": "8.1.2",
        "ffmpeg_build_sha256": "a" * 64,
        "encoder_path": "software",
        "codec": "h264",
        "target_fs": "ext4",
        "target_medium": "local",
        "fingerprint_sha256": identifier,
        "epoch_id": epoch,
    }
    base.update(overrides)
    return base


def _sample(index: int, seconds: float, *, environment: dict | None = None, day_offset: int = 0) -> dict:
    return {
        "operation_id": f"op{index:03d}",
        "signature": ("h264", "fast", "1920x1080", "30", "pair", ""),
        "compatible_signature": ("h264", "fast", "1920x1080", "pair"),
        "segment": {"codec": "h264", "profile": "fast", "resolution": "1920x1080"},
        "job_count": 1,
        "runtime_seconds": seconds,
        "seconds_per_job": seconds,
        "output_bytes_per_job": 1000.0,
        "updated_at": (NOW + timedelta(days=day_offset, minutes=index)).isoformat(),
        "environment": dict(environment or {}),
    }


def test_environment_fingerprint_changes_for_render_relevant_inputs() -> None:
    base = _environment("placeholder")
    base.pop("fingerprint_sha256")
    first = environment_fingerprint(base)
    changed = dict(base, ffmpeg_version="9.0")
    assert environment_fingerprint(changed) != first
    assert environment_fingerprint(dict(base, thread_limit=8)) != first
    assert environment_fingerprint(dict(base, target_medium="network")) != first


def test_environment_comparison_identifies_changed_fields() -> None:
    previous = _environment("old", ffmpeg_version="8.1.1", thread_limit=2)
    current = _environment("new", ffmpeg_version="8.1.2", thread_limit=4)
    comparison = compare_environment_profiles(current, previous)
    assert comparison["changed"] is True
    assert {"ffmpeg_version", "thread_limit"}.issubset(set(comparison["changed_fields"]))


def test_live_forecast_does_not_mix_different_environment_profiles(tmp_path, monkeypatch) -> None:
    current = _environment("env-current")
    other = _environment("env-other")
    monkeypatch.setattr("videobatch_fast.scheduler_forecast.safe_capture_render_environment", lambda _options: current)
    samples = [_sample(i, 100.0, environment=current) for i in range(5)]
    samples += [_sample(i + 10, 1000.0, environment=other) for i in range(8)]
    forecast = estimate_schedule(_record(tmp_path), samples=samples, now=NOW)
    assert forecast["runtime_seconds_p50"] == 100.0
    assert forecast["sample_count"] == 5
    assert forecast["environment_match"] == "exact_epoch"


def test_previous_epoch_is_available_only_with_low_confidence(tmp_path, monkeypatch) -> None:
    current = _environment("env-current", epoch="ep-new")
    previous = _environment("env-current", epoch="ep-old")
    monkeypatch.setattr("videobatch_fast.scheduler_forecast.safe_capture_render_environment", lambda _options: current)
    forecast = estimate_schedule(_record(tmp_path), samples=[_sample(i, 100.0, environment=previous) for i in range(10)], now=NOW)
    assert forecast["available"] is True
    assert forecast["environment_match"] == "previous_epoch"
    assert forecast["confidence"] == "low"


def test_forecast_blocks_cross_environment_fallback_when_no_legacy_samples(tmp_path, monkeypatch) -> None:
    current = _environment("env-current")
    other = _environment("env-other")
    monkeypatch.setattr("videobatch_fast.scheduler_forecast.safe_capture_render_environment", lambda _options: current)
    forecast = estimate_schedule(_record(tmp_path), samples=[_sample(i, 100.0, environment=other) for i in range(10)], now=NOW)
    assert forecast["available"] is False
    assert forecast["environment_match"] == "environment_mismatch"


def test_legacy_samples_remain_backward_compatible(tmp_path, monkeypatch) -> None:
    current = _environment("env-current")
    monkeypatch.setattr("videobatch_fast.scheduler_forecast.safe_capture_render_environment", lambda _options: current)
    forecast = estimate_schedule(_record(tmp_path), samples=[_sample(i, 100.0) for i in range(8)], now=NOW)
    assert forecast["available"] is True
    assert forecast["environment_match"] == "legacy"
    assert forecast["base_confidence"] == "high"


def test_runtime_drift_creates_new_epoch_without_deleting_old(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    profile = _environment("env-drift")
    profile.pop("epoch_id")
    profile["fingerprint_sha256"] = environment_fingerprint(profile)
    initial = current_epoch(profile)
    profile["epoch_id"] = initial["epoch_id"]
    observations = []
    for index in range(10):
        value = 100.0 if index < 5 else 160.0
        observations.append({
            "finished_at": (NOW + timedelta(minutes=index)).isoformat(),
            "environment": dict(profile),
            "actual": {"seconds_per_job": value},
        })
    new_epoch = maybe_rebaseline_environment(profile, observations)
    assert new_epoch is not None
    assert new_epoch["epoch_id"] != initial["epoch_id"]
    assert new_epoch["reason"] == "runtime_drift_rebaseline"
    epochs = list_environment_epochs(profile["fingerprint_sha256"])
    assert len(epochs) == 2
    assert epochs[0]["active"] is False
    assert epochs[1]["active"] is True
    assert maybe_rebaseline_environment(profile, observations) is None


def test_environment_change_is_reported_separately_from_model_drift(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    old = _environment("env-old")
    new = _environment("env-new", ffmpeg_version="9.0")
    samples = [_sample(i, 100.0, environment=old) for i in range(8)]
    samples += [_sample(i + 20, 100.0, environment=new) for i in range(2)]
    report = build_forecast_quality_report(samples=samples, observations=[])
    assert report["environment"]["status"] == "changed"
    assert report["drift_cause"] == "environment_change"
    assert "ffmpeg_version" in report["environment"]["comparison"]["changed_fields"]


def test_same_environment_runtime_shift_is_classified_as_performance_drift(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    env = _environment("env-same")
    samples = [_sample(i, 100.0, environment=env) for i in range(10)]
    samples += [_sample(i + 20, 200.0, environment=env) for i in range(5)]
    report = build_forecast_quality_report(samples=samples, observations=[])
    assert report["environment"]["status"] == "stable"
    assert report["runtime_drift"]["status"] == "drift"
    assert report["drift_cause"] == "performance_drift_same_environment"


def test_actual_observation_persists_environment_epoch_and_seconds_per_job(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    record = _record(tmp_path)
    env = _environment("env-observed")
    forecast = {
        "runtime_seconds_p50": 100.0,
        "runtime_seconds_p75": 120.0,
        "runtime_seconds_p90": 150.0,
        "output_bytes_p75": 1000,
        "confidence": "medium",
        "match": "exact",
        "sample_count": 8,
        "job_count": 2,
        "environment_match": "exact_epoch",
        "environment": env,
    }
    monkeypatch.setattr("videobatch_fast.scheduler_calibration.maybe_rebaseline_environment", lambda *_args, **_kwargs: None)
    append_forecast_observation(
        record, forecast=forecast, actual_runtime_seconds=120.0, actual_output_bytes=1200,
        outcome="success", operation_id="run24", finished_at=NOW,
    )
    rows = list_forecast_observations(project_path=Path(record["project_path"]))
    assert rows[0]["environment"]["fingerprint_sha256"] == "env-observed"
    assert rows[0]["environment"]["epoch_id"] == "ep-1"
    assert rows[0]["actual"]["seconds_per_job"] == 60.0
    assert rows[0]["prediction"]["environment_match"] == "exact_epoch"


def test_job_journal_stores_environment_without_hostname(tmp_path, monkeypatch) -> None:
    from videobatch_fast.job_journal import BatchJournal
    from videobatch_fast.models import BatchOptions

    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    monkeypatch.setattr("videobatch_fast.job_journal.safe_capture_render_environment", lambda _options, **_kwargs: _environment("env-journal"))
    journal = BatchJournal("op24", [], BatchOptions(tmp_path / "out", codec="h264"))
    payload = json.loads(journal.path.read_text(encoding="utf-8"))
    assert payload["render_environment"]["fingerprint_sha256"] == "env-journal"
    assert "node" not in payload["render_environment"]
    assert "hostname" not in payload["render_environment"]



def test_software_codec_change_does_not_create_false_environment_change() -> None:
    base = _environment("placeholder")
    base.pop("fingerprint_sha256")
    first = environment_fingerprint(base)
    assert environment_fingerprint(dict(base, codec="hevc")) == first
    assert environment_fingerprint(dict(base, encoder_path="nvenc")) != first


def test_completed_batch_journal_triggers_noncritical_rebaseline(tmp_path, monkeypatch) -> None:
    from videobatch_fast.job_journal import BatchJournal
    from videobatch_fast.models import BatchOptions

    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    monkeypatch.setattr("videobatch_fast.job_journal.safe_capture_render_environment", lambda _options, **_kwargs: _environment("env-journal"))
    called = []
    monkeypatch.setattr("videobatch_fast.job_journal.maybe_rebaseline_from_job_history", lambda environment, history: called.append((environment, history)))
    journal = BatchJournal("op24-finish", [], BatchOptions(tmp_path / "out", codec="h264"))
    destination = journal.finish(terminal_event="batch_finished", cancelled=False)
    assert destination.is_file()
    assert called and called[0][0]["fingerprint_sha256"] == "env-journal"


def test_scheduler_export_contains_environment_epoch_archive(tmp_path, monkeypatch) -> None:
    from videobatch_fast.scheduler_export import export_scheduler_state

    project = tmp_path / "project.json"
    project.write_text("{}", encoding="utf-8")
    monkeypatch.setattr("videobatch_fast.scheduler_export.list_schedules", lambda project_path=None: [])
    monkeypatch.setattr("videobatch_fast.scheduler_export.list_scheduler_history", lambda project_path=None, limit=500: [])
    monkeypatch.setattr("videobatch_fast.scheduler_export.list_queue_entries", lambda: [])
    monkeypatch.setattr("videobatch_fast.scheduler_export.load_scheduler_policy", lambda: {"schema_version": 1})
    monkeypatch.setattr("videobatch_fast.scheduler_export.load_render_samples", lambda: [])
    monkeypatch.setattr("videobatch_fast.scheduler_export.list_forecast_observations", lambda project_path=None, limit=500: [])
    monkeypatch.setattr("videobatch_fast.scheduler_export.list_environment_epochs", lambda: [{"epoch_id": "ep-1", "active": True}])
    target = export_scheduler_state(project, tmp_path / "exports", now=NOW)
    with ZipFile(target) as archive:
        assert "forecast-environment-epochs.json" in archive.namelist()
        epochs = json.loads(archive.read("forecast-environment-epochs.json"))
    assert epochs[0]["epoch_id"] == "ep-1"
