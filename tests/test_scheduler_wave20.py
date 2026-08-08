from __future__ import annotations

import json
import subprocess
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from videobatch_fast.models import BatchOptions
from videobatch_fast.render_coordination import RenderBusyError, RenderExecutionLease, render_lock_path
from videobatch_fast.runner import BatchRunner
from videobatch_fast.scheduler import (
    build_systemd_units,
    cancel_schedule,
    complete_schedule_occurrence,
    create_schedule_record,
    defer_schedule_for_conflict,
    list_schedules,
    load_schedule,
    save_schedule,
    schedule_fingerprint,
    schedule_path,
)
from videobatch_fast.scheduler_history import list_scheduler_history
from videobatch_fast.scheduler_recurrence import (
    next_valid_occurrence,
    normalize_recurrence,
    occurrence_at_index,
    resolve_local_wall_time,
    should_run_occurrence,
)


def _fixture(tmp_path: Path, *, scheduled: datetime, recurrence: dict | None = None):
    tmp_path.mkdir(parents=True, exist_ok=True)
    project = tmp_path / "project.vbfast.json"
    audio = tmp_path / "audio.mp3"
    image = tmp_path / "image.png"
    launcher = tmp_path / "videobatch.sh"
    audio.write_bytes(b"audio")
    image.write_bytes(b"image")
    project.write_text(json.dumps({"schema_version": 3, "audio_paths": [str(audio)], "media_paths": [str(image)]}), encoding="utf-8")
    launcher.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
    launcher.chmod(0o755)
    record = create_schedule_record(
        project_path=project,
        source_paths=[audio, image],
        options=BatchOptions(output_dir=tmp_path / "out"),
        scheduled_at=scheduled,
        recurrence=recurrence,
        timezone_name="Europe/Berlin",
        launcher=launcher,
        now=scheduled - timedelta(minutes=20),
    )
    return record


def _systemctl_ok(args: list[str]):
    return subprocess.CompletedProcess(["systemctl", *args], 0, "", "")


def test_daily_recurrence_is_bounded_and_fingerprint_bound(tmp_path) -> None:
    scheduled = datetime(2026, 8, 8, 9, 30, tzinfo=ZoneInfo("Europe/Berlin"))
    record = _fixture(tmp_path, scheduled=scheduled, recurrence={"kind": "daily", "interval": 2, "max_occurrences": 5, "catch_up_policy": "skip", "timezone": "Europe/Berlin", "dst_policy": "later"})
    assert record["schema_version"] == 3
    assert record["recurrence"]["max_occurrences"] == 5
    assert occurrence_at_index(record, 3).date() == date(2026, 8, 12)
    original = record["schedule_fingerprint"]
    record["recurrence"]["interval"] = 3
    assert schedule_fingerprint(record) != original


def test_recurrence_limits_reject_unbounded_rules() -> None:
    scheduled = datetime(2026, 8, 8, 9, 30, tzinfo=ZoneInfo("Europe/Berlin"))
    with pytest.raises(ValueError, match="Maximale Läufe"):
        normalize_recurrence({"kind": "daily", "max_occurrences": 367}, scheduled_at=scheduled, timezone_name="Europe/Berlin")
    with pytest.raises(ValueError, match="Wiederholungsintervall"):
        normalize_recurrence({"kind": "weekly", "interval": 31, "max_occurrences": 2}, scheduled_at=scheduled, timezone_name="Europe/Berlin")


def test_dst_spring_gap_is_skipped_deterministically(tmp_path) -> None:
    anchor = datetime(2026, 3, 28, 2, 30, tzinfo=ZoneInfo("Europe/Berlin"))
    record = _fixture(tmp_path, scheduled=anchor, recurrence={"kind": "daily", "interval": 1, "max_occurrences": 3, "timezone": "Europe/Berlin", "dst_policy": "later", "catch_up_policy": "run_once"})
    assert occurrence_at_index(record, 2) is None
    item = next_valid_occurrence(record, after_index=1)
    assert item is not None
    index, when, skipped = item
    assert index == 3
    assert skipped == [2]
    assert when.date() == date(2026, 3, 30)


