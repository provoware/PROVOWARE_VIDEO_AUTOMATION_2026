from __future__ import annotations

import json
import shutil
import subprocess
import zipfile
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pytest

from videobatch_fast.models import BatchOptions
from videobatch_fast.scheduler import (
    build_systemd_units,
    create_schedule_record,
    load_schedule,
    register_systemd_schedule,
    save_schedule,
    schedule_fingerprint,
    schedule_path,
    systemd_user_dir,
)
from videobatch_fast.scheduler_export import export_scheduler_state
from videobatch_fast.scheduler_governance import (
    cleanup_completed_schedules,
    pause_schedule,
    priority_of,
    queue_schedule_wait,
    resume_schedule,
    update_priority,
)
from videobatch_fast.scheduler_history import list_scheduler_history
from videobatch_fast.scheduler_operations import build_operations_snapshot
from videobatch_fast.scheduler_policy import (
    active_blackout,
    default_scheduler_policy,
    normalize_scheduler_policy,
    resource_readiness,
    save_scheduler_policy,
)
from videobatch_fast.scheduler_queue import enqueue_schedule, list_queue_entries, queue_position
from videobatch_fast.scheduler_reconcile import reconcile_scheduler_state

TZ = ZoneInfo("Europe/Berlin")


def _ok(args: list[str]):
    return subprocess.CompletedProcess(["systemctl", *args], 0, "", "")


def _fixture(tmp_path: Path, *, when: datetime | None = None, priority: int = 50):
    tmp_path.mkdir(parents=True, exist_ok=True)
    project = tmp_path / "project.vbfast.json"
    audio = tmp_path / "a.mp3"
    image = tmp_path / "i.png"
    launcher = tmp_path / "videobatch.sh"
    audio.write_bytes(b"audio")
    image.write_bytes(b"image")
    project.write_text(json.dumps({"schema_version": 3, "audio_paths": [str(audio)], "media_paths": [str(image)]}), encoding="utf-8")
    launcher.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
    launcher.chmod(0o755)
    scheduled = when or datetime(2026, 8, 8, 9, 30, tzinfo=TZ)
    record = create_schedule_record(
        project_path=project,
        source_paths=[audio, image],
        options=BatchOptions(output_dir=tmp_path / "out"),
        scheduled_at=scheduled,
        recurrence={"kind": "daily", "max_occurrences": 3, "timezone": "Europe/Berlin"},
        timezone_name="Europe/Berlin",
        priority=priority,
        launcher=launcher,
        now=scheduled - timedelta(minutes=20),
    )
    return record, project


