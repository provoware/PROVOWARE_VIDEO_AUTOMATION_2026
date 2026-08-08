from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from videobatch_fast.models import BatchOptions
from videobatch_fast.scheduler import create_schedule_record, load_schedule, save_schedule
from videobatch_fast.scheduler_deadletter import mark_dead_letter
from videobatch_fast.scheduler_diagnostics import diagnose_schedule
from videobatch_fast.scheduler_forecast import estimate_schedule, load_render_samples
from videobatch_fast.scheduler_history import list_scheduler_history
from videobatch_fast.scheduler_operations import build_operations_snapshot
from videobatch_fast.scheduler_simulation import simulate_scheduler

TZ = ZoneInfo("Europe/Berlin")
NOW = datetime(2026, 8, 8, 9, 0, tzinfo=TZ)


def _ok(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(["systemctl", "--user", *args], 0, "", "")


def _record(tmp_path: Path, *, priority: int = 50, when: datetime | None = None, max_lateness: int = 180, recurrence=None):
    tmp_path.mkdir(parents=True, exist_ok=True)
    audio = tmp_path / "audio.wav"
    media = tmp_path / "image.png"
    audio.write_bytes(b"a" * 200)
    media.write_bytes(b"m" * 400)
    project = tmp_path / "project.json"
    project.write_text(json.dumps({"audio_paths": [str(audio)], "media_paths": [str(media)]}), encoding="utf-8")
    launcher = tmp_path / "videobatch.sh"
    launcher.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    launcher.chmod(0o755)
    output = tmp_path / "out"
    output.mkdir()
    record = create_schedule_record(
        project_path=project,
        source_paths=[audio, media],
        options=BatchOptions(output_dir=output),
        scheduled_at=when or (NOW + timedelta(hours=1)),
        max_lateness_minutes=max_lateness,
        recurrence=recurrence or {"kind": "once"},
        timezone_name="Europe/Berlin",
        priority=priority,
        launcher=launcher,
        now=NOW,
    )
    return record, project


def _journal(state_root: Path, record: dict, *, name: str, elapsed: float, output_bytes: int = 10_000_000) -> None:
    directory = state_root / "VideoBatchFast" / "jobs" / "history"
    directory.mkdir(parents=True, exist_ok=True)
    output = directory / f"{name}.mp4"
    output.write_bytes(b"x" * output_bytes)
    payload = {
        "schema_version": 2,
        "operation_id": name,
        "state": "completed",
        "updated_at": f"2026-08-08T08:0{name[-1]}:00+0200",
        "options": record["options"],
        "jobs": [{"index": 1, "state": "completed", "elapsed_seconds": elapsed, "output": str(output)}],
    }
    (directory / f"{name}.json").write_text(json.dumps(payload), encoding="utf-8")


def _tree_digest(root: Path) -> str:
    digest = hashlib.sha256()
    if not root.exists():
        return digest.hexdigest()
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        digest.update(str(path.relative_to(root)).encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def test_forecast_uses_robust_median_and_confidence(tmp_path, monkeypatch) -> None:
    state = tmp_path / "state"
    monkeypatch.setenv("XDG_STATE_HOME", str(state))
    record, _project = _record(tmp_path / "data")
    for index, elapsed in enumerate((90.0, 100.0, 110.0, 120.0, 1000.0), start=1):
        _journal(state, record, name=f"run{index}", elapsed=elapsed, output_bytes=index * 1_000_000)
    samples = load_render_samples()
    forecast = estimate_schedule(record, samples=samples)
    assert forecast["runtime_seconds_p50"] == 110.0
    assert forecast["runtime_seconds_p75"] == 120.0
    assert forecast["runtime_seconds_p90"] < 1000.0
    assert forecast["confidence"] == "medium"
    assert forecast["output_bytes_p75"] is not None


def test_forecast_without_history_refuses_fake_precision(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    record, _project = _record(tmp_path / "data")
    forecast = estimate_schedule(record, samples=[])
    assert forecast["available"] is False
    assert forecast["confidence"] == "none"
    assert forecast["runtime_seconds_p50"] is None
    assert forecast["series_output_bytes_p75"] is None


def test_priority_orders_equal_time_forecast(tmp_path, monkeypatch) -> None:
    state = tmp_path / "state"
    monkeypatch.setenv("XDG_STATE_HOME", str(state))
    first, _ = _record(tmp_path / "first", priority=20)
    second, _ = _record(tmp_path / "second", priority=90)
    for index in range(3):
        _journal(state, first, name=f"r{index}", elapsed=600.0)
    report = simulate_scheduler([first, second], horizon_hours=24, now=NOW, samples=load_render_samples())
    events = [item for item in report["events"] if item.get("projected_start")]
    assert events[0]["schedule_id"] == second["schedule_id"]
    assert events[1]["schedule_id"] == first["schedule_id"]
    assert "Render-Slot" in events[1]["reason"]


def test_blackout_moves_projected_start_without_writing(tmp_path, monkeypatch) -> None:
    state = tmp_path / "state"
    monkeypatch.setenv("XDG_STATE_HOME", str(state))
    record, _ = _record(tmp_path / "data", when=datetime(2026, 8, 8, 10, 0, tzinfo=TZ))
    _journal(state, record, name="r1", elapsed=600.0)
    policy = {
        "schema_version": 1,
        "max_parallel_renders": 1,
        "min_free_output_bytes": 0,
        "conflict_retry_minutes": 5,
        "blackout_windows": [{"days": [5], "start": "09:30", "end": "11:00", "timezone": "Europe/Berlin", "label": "Wartung"}],
    }
    before = _tree_digest(state)
    report = simulate_scheduler([record], horizon_hours=24, now=NOW, samples=load_render_samples(), policy=policy)
    after = _tree_digest(state)
    event = report["events"][0]
    assert event["projected_start"].startswith("2026-08-08T11:00:00")
    assert "Wartungsfenster" in event["reason"]
    assert before == after


def test_queue_delay_can_predict_missed_deadline(tmp_path, monkeypatch) -> None:
    state = tmp_path / "state"
    monkeypatch.setenv("XDG_STATE_HOME", str(state))
    first, _ = _record(tmp_path / "first", priority=90, max_lateness=180)
    second, _ = _record(tmp_path / "second", priority=20, max_lateness=5)
    for index in range(3):
        _journal(state, first, name=f"r{index}", elapsed=20 * 60.0)
    report = simulate_scheduler([first, second], horizon_hours=24, now=NOW, samples=load_render_samples())
    second_event = next(item for item in report["events"] if item["schedule_id"] == second["schedule_id"])
    assert second_event["status"] == "missed"
    assert second_event["projected_start"] is None


def test_dead_letter_is_persistent_and_historized(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setattr("videobatch_fast.scheduler._systemctl", lambda args, timeout=15.0: _ok(args))
    record, project = _record(tmp_path / "data")
    save_schedule(record)
    marked = mark_dead_letter(
        record["schedule_id"], code="source_changed", detail="Quelle verändert.",
        next_action="Zeitplan neu speichern.", now=NOW,
    )
    assert marked["status"] == "dead_letter"
    assert marked["next_run_at"] is None
    assert load_schedule(record["schedule_id"])["dead_letter"]["code"] == "source_changed"
    assert list_scheduler_history(project_path=project)[0]["outcome"] == "dead_letter"


def test_dead_letter_diagnosis_has_concrete_action(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setattr("videobatch_fast.scheduler._systemctl", lambda args, timeout=15.0: _ok(args))
    record, _ = _record(tmp_path / "data")
    save_schedule(record)
    marked = mark_dead_letter(record["schedule_id"], code="project_invalid", detail="Projekt kaputt.", next_action="Projekt reparieren.", now=NOW)
    diagnosis = diagnose_schedule(marked, now=NOW)
    assert diagnosis["severity"] == "critical"
    assert diagnosis["code"] == "dead_letter:project_invalid"
    assert diagnosis["next_action"] == "Projekt reparieren."


def test_operations_snapshot_exposes_eta_action_and_simulation(tmp_path, monkeypatch) -> None:
    state = tmp_path / "state"
    monkeypatch.setenv("XDG_STATE_HOME", str(state))
    record, project = _record(tmp_path / "data")
    _journal(state, record, name="r1", elapsed=120.0)
    snapshot = build_operations_snapshot(schedules=[record], project_path=project, now=NOW, horizon_hours=48)
    row = snapshot["rows"][0]
    assert row["forecast"]["runtime_seconds_p50"] == 120.0
    assert row["next_action"]
    assert snapshot["simulation"]["horizon_hours"] == 48
    assert snapshot["simulation"]["event_count"] == 1


@pytest.mark.parametrize("hours", [24, 48, 168])
def test_supported_dry_run_horizons(hours, tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    record, _ = _record(tmp_path / "data")
    report = simulate_scheduler([record], horizon_hours=hours, now=NOW, samples=[])
    assert report["horizon_hours"] == hours


def test_unknown_dry_run_horizon_is_rejected(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    record, _ = _record(tmp_path / "data")
    with pytest.raises(ValueError, match="24, 48 oder 168"):
        simulate_scheduler([record], horizon_hours=72, now=NOW, samples=[])


def test_forecast_projects_storage_for_remaining_series(tmp_path, monkeypatch) -> None:
    state = tmp_path / "state"
    monkeypatch.setenv("XDG_STATE_HOME", str(state))
    record, _ = _record(
        tmp_path / "data",
        recurrence={"kind": "daily", "interval": 1, "max_occurrences": 3, "catch_up_policy": "run_once"},
    )
    for index in range(3):
        _journal(state, record, name=f"s{index}", elapsed=60.0, output_bytes=2_000_000)
    forecast = estimate_schedule(record, samples=load_render_samples())
    assert forecast["output_bytes_p75"] == 2_000_000
    assert forecast["series_output_bytes_p75"] == 6_000_000
    assert forecast["remaining_occurrences"] == 3


def test_worker_invalid_project_becomes_dead_letter(monkeypatch) -> None:
    from videobatch_fast.scheduler_worker import execute_schedule

    now = NOW
    record = {
        "status": "pending",
        "scheduled_at": now.isoformat(),
        "next_run_at": now.isoformat(),
        "max_lateness_minutes": 180,
        "project_path": "/missing/project.json",
        "options": {},
        "after_action": "none",
    }
    marked = []
    monkeypatch.setattr("videobatch_fast.scheduler_worker.load_schedule", lambda _id: record)
    monkeypatch.setattr("videobatch_fast.scheduler_worker.should_run_occurrence", lambda _record, now: (True, "ok"))
    monkeypatch.setattr("videobatch_fast.scheduler_worker.scheduler_preflight_wait", lambda _record, now: (None, "ok", None, {}))
    monkeypatch.setattr("videobatch_fast.scheduler_worker.source_snapshot_is_current", lambda _record: (True, "ok"))
    monkeypatch.setattr("videobatch_fast.scheduler_worker.update_schedule_status", lambda *args, **kwargs: record)
    monkeypatch.setattr("videobatch_fast.scheduler_worker._project_payload", lambda _path: (_ for _ in ()).throw(ValueError("kaputt")))
    monkeypatch.setattr("videobatch_fast.scheduler_worker.mark_dead_letter", lambda *args, **kwargs: marked.append(kwargs))
    assert execute_schedule("0123456789abcdef", now=now) == 21
    assert marked[-1]["code"] == "project_invalid"
    assert "Projektdatei reparieren" in marked[-1]["next_action"]