def test_dst_fall_back_uses_later_occurrence() -> None:
    resolved = resolve_local_wall_time(date(2026, 10, 25), time(2, 30), "Europe/Berlin", dst_policy="later")
    assert resolved is not None
    assert resolved.fold == 1
    assert resolved.astimezone(timezone.utc).hour == 1


def test_systemd_unit_uses_exact_utc_instant(tmp_path) -> None:
    scheduled = datetime(2026, 8, 8, 9, 30, tzinfo=ZoneInfo("Europe/Berlin"))
    record = _fixture(tmp_path, scheduled=scheduled)
    _service, timer = build_systemd_units(record)
    assert "OnCalendar=2026-08-08 07:30:00 UTC" in timer
    assert "Persistent=true" in timer


def test_catch_up_policy_skip_and_run_once(tmp_path) -> None:
    planned = datetime(2026, 8, 8, 9, 30, tzinfo=ZoneInfo("Europe/Berlin"))
    skip = _fixture(tmp_path / "skip", scheduled=planned, recurrence={"kind": "daily", "max_occurrences": 2, "catch_up_policy": "skip", "timezone": "Europe/Berlin"})
    assert should_run_occurrence(skip, now=planned + timedelta(minutes=5))[0] is False
    run = _fixture(tmp_path / "run", scheduled=planned, recurrence={"kind": "daily", "max_occurrences": 2, "catch_up_policy": "run_once", "timezone": "Europe/Berlin"})
    assert should_run_occurrence(run, now=planned + timedelta(minutes=5))[0] is True
    assert should_run_occurrence(run, now=planned + timedelta(hours=4))[0] is False