def test_schema2_schedule_migrates_to_governance_schema3(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    record, _project = _fixture(tmp_path / "data")
    legacy = dict(record)
    legacy["schema_version"] = 2
    legacy.pop("governance")
    legacy["schedule_fingerprint"] = schedule_fingerprint(legacy)
    path = schedule_path(legacy["schedule_id"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(legacy), encoding="utf-8")
    loaded = load_schedule(legacy["schedule_id"])
    assert loaded["schema_version"] == 3
    assert loaded["governance"] == {"priority": 50}


def test_priority_is_fingerprint_bound(tmp_path) -> None:
    record, _project = _fixture(tmp_path, priority=80)
    assert priority_of(record) == 80
    original = record["schedule_fingerprint"]
    record["governance"]["priority"] = 20
    assert schedule_fingerprint(record) != original


def test_priority_queue_orders_eligible_entries(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    now = datetime(2026, 8, 8, 9, 0, tzinfo=TZ)
    deadline = now + timedelta(hours=1)
    enqueue_schedule("aaaaaaaaaaaaaaaa", priority=20, reason="render_conflict", detail="low", queued_at=now, eligible_at=now, deadline=deadline)
    enqueue_schedule("bbbbbbbbbbbbbbbb", priority=80, reason="render_conflict", detail="high", queued_at=now + timedelta(seconds=1), eligible_at=now, deadline=deadline)
    assert queue_position("bbbbbbbbbbbbbbbb", now=now + timedelta(seconds=2))[0] == 1
    assert queue_position("aaaaaaaaaaaaaaaa", now=now + timedelta(seconds=2))[0] == 2


def test_blackout_window_crossing_midnight(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    policy = default_scheduler_policy()
    policy["blackout_windows"] = [{"days": [4], "start": "23:00", "end": "02:00", "timezone": "Europe/Berlin", "label": "Nachtwartung"}]
    saved = save_scheduler_policy(policy)
    assert saved.is_file()
    hit = active_blackout(datetime(2026, 8, 8, 1, 0, tzinfo=TZ))  # Saturday 01:00 belongs to Friday window
    assert hit is not None
    assert hit["label"] == "Nachtwartung"
    assert active_blackout(datetime(2026, 8, 8, 3, 0, tzinfo=TZ)) is None


def test_resource_floor_is_enforced(monkeypatch, tmp_path) -> None:
    policy = default_scheduler_policy()
    policy["min_free_output_bytes"] = 1024
    monkeypatch.setattr(shutil, "disk_usage", lambda _path: SimpleNamespace(total=2000, used=1500, free=500))
    ready, detail, metrics = resource_readiness(tmp_path, policy)
    assert ready is False
    assert "Freispeicher" in detail
    assert metrics["free_bytes"] == 500


def test_pause_and_resume_rearms_series(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setattr("videobatch_fast.scheduler._systemctl", lambda args, timeout=15.0: _ok(args))
    monkeypatch.setattr("videobatch_fast.scheduler.shutil.which", lambda name: f"/usr/bin/{name}")
    record, project = _fixture(tmp_path / "data")
    save_schedule(record)
    paused = pause_schedule(record["schedule_id"], now=datetime(2026, 8, 8, 8, 30, tzinfo=TZ))
    assert paused["status"] == "paused"
    resumed = resume_schedule(record["schedule_id"], now=datetime(2026, 8, 8, 8, 40, tzinfo=TZ), run_systemctl=_ok)
    assert resumed["status"] == "pending"
    history = list_scheduler_history(project_path=project)
    assert {item["outcome"] for item in history} >= {"paused", "resumed"}


def test_priority_update_refreshes_queued_entry(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    record, _project = _fixture(tmp_path / "data")
    save_schedule(record)
    now = datetime(2026, 8, 8, 9, 0, tzinfo=TZ)
    enqueue_schedule(record["schedule_id"], priority=50, reason="render_conflict", detail="busy", queued_at=now, eligible_at=now, deadline=now + timedelta(hours=1))
    updated = update_priority(record["schedule_id"], 80)
    assert updated["governance"]["priority"] == 80
    assert list_queue_entries()[0]["priority"] == 80


def test_queue_wait_sets_queued_status_and_exact_timer(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setattr("videobatch_fast.scheduler.shutil.which", lambda name: f"/usr/bin/{name}")
    record, _project = _fixture(tmp_path / "data")
    save_schedule(record)
    now = datetime(2026, 8, 8, 9, 0, tzinfo=TZ)
    assert queue_schedule_wait(record["schedule_id"], reason="render_conflict", detail="busy", now=now, eligible_at=now + timedelta(minutes=5), run_systemctl=_ok)
    loaded = load_schedule(record["schedule_id"])
    assert loaded["status"] == "queued"
    _service, timer = build_systemd_units(loaded)
    assert "OnCalendar=2026-08-08 07:05:00 UTC" in timer


def test_reconcile_repairs_manually_drifted_units(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setattr("videobatch_fast.scheduler.shutil.which", lambda name: f"/usr/bin/{name}")
    record, _project = _fixture(tmp_path / "data")
    save_schedule(record)
    service_name, timer_name = __import__("videobatch_fast.scheduler", fromlist=["unit_names"]).unit_names(record["schedule_id"])
    directory = systemd_user_dir()
    (directory / service_name).write_text("tampered", encoding="utf-8")
    (directory / timer_name).write_text("tampered", encoding="utf-8")

    def runner(args: list[str]):
        if args and args[0] in {"is-enabled", "is-active"}:
            return subprocess.CompletedProcess(["systemctl", *args], 1, "", "")
        return _ok(args)

    report = reconcile_scheduler_state(repair=True, run_systemctl=runner)
    assert report["issues"] >= 1
    assert report["repaired"] == 1
    expected_service, expected_timer = build_systemd_units(load_schedule(record["schedule_id"]))
    assert (directory / service_name).read_text(encoding="utf-8") == expected_service
    assert (directory / timer_name).read_text(encoding="utf-8") == expected_timer


def test_operations_snapshot_explains_queue_reason(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    record, project = _fixture(tmp_path / "data", priority=80)
    save_schedule(record)
    now = datetime(2026, 8, 8, 9, 0, tzinfo=TZ)
    enqueue_schedule(record["schedule_id"], priority=80, reason="blackout", detail="maintenance", queued_at=now, eligible_at=now + timedelta(minutes=10), deadline=now + timedelta(hours=1))
    snapshot = build_operations_snapshot(schedules=[record], project_path=project, now=now)
    assert snapshot["queue_size"] == 1
    assert "Wartungsfensters" in snapshot["rows"][0]["reason"]


def test_export_contains_hash_manifest_and_operational_state(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    record, project = _fixture(tmp_path / "data")
    save_schedule(record)
    path = export_scheduler_state(project, tmp_path / "exports", now=datetime(2026, 8, 8, 10, 0, tzinfo=TZ))
    with zipfile.ZipFile(path) as archive:
        names = set(archive.namelist())
        assert {"manifest.json", "schedules.json", "schedules.csv", "history.json", "queue.json", "policy.json"} <= names
        manifest = json.loads(archive.read("manifest.json"))
        assert manifest["files"]["schedules.json"]["sha256"]


def test_cleanup_removes_only_old_terminal_records(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setattr("videobatch_fast.scheduler._systemctl", lambda args, timeout=15.0: _ok(args))
    record, project = _fixture(tmp_path / "data")
    record["status"] = "success"
    record["next_run_at"] = None
    record["updated_at"] = "2026-01-01T00:00:00+01:00"
    save_schedule(record)
    report = cleanup_completed_schedules(project_path=project, older_than_days=30, keep_recent=0, now=datetime(2026, 8, 8, 10, 0, tzinfo=TZ))
    assert report["removed_count"] == 1
    assert not schedule_path(record["schedule_id"]).exists()


def test_policy_rejects_parallelism_above_global_render_contract() -> None:
    with pytest.raises(ValueError, match="exakt einen"):
        normalize_scheduler_policy({"max_parallel_renders": 2})

def test_pause_requested_during_running_applies_after_current_occurrence(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setattr("videobatch_fast.scheduler._systemctl", lambda args, timeout=15.0: _ok(args))
    record, _project = _fixture(tmp_path / "data")
    record["status"] = "running"
    save_schedule(record)
    running = pause_schedule(record["schedule_id"], now=datetime(2026, 8, 8, 9, 31, tzinfo=TZ))
    assert running["status"] == "running"
    assert running["pause_after_current"] is True
    from videobatch_fast.scheduler import complete_schedule_occurrence
    completed = complete_schedule_occurrence(
        record["schedule_id"], "success", "done", finished_at=datetime(2026, 8, 8, 9, 40, tzinfo=TZ)
    )
    assert completed["status"] == "paused"
    assert completed["next_run_at"] is not None
    assert "pause_after_current" not in completed


def test_cancel_during_running_cannot_rearm_after_worker_finishes(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setattr("videobatch_fast.scheduler._systemctl", lambda args, timeout=15.0: _ok(args))
    record, _project = _fixture(tmp_path / "data")
    record["status"] = "running"
    save_schedule(record)
    from videobatch_fast.scheduler import cancel_schedule, complete_schedule_occurrence
    cancelled = cancel_schedule(record["schedule_id"], run_systemctl=_ok)
    assert cancelled["status"] == "cancelled"
    assert cancelled["next_run_at"] is None
    finished = complete_schedule_occurrence(
        record["schedule_id"], "success", "current render finished", finished_at=datetime(2026, 8, 8, 9, 40, tzinfo=TZ)
    )
    assert finished["status"] == "cancelled"
    assert finished["next_run_at"] is None


def test_project_scoped_reconcile_does_not_prune_other_project_queue(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setattr("videobatch_fast.scheduler.shutil.which", lambda name: f"/usr/bin/{name}")
    first, first_project = _fixture(tmp_path / "first")
    second, _second_project = _fixture(tmp_path / "second")
    save_schedule(first)
    save_schedule(second)
    now = datetime(2026, 8, 8, 9, 0, tzinfo=TZ)
    for record in (first, second):
        enqueue_schedule(
            record["schedule_id"], priority=50, reason="render_conflict", detail="busy",
            queued_at=now, eligible_at=now, deadline=now + timedelta(hours=1),
        )
    runner = lambda args: subprocess.CompletedProcess(["systemctl", *args], 0, "", "")
    reconcile_scheduler_state(project_path=first_project, repair=False, run_systemctl=runner, now=now)
    assert {item["schedule_id"] for item in list_queue_entries()} == {first["schedule_id"], second["schedule_id"]}


def test_operations_queue_count_is_project_scoped(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    first, first_project = _fixture(tmp_path / "first")
    second, _second_project = _fixture(tmp_path / "second")
    save_schedule(first)
    save_schedule(second)
    now = datetime(2026, 8, 8, 9, 0, tzinfo=TZ)
    for record in (first, second):
        enqueue_schedule(record["schedule_id"], priority=50, reason="render_conflict", detail="busy", queued_at=now, eligible_at=now, deadline=now + timedelta(hours=1))
    snapshot = build_operations_snapshot(schedules=[first], project_path=first_project, now=now)
    assert snapshot["queue_size"] == 1

def test_governance_priority_boundaries_and_labels() -> None:
    from videobatch_fast.scheduler_contract import normalize_governance
    from videobatch_fast.scheduler_operations import priority_label
    assert priority_label(80) == "Hoch"
    assert priority_label(20) == "Niedrig"
    assert priority_label(50) == "Normal"
    with pytest.raises(ValueError, match="Priorität"):
        normalize_governance({"priority": 101})
