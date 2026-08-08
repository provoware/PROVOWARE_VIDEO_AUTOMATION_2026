from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from videobatch_fast.scheduler_calibration import (
    accuracy_metrics,
    append_forecast_observation,
    build_forecast_quality_report,
    calibration_profile,
    list_forecast_observations,
    rolling_backtest,
)
from videobatch_fast.scheduler_forecast import estimate_schedule
from videobatch_fast.scheduler_operations import build_operations_snapshot

NOW = datetime(2026, 8, 8, 12, 0, tzinfo=timezone.utc)


def _record(tmp_path: Path, *, codec: str = "h264", profile: str = "fast", resolution: str = "1920x1080") -> dict:
    project = tmp_path / "project.json"
    project.write_text(json.dumps({"audio_paths": ["a.wav"], "media_paths": ["i.png"]}), encoding="utf-8")
    return {
        "schedule_id": "0123456789abcdef",
        "project_path": str(project),
        "sources": ["a.wav", "i.png"],
        "status": "pending",
        "scheduled_at": NOW.isoformat(),
        "next_run_at": (NOW + timedelta(hours=1)).isoformat(),
        "occurrence_index": 1,
        "occurrences_completed": 0,
        "max_lateness_minutes": 180,
        "recurrence": {"kind": "once", "max_occurrences": 1},
        "governance": {"priority": 50},
        "options": {
            "codec": codec,
            "profile": profile,
            "resolution": resolution,
            "fps": 30,
            "assignment_mode": "sequential",
            "quick_mode": "balanced",
            "output_dir": str(tmp_path / "out"),
        },
    }


def _sample(index: int, seconds: float, *, day_offset: int = 0, codec: str = "h264", output: float = 1000.0) -> dict:
    when = NOW + timedelta(days=day_offset, minutes=index)
    return {
        "operation_id": f"op{index:03d}",
        "signature": (codec, "fast", "1920x1080", "30", "sequential", "balanced"),
        "compatible_signature": (codec, "fast", "1920x1080", "sequential"),
        "segment": {"codec": codec, "profile": "fast", "resolution": "1920x1080"},
        "job_count": 1,
        "runtime_seconds": float(seconds),
        "seconds_per_job": float(seconds),
        "output_bytes_per_job": float(output),
        "updated_at": when.isoformat(),
    }


def test_rolling_backtest_never_uses_future_samples() -> None:
    samples = [_sample(i, 100.0) for i in range(3)]
    samples.append(_sample(3, 1000.0))
    samples.extend(_sample(i, 1000.0) for i in range(4, 8))
    outcomes = rolling_backtest(samples)
    target = next(item for item in outcomes if item["operation_id"] == "op003")
    assert target["predicted_runtime_seconds"] == 100.0
    assert target["actual_runtime_seconds"] == 1000.0
    assert target["abs_pct_error"] == 0.9


def test_backtest_windows_30_90_180_are_reported() -> None:
    samples = [_sample(i, 100.0 + (i % 3) * 5.0) for i in range(40)]
    report = build_forecast_quality_report(samples=samples, observations=[])
    assert set(report["windows"]) == {"30", "90", "180"}
    assert report["windows"]["30"]["count"] == 30
    assert report["windows"]["90"]["count"] == 37
    assert report["method"] == "rolling_origin_no_future_leakage"


def test_accuracy_metrics_include_mae_rmse_bias_and_percentiles() -> None:
    outcomes = [
        {"error_seconds": 10.0, "actual_runtime_seconds": 100.0, "abs_pct_error": 0.10, "output_abs_pct_error": 0.20},
        {"error_seconds": -20.0, "actual_runtime_seconds": 100.0, "abs_pct_error": 0.20, "output_abs_pct_error": 0.10},
    ]
    metrics = accuracy_metrics(outcomes)
    assert metrics["mae_seconds"] == 15.0
    assert metrics["rmse_seconds"] > 15.0
    assert metrics["median_abs_pct_error"] == 0.15
    assert metrics["bias_pct"] == -0.05
    assert metrics["output_median_abs_pct_error"] == 0.15


def test_runtime_drift_detects_recent_level_shift() -> None:
    samples = [_sample(i, 100.0) for i in range(10)] + [_sample(i + 10, 200.0) for i in range(5)]
    report = build_forecast_quality_report(samples=samples, observations=[])
    assert report["runtime_drift"]["status"] == "drift"
    assert report["runtime_drift"]["shift_pct"] >= 0.9