def test_recurring_completion_rearms_and_writes_history(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setattr("videobatch_fast.scheduler.shutil.which", lambda name: f"/usr/bin/{name}")
    scheduled = datetime(2026, 8, 8, 9, 30, tzinfo=ZoneInfo("Europe/Berlin"))
    record = _fixture(tmp_path / "data", scheduled=scheduled, recurrence={"kind": "daily", "max_occurrences": 2, "timezone": "Europe/Berlin"})
    save_schedule(record)
    updated = complete_schedule_occurrence(record["schedule_id"], "success", "ok", finished_at=scheduled + timedelta(minutes=2), run_systemctl=_systemctl_ok)
    assert updated["status"] == "pending"
    assert updated["occurrence_index"] == 2
    assert datetime.fromisoformat(updated["next_run_at"]).date() == date(2026, 8, 9)
    history = list_scheduler_history(project_path=Path(record["project_path"]))
    assert history[0]["outcome"] == "success"
    assert history[0]["occurrence_index"] == 1


def test_final_occurrence_stops_series(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setattr("videobatch_fast.scheduler._systemctl", lambda args, timeout=15.0: _systemctl_ok(args))
    scheduled = datetime(2026, 8, 8, 9, 30, tzinfo=ZoneInfo("Europe/Berlin"))
    record = _fixture(tmp_path / "data", scheduled=scheduled)
    save_schedule(record)
    updated = complete_schedule_occurrence(record["schedule_id"], "success", "done", finished_at=scheduled + timedelta(minutes=1))
    assert updated["status"] == "success"
    assert updated["next_run_at"] is None
    assert updated["occurrences_completed"] == 1


def test_conflict_retry_is_bounded_by_catch_up_deadline(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setattr("videobatch_fast.scheduler.shutil.which", lambda name: f"/usr/bin/{name}")
    planned = datetime(2026, 8, 8, 9, 30, tzinfo=ZoneInfo("Europe/Berlin"))
    record = _fixture(tmp_path / "data", scheduled=planned)
    record["max_lateness_minutes"] = 30
    record["schedule_fingerprint"] = schedule_fingerprint(record)
    save_schedule(record)
    assert defer_schedule_for_conflict(record["schedule_id"], now=planned + timedelta(minutes=5), retry_minutes=10, run_systemctl=_systemctl_ok) is True
    loaded = load_schedule(record["schedule_id"])
    assert datetime.fromisoformat(loaded["next_run_at"]) == planned + timedelta(minutes=15)
    assert defer_schedule_for_conflict(record["schedule_id"], now=planned + timedelta(minutes=25), retry_minutes=10, run_systemctl=_systemctl_ok) is False


def test_global_render_lease_blocks_parallel_process_contract(tmp_path) -> None:
    path = tmp_path / "render.lock"
    first = RenderExecutionLease(path)
    second = RenderExecutionLease(path)
    first.acquire()
    try:
        with pytest.raises(RenderBusyError):
            second.acquire()
    finally:
        first.release()
    second.acquire()
    second.release()


def test_multiple_plans_and_cancellation_history(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    first = _fixture(tmp_path / "data", scheduled=datetime(2026, 8, 8, 9, 30, tzinfo=ZoneInfo("Europe/Berlin")))
    second = _fixture(tmp_path / "data", scheduled=datetime(2026, 8, 8, 10, 30, tzinfo=ZoneInfo("Europe/Berlin")))
    save_schedule(first)
    save_schedule(second)
    assert len(list_schedules(project_path=Path(first["project_path"]))) == 2
    cancel_schedule(first["schedule_id"], run_systemctl=_systemctl_ok)
    history = list_scheduler_history(project_path=Path(first["project_path"]))
    assert any(item["outcome"] == "cancelled" for item in history)


def test_batch_runner_respects_global_render_lease(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    lease = RenderExecutionLease(render_lock_path())
    lease.acquire()
    try:
        runner = BatchRunner(lambda _event: None)
        with pytest.raises(RenderBusyError):
            runner.start([], BatchOptions(output_dir=tmp_path / "out"))
    finally:
        lease.release()


def test_ui_reports_render_busy_distinct_from_output_reservation() -> None:
    source = Path("src/videobatch_fast/ui.py").read_text(encoding="utf-8")
    assert '"RENDER_BUSY" if busy else "OUTPUT_RESERVATION_FAILED"' in source
    assert "anderer VideoBatch-Renderlauf" in source


def test_weekly_recurrence_keeps_local_wall_time_across_dst(tmp_path) -> None:
    anchor = datetime(2026, 10, 18, 2, 30, tzinfo=ZoneInfo("Europe/Berlin"))
    record = _fixture(
        tmp_path, scheduled=anchor,
        recurrence={"kind": "weekly", "interval": 1, "max_occurrences": 3, "timezone": "Europe/Berlin", "dst_policy": "later"},
    )
    second = occurrence_at_index(record, 2)
    third = occurrence_at_index(record, 3)
    assert second is not None and second.date() == date(2026, 10, 25) and second.fold == 1
    assert third is not None and third.hour == 2 and third.minute == 30


def test_legacy_scheduler_record_migrates_explicitly_to_one_time(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    scheduled = datetime(2026, 8, 8, 9, 30, tzinfo=ZoneInfo("Europe/Berlin"))
    record = _fixture(tmp_path / "data", scheduled=scheduled)
    legacy = dict(record)
    legacy["schema_version"] = 1
    for key in ("next_run_at", "occurrence_planned_at", "occurrence_index", "occurrences_completed", "recurrence"):
        legacy.pop(key, None)
    legacy["schedule_fingerprint"] = schedule_fingerprint(legacy)
    path = schedule_path(legacy["schedule_id"])
    path.write_text(json.dumps(legacy), encoding="utf-8")
    loaded = load_schedule(legacy["schedule_id"])
    assert loaded["schema_version"] == 3
    assert loaded["recurrence"]["kind"] == "once"
    assert loaded["next_run_at"] == legacy["scheduled_at"]
