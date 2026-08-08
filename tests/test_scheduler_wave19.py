from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
import subprocess

import pytest

from videobatch_fast.models import BatchOptions
from videobatch_fast.scheduler import (
    build_systemd_units,
    cancel_schedule,
    create_schedule_record,
    load_schedule,
    register_systemd_schedule,
    save_schedule,
    source_snapshot_is_current,
    systemd_user_dir,
)
from videobatch_fast.scheduler_worker import execute_schedule


def _fixture_record(tmp_path: Path, *, now: datetime | None = None):
    tmp_path.mkdir(parents=True, exist_ok=True)
    project = tmp_path / "project.vbfast.json"
    source = tmp_path / "source.mp3"
    media = tmp_path / "image.png"
    launcher = tmp_path / "videobatch.sh"
    source.write_bytes(b"audio")
    media.write_bytes(b"image")
    project.write_text(
        '{"schema_version":3,"audio_paths":["%s"],"media_paths":["%s"],"updated_at":"initial"}'
        % (source, media),
        encoding="utf-8",
    )
    launcher.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
    launcher.chmod(0o755)
    base = now or datetime(2026, 8, 8, 1, 0, tzinfo=timezone.utc)
    record = create_schedule_record(
        project_path=project,
        source_paths=[source, media],
        options=BatchOptions(output_dir=tmp_path / "out"),
        scheduled_at=base + timedelta(minutes=15),
        launcher=launcher,
        now=base,
    )
    return record, project, source, media