def test_old_samples_are_downweighted_in_live_forecast(tmp_path) -> None:
    record = _record(tmp_path)
    old = [_sample(i, 1000.0, day_offset=-220) for i in range(4)]
    recent = [_sample(i + 4, 100.0, day_offset=-5) for i in range(4)]
    forecast = estimate_schedule(record, samples=old + recent, now=NOW)
    assert forecast["runtime_seconds_p50"] == 100.0
    assert forecast["sample_age_weighting"] is True


def test_confidence_is_capped_when_backtest_quality_is_poor(tmp_path) -> None:
    record = _record(tmp_path)
    values = [100.0, 100.0, 100.0, 900.0, 100.0, 900.0, 100.0, 900.0, 100.0, 900.0]
    samples = [_sample(i, value) for i, value in enumerate(values)]
    forecast = estimate_schedule(record, samples=samples, now=NOW)
    assert forecast["base_confidence"] == "high"
    assert forecast["confidence"] in {"low", "medium"}
    assert forecast["calibration"]["count"] >= 4


def test_forecast_observation_persists_actual_vs_predicted(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    record = _record(tmp_path)
    forecast = {
        "runtime_seconds_p50": 100.0,
        "runtime_seconds_p75": 120.0,
        "runtime_seconds_p90": 150.0,
        "output_bytes_p75": 1000,
        "confidence": "medium",
        "match": "exact",
        "sample_count": 8,
    }
    path = append_forecast_observation(
        record, forecast=forecast, actual_runtime_seconds=125.0, actual_output_bytes=1200,
        outcome="success", operation_id="run1", finished_at=NOW,
    )
    assert path is not None and path.is_file()
    rows = list_forecast_observations(project_path=Path(record["project_path"]))
    assert len(rows) == 1
    assert rows[0]["prediction"]["runtime_seconds_p50"] == 100.0
    assert rows[0]["actual"]["runtime_seconds"] == 125.0
    assert rows[0]["error"]["runtime_abs_pct"] == 0.2


def test_invalid_zero_actual_is_not_persisted(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    record = _record(tmp_path)
    result = append_forecast_observation(
        record, forecast={}, actual_runtime_seconds=0.0, actual_output_bytes=None,
        outcome="failed", finished_at=NOW,
    )
    assert result is None
    assert list_forecast_observations() == []


def test_segment_report_separates_codec_profile_resolution() -> None:
    samples = [_sample(i, 100.0, codec="h264") for i in range(8)]
    samples += [_sample(i + 20, 200.0, codec="hevc") for i in range(8)]
    report = build_forecast_quality_report(samples=samples, observations=[])
    codecs = {item["codec"] for item in report["segments"]}
    assert {"h264", "hevc"}.issubset(codecs)


def test_operations_snapshot_exposes_forecast_quality(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    monkeypatch.setattr("videobatch_fast.scheduler_operations.diagnose_schedule", lambda *args, **kwargs: {
        "reason": "ok", "next_action": "none", "code": "scheduled", "severity": "info"
    })
    record = _record(tmp_path)
    snapshot = build_operations_snapshot(schedules=[record], project_path=Path(record["project_path"]), now=NOW, horizon_hours=24)
    assert "forecast_quality" in snapshot
    assert snapshot["forecast_quality"]["windows"]["30"]["count"] == 0


def test_calibration_profile_reports_error_drift_with_enough_bad_recent_predictions() -> None:
    baseline = [_sample(i, 100.0) for i in range(10)]
    recent = [_sample(i + 10, 300.0 if i % 2 == 0 else 50.0) for i in range(8)]
    profile = calibration_profile(baseline + recent)
    assert profile["count"] >= 10
    assert profile["drift"]["status"] in {"watch", "drift", "stable"}
    assert profile["median_abs_pct_error"] is not None


def test_scheduler_export_contains_forecast_quality_and_observations(tmp_path, monkeypatch) -> None:
    from zipfile import ZipFile
    from videobatch_fast.scheduler_export import export_scheduler_state

    project = tmp_path / "project.json"
    project.write_text("{}", encoding="utf-8")
    monkeypatch.setattr("videobatch_fast.scheduler_export.list_schedules", lambda project_path=None: [])
    monkeypatch.setattr("videobatch_fast.scheduler_export.list_scheduler_history", lambda project_path=None, limit=500: [])
    monkeypatch.setattr("videobatch_fast.scheduler_export.list_queue_entries", lambda: [])
    monkeypatch.setattr("videobatch_fast.scheduler_export.load_scheduler_policy", lambda: {"schema_version": 1})
    monkeypatch.setattr("videobatch_fast.scheduler_export.load_render_samples", lambda: [_sample(i, 100.0) for i in range(6)])
    monkeypatch.setattr("videobatch_fast.scheduler_export.list_forecast_observations", lambda project_path=None, limit=500: [])
    target = export_scheduler_state(project, tmp_path / "exports", now=NOW)
    with ZipFile(target) as archive:
        names = set(archive.namelist())
        assert "forecast-quality.json" in names
        assert "forecast-actual-vs-predicted.json" in names
        quality = json.loads(archive.read("forecast-quality.json"))
    assert quality["method"] == "rolling_origin_no_future_leakage"


def test_worker_records_actual_vs_predicted_after_real_batch_payload(tmp_path, monkeypatch) -> None:
    from types import SimpleNamespace
    from videobatch_fast.scheduler_worker import execute_schedule

    project = tmp_path / "project.json"
    project.write_text("{}", encoding="utf-8")
    output = tmp_path / "out.mp4"
    output.write_bytes(b"x" * 1234)
    job = SimpleNamespace(output=output)
    record = {
        "schedule_id": "0123456789abcdef",
        "status": "pending",
        "scheduled_at": NOW.isoformat(),
        "next_run_at": NOW.isoformat(),
        "max_lateness_minutes": 180,
        "project_path": str(project),
        "options": {"output_dir": str(tmp_path), "codec": "h264", "profile": "fast", "resolution": "1920x1080"},
        "after_action": "none",
    }

    class FakeRunner:
        def __init__(self, callback):
            self.callback = callback
            self.operation_id = "operation-23"
        def start(self, jobs, options):
            self.callback(SimpleNamespace(name="batch_finished", payload={
                "successes": 1, "failures": 0, "unprocessed": 0, "total": 1,
                "terminal_event": "batch_finished", "elapsed": 125.0,
            }))
        def wait(self, timeout=None):
            return True

    captured = []
    monkeypatch.setattr("videobatch_fast.scheduler_worker.load_schedule", lambda _id: record)
    monkeypatch.setattr("videobatch_fast.scheduler_worker.should_run_occurrence", lambda _record, now: (True, "ok"))
    monkeypatch.setattr("videobatch_fast.scheduler_worker.scheduler_preflight_wait", lambda _record, now: (None, "ok", None, {}))
    monkeypatch.setattr("videobatch_fast.scheduler_worker.source_snapshot_is_current", lambda _record: (True, "ok"))
    monkeypatch.setattr("videobatch_fast.scheduler_worker._project_payload", lambda _path: {"audio_paths": ["a"], "media_paths": ["b"]})
    monkeypatch.setattr("videobatch_fast.scheduler_worker.build_jobs", lambda *args, **kwargs: [job])
    monkeypatch.setattr("videobatch_fast.scheduler_worker.validate_pairs", lambda *args, **kwargs: [])
    monkeypatch.setattr("videobatch_fast.scheduler_worker.BatchRunner", FakeRunner)
    monkeypatch.setattr("videobatch_fast.scheduler_worker.update_schedule_status", lambda *args, **kwargs: record)
    monkeypatch.setattr("videobatch_fast.scheduler_worker.complete_schedule_occurrence", lambda *args, **kwargs: record)
    monkeypatch.setattr("videobatch_fast.scheduler_worker._after_success", lambda _action: (True, "ok"))
    monkeypatch.setattr("videobatch_fast.scheduler_worker.estimate_schedule", lambda *args, **kwargs: {
        "runtime_seconds_p50": 100.0, "runtime_seconds_p75": 120.0, "runtime_seconds_p90": 150.0,
        "output_bytes_p75": 1000, "confidence": "medium", "match": "exact", "sample_count": 8,
    })
    monkeypatch.setattr("videobatch_fast.scheduler_worker.append_forecast_observation", lambda *args, **kwargs: captured.append(kwargs))
    assert execute_schedule(record["schedule_id"], now=NOW) == 0
    assert captured[-1]["actual_runtime_seconds"] == 125.0
    assert captured[-1]["actual_output_bytes"] == 1234
    assert captured[-1]["operation_id"] == "operation-23"


def test_quality_ui_exposes_backtest_segments_and_actual_history() -> None:
    source = Path("src/videobatch_fast/scheduler_manager_dialog.py").read_text(encoding="utf-8")
    assert 'text="Prognosequalität"' in source
    assert "Codec / Profil / Auflösung" in source
    assert "Rolling-Origin" in source
    assert "echte Scheduler-Vergleiche" in source