def test_schedule_record_is_fingerprint_bound_and_rejects_mutation(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    record, _project, _source, _media = _fixture_record(tmp_path)
    save_schedule(record)
    loaded = load_schedule(record["schedule_id"])
    assert loaded["schedule_fingerprint"] == record["schedule_fingerprint"]
    path = Path(tmp_path / "state" / "VideoBatchFast" / "scheduler" / "schedules" / f"{record['schedule_id']}.json")
    payload = path.read_text(encoding="utf-8").replace('"inhibit_sleep": true', '"inhibit_sleep": false')
    path.write_text(payload, encoding="utf-8")
    with pytest.raises(ValueError, match="Fingerprint"):
        load_schedule(record["schedule_id"])


def test_schedule_blocks_render_changes_but_ignores_volatile_project_metadata(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    record, project, source, media = _fixture_record(tmp_path)
    assert source_snapshot_is_current(record)[0] is True

    # Volatile/autosaved metadata must not invalidate an otherwise identical render plan.
    payload = __import__("json").loads(project.read_text(encoding="utf-8"))
    payload["updated_at"] = "later"
    payload["canonical_kpi"] = {"history": [1, 2, 3]}
    project.write_text(__import__("json").dumps(payload), encoding="utf-8")
    assert source_snapshot_is_current(record)[0] is True

    # Ordered render inputs are semantic and therefore must invalidate the plan.
    payload["media_paths"] = [str(media), str(source)]
    project.write_text(__import__("json").dumps(payload), encoding="utf-8")
    ok, detail = source_snapshot_is_current(record)
    assert ok is False
    assert "Renderrelevante" in detail

    record2, _project2, source2, _media2 = _fixture_record(tmp_path / "second")
    source2.write_bytes(b"changed")
    ok, detail = source_snapshot_is_current(record2)
    assert ok is False
    assert "Quelle" in detail


def test_systemd_units_are_persistent_one_shot_and_inhibit_sleep(tmp_path) -> None:
    record, _project, _source, _media = _fixture_record(tmp_path)
    service, timer = build_systemd_units(record, inhibit_binary="/usr/bin/systemd-inhibit")
    assert "scheduler-run" in service
    assert "--what=sleep:shutdown" in service
    assert "NoNewPrivileges=yes" in service
    assert "OnCalendar=2026-08-08 01:15:00" in timer
    assert "AccuracySec=1s" in timer
    assert "Persistent=true" in timer


def test_register_and_cancel_user_timer_atomically(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setattr("videobatch_fast.scheduler.shutil.which", lambda name: f"/usr/bin/{name}")
    record, _project, _source, _media = _fixture_record(tmp_path)
    save_schedule(record)
    calls: list[list[str]] = []

    def fake_systemctl(args: list[str]):
        calls.append(list(args))
        return subprocess.CompletedProcess(["systemctl", *args], 0, "", "")

    registered = register_systemd_schedule(record, run_systemctl=fake_systemctl)
    service = systemd_user_dir() / registered["systemd"]["service"]
    timer = systemd_user_dir() / registered["systemd"]["timer"]
    assert service.is_file() and timer.is_file()
    assert ["daemon-reload"] in calls
    assert any(call[:2] == ["enable", "--now"] for call in calls)

    cancelled = cancel_schedule(record["schedule_id"], run_systemctl=fake_systemctl)
    assert cancelled["status"] == "cancelled"
    assert not service.exists() and not timer.exists()


def test_worker_blocks_stale_schedule_before_runner(monkeypatch) -> None:
    now = datetime(2026, 8, 8, 1, 15, tzinfo=timezone.utc)
    record = {
        "status": "pending",
        "scheduled_at": now.isoformat(),
        "max_lateness_minutes": 180,
        "project_path": "/tmp/project.json",
        "options": {},
        "after_action": "none",
    }
    dead_letters = []
    monkeypatch.setattr("videobatch_fast.scheduler_worker.load_schedule", lambda _id: record)
    monkeypatch.setattr("videobatch_fast.scheduler_worker.source_snapshot_is_current", lambda _record: (False, "Projekt wurde verändert."))
    monkeypatch.setattr("videobatch_fast.scheduler_worker.mark_dead_letter", lambda *args, **kwargs: dead_letters.append((args, kwargs)))
    assert execute_schedule("0123456789abcdef", now=now) == 13
    assert dead_letters[-1][1]["code"] == "source_changed"


def test_worker_success_records_terminal_result(monkeypatch, tmp_path) -> None:
    now = datetime(2026, 8, 8, 1, 15, tzinfo=timezone.utc)
    project = tmp_path / "project.json"
    project.write_text("{}", encoding="utf-8")
    record = {
        "status": "pending",
        "scheduled_at": now.isoformat(),
        "max_lateness_minutes": 180,
        "project_path": str(project),
        "options": {"output_dir": str(tmp_path / "out")},
        "after_action": "none",
    }
    updates = []
    job = object()

    class FakeRunner:
        def __init__(self, callback):
            self.callback = callback
        def start(self, jobs, options):
            assert jobs == [job]
            self.callback(SimpleNamespace(name="batch_finished", payload={
                "successes": 1, "failures": 0, "unprocessed": 0, "total": 1,
                "terminal_event": "batch_finished",
            }))
        def wait(self, timeout=None):
            return True

    monkeypatch.setattr("videobatch_fast.scheduler_worker.load_schedule", lambda _id: record)
    monkeypatch.setattr("videobatch_fast.scheduler_worker.source_snapshot_is_current", lambda _record: (True, "ok"))
    monkeypatch.setattr("videobatch_fast.scheduler_worker._project_payload", lambda _path: {"audio_paths": ["a"], "media_paths": ["b"]})
    monkeypatch.setattr("videobatch_fast.scheduler_worker.build_jobs", lambda *args, **kwargs: [job])
    monkeypatch.setattr("videobatch_fast.scheduler_worker.validate_pairs", lambda *args, **kwargs: [])
    monkeypatch.setattr("videobatch_fast.scheduler_worker.BatchRunner", FakeRunner)
    completed = []
    monkeypatch.setattr("videobatch_fast.scheduler_worker.update_schedule_status", lambda *args, **kwargs: updates.append((args, kwargs)))
    monkeypatch.setattr("videobatch_fast.scheduler_worker.complete_schedule_occurrence", lambda *args, **kwargs: completed.append((args, kwargs)))
    monkeypatch.setattr("videobatch_fast.scheduler_worker._after_success", lambda _action: (True, "Keine Energieaktion angefordert."))

    assert execute_schedule("0123456789abcdef", now=now) == 0
    assert any(args[1] == "running" for args, _kwargs in updates)
    assert completed[-1][0][1] == "success"
    assert completed[-1][1]["result"]["successes"] == 1
    assert completed[-1][1]["result"]["energy_action_ok"] is True


def test_worker_rejects_excessively_late_start(monkeypatch) -> None:
    planned = datetime(2026, 8, 8, 1, 0, tzinfo=timezone.utc)
    record = {
        "status": "pending",
        "scheduled_at": planned.isoformat(),
        "max_lateness_minutes": 30,
    }
    completed = []
    record["recurrence"] = {"catch_up_policy": "run_once"}
    monkeypatch.setattr("videobatch_fast.scheduler_worker.load_schedule", lambda _id: record)
    monkeypatch.setattr("videobatch_fast.scheduler_worker.complete_schedule_occurrence", lambda *args, **kwargs: completed.append((args, kwargs)))
    assert execute_schedule("0123456789abcdef", now=planned + timedelta(minutes=31)) == 12
    assert completed[-1][0][1] == "missed"


def test_schedule_rejects_symlinked_inputs_and_nonexecutable_launcher(tmp_path) -> None:
    real = tmp_path / "real"
    record, project, source, media = _fixture_record(real)
    link = tmp_path / "project-link.json"
    link.symlink_to(project)
    with pytest.raises(ValueError, match="symbolischer Link"):
        create_schedule_record(
            project_path=link,
            source_paths=[source, media],
            options=BatchOptions(output_dir=tmp_path / "out"),
            scheduled_at=datetime(2026, 8, 8, 1, 30, tzinfo=timezone.utc),
            launcher=real / "videobatch.sh",
            now=datetime(2026, 8, 8, 1, 0, tzinfo=timezone.utc),
        )

    launcher = real / "videobatch.sh"
    launcher.chmod(0o644)
    with pytest.raises(ValueError, match="nicht ausführbar"):
        create_schedule_record(
            project_path=project,
            source_paths=[source, media],
            options=BatchOptions(output_dir=tmp_path / "out"),
            scheduled_at=datetime(2026, 8, 8, 1, 30, tzinfo=timezone.utc),
            launcher=launcher,
            now=datetime(2026, 8, 8, 1, 0, tzinfo=timezone.utc),
        )


def test_successful_render_is_not_failed_by_optional_energy_action(monkeypatch, tmp_path) -> None:
    now = datetime(2026, 8, 8, 1, 15, tzinfo=timezone.utc)
    project = tmp_path / "project.json"
    project.write_text("{}", encoding="utf-8")
    record = {
        "status": "pending", "scheduled_at": now.isoformat(), "max_lateness_minutes": 180,
        "project_path": str(project), "options": {"output_dir": str(tmp_path / "out")}, "after_action": "suspend",
    }
    updates = []
    job = object()

    class FakeRunner:
        def __init__(self, callback): self.callback = callback
        def start(self, jobs, options):
            self.callback(SimpleNamespace(name="batch_finished", payload={
                "successes": 1, "failures": 0, "unprocessed": 0, "total": 1, "terminal_event": "batch_finished",
            }))
        def wait(self, timeout=None): return True

    monkeypatch.setattr("videobatch_fast.scheduler_worker.load_schedule", lambda _id: record)
    monkeypatch.setattr("videobatch_fast.scheduler_worker.source_snapshot_is_current", lambda _record: (True, "ok"))
    monkeypatch.setattr("videobatch_fast.scheduler_worker._project_payload", lambda _path: {"audio_paths": ["a"], "media_paths": ["b"]})
    monkeypatch.setattr("videobatch_fast.scheduler_worker.build_jobs", lambda *args, **kwargs: [job])
    monkeypatch.setattr("videobatch_fast.scheduler_worker.validate_pairs", lambda *args, **kwargs: [])
    monkeypatch.setattr("videobatch_fast.scheduler_worker.BatchRunner", FakeRunner)
    completed = []
    monkeypatch.setattr("videobatch_fast.scheduler_worker.update_schedule_status", lambda *args, **kwargs: updates.append((args, kwargs)))
    monkeypatch.setattr("videobatch_fast.scheduler_worker.complete_schedule_occurrence", lambda *args, **kwargs: completed.append((args, kwargs)))
    monkeypatch.setattr("videobatch_fast.scheduler_worker._after_success", lambda _action: (False, "Energiesparen nicht möglich."))

    assert execute_schedule("0123456789abcdef", now=now) == 0
    assert completed[-1][0][1] == "success"
    assert completed[-1][1]["result"]["energy_action_ok"] is False
