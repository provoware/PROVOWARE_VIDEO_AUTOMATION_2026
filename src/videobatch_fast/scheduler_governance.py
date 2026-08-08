from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable
import subprocess

from .safe_io import atomic_write_json, exclusive_file_lock, fsync_directory
from .scheduler import (
    DEFAULT_MAX_LATENESS_MINUTES, FINAL_STATUSES,
    load_schedule,
    register_systemd_schedule,
    remove_finished_units,
    schedule_fingerprint,
    schedule_path, schedules_dir,
    scheduler_lock_path,
)
from .scheduler_history import append_scheduler_history
from .scheduler_policy import active_blackout, load_scheduler_policy, resource_readiness
from .scheduler_queue import enqueue_schedule, list_queue_entries, queue_position, remove_queue_entry
from .scheduler_recurrence import next_valid_occurrence, should_run_occurrence

ACTIVE_STATUSES = {"pending", "queued", "running"}


def schedule_deadline(record: dict[str, Any]) -> datetime:
    planned = datetime.fromisoformat(str(record.get("occurrence_planned_at") or record.get("scheduled_at")))
    return planned + timedelta(minutes=int(record.get("max_lateness_minutes", DEFAULT_MAX_LATENESS_MINUTES)))


def priority_of(record: dict[str, Any]) -> int:
    governance = record.get("governance") if isinstance(record.get("governance"), dict) else {}
    return int(governance.get("priority", 50) or 50)


def update_priority(schedule_id: str, priority: int) -> dict[str, Any]:
    selected = int(priority)
    if selected < 0 or selected > 100:
        raise ValueError("Scheduler-Priorität muss zwischen 0 und 100 liegen.")
    with exclusive_file_lock(scheduler_lock_path(), timeout_seconds=5.0):
        record = load_schedule(schedule_id)
        record["governance"] = {"priority": selected}
        record["schedule_fingerprint"] = schedule_fingerprint(record)
        record["updated_at"] = datetime.now().astimezone().isoformat(timespec="seconds")
        atomic_write_json(schedule_path(schedule_id), record)
    # Refresh an existing queue entry so ordering follows the new priority.
    for entry in list_queue_entries():
        if entry["schedule_id"] == schedule_id:
            enqueue_schedule(
                schedule_id, priority=selected, reason=entry["reason"], detail=entry["detail"],
                queued_at=datetime.fromisoformat(entry["queued_at"]),
                eligible_at=datetime.fromisoformat(entry["eligible_at"]), deadline=datetime.fromisoformat(entry["deadline"]),
            )
            break
    return record


def _write_status(record: dict[str, Any], status: str, detail: str, *, now: datetime) -> dict[str, Any]:
    record["status"] = status
    record["status_detail"] = detail[:1000]
    record["updated_at"] = now.isoformat(timespec="seconds")
    atomic_write_json(schedule_path(str(record["schedule_id"])), record)
    return record


def pause_schedule(schedule_id: str, *, now: datetime | None = None) -> dict[str, Any]:
    current = now or datetime.now().astimezone()
    with exclusive_file_lock(scheduler_lock_path(), timeout_seconds=5.0):
        record = load_schedule(schedule_id)
        status = str(record.get("status"))
        if status == "paused":
            return record
        if status == "running":
            requested = not bool(record.get("pause_after_current", False))
            record["pause_after_current"] = requested
            detail = "Serie pausiert nach dem aktuellen Renderlauf." if requested else "Pause nach aktuellem Lauf wurde aufgehoben."
            return _write_status(record, "running", detail, now=current)
        if not record.get("next_run_at"):
            raise ValueError("Abgeschlossene Serie kann nicht pausiert werden.")
        append_scheduler_history(
            record, outcome="paused", detail="Serie wurde vom Nutzer pausiert.",
            occurrence_index=int(record.get("occurrence_index", 1)),
            planned_at=str(record.get("occurrence_planned_at") or record["scheduled_at"]),
            finished_at=current.isoformat(timespec="seconds"),
        )
        _write_status(record, "paused", "Serie pausiert; es werden keine Timer gestartet.", now=current)
    remove_queue_entry(schedule_id)
    remove_finished_units(schedule_id)
    return record


def _advance_expired_paused(record: dict[str, Any], *, now: datetime) -> bool:
    should_run, _detail = should_run_occurrence(record, now=now)
    if should_run:
        record["next_run_at"] = (now + timedelta(seconds=15)).isoformat(timespec="seconds")
        return True
    while True:
        index = int(record.get("occurrence_index", 1))
        append_scheduler_history(
            record, outcome="paused_skipped", detail="Termin lag während der Pause außerhalb des Catch-up-Fensters.",
            occurrence_index=index, planned_at=str(record.get("occurrence_planned_at") or record["scheduled_at"]),
            finished_at=now.isoformat(timespec="seconds"),
        )
        next_item = next_valid_occurrence(record, after_index=index)
        if next_item is None:
            record["next_run_at"] = None
            record["occurrences_completed"] = index
            record["status"] = "missed"
            record["status_detail"] = "Serie endete während der Pause; keine zulässigen Termine mehr vorhanden."
            return False
        next_index, next_when, skipped = next_item
        for skipped_index in skipped:
            append_scheduler_history(
                record, outcome="dst_skipped", detail="DST-Termin während Resume-Prüfung übersprungen.",
                occurrence_index=skipped_index, planned_at=f"DST-skip:{skipped_index}",
                finished_at=now.isoformat(timespec="seconds"),
            )
        record["occurrence_index"] = next_index
        record["occurrences_completed"] = next_index - 1
        record["occurrence_planned_at"] = next_when.isoformat(timespec="seconds")
        record["next_run_at"] = next_when.isoformat(timespec="seconds")
        if next_when > now + timedelta(seconds=10):
            return True


def resume_schedule(
    schedule_id: str,
    *,
    now: datetime | None = None,
    run_systemctl: Callable[[list[str]], subprocess.CompletedProcess[str]] | None = None,
) -> dict[str, Any]:
    current = now or datetime.now().astimezone()
    with exclusive_file_lock(scheduler_lock_path(), timeout_seconds=5.0):
        record = load_schedule(schedule_id)
        if str(record.get("status")) != "paused":
            raise ValueError("Nur eine pausierte Serie kann fortgesetzt werden.")
        has_next = _advance_expired_paused(record, now=current)
        append_scheduler_history(
            record, outcome="resumed" if has_next else "resume_finished",
            detail="Serie wurde fortgesetzt." if has_next else "Serie besitzt nach der Pause keinen zulässigen Folgetermin.",
            occurrence_index=int(record.get("occurrence_index", 1)),
            planned_at=str(record.get("occurrence_planned_at") or record["scheduled_at"]),
            finished_at=current.isoformat(timespec="seconds"),
        )
        if has_next:
            _write_status(record, "pending", "Serie wurde fortgesetzt und neu aktiviert.", now=current)
        else:
            _write_status(record, "missed", record["status_detail"], now=current)
    if has_next:
        return register_systemd_schedule(record, run_systemctl=run_systemctl)
    remove_finished_units(schedule_id)
    return record


def queue_schedule_wait(
    schedule_id: str,
    *,
    reason: str,
    detail: str,
    now: datetime,
    eligible_at: datetime,
    run_systemctl: Callable[[list[str]], subprocess.CompletedProcess[str]] | None = None,
) -> bool:
    record = load_schedule(schedule_id)
    deadline = schedule_deadline(record)
    if eligible_at > deadline:
        return False
    entry = enqueue_schedule(
        schedule_id,
        priority=priority_of(record),
        reason=reason,
        detail=detail,
        queued_at=now,
        eligible_at=eligible_at,
        deadline=deadline,
    )
    with exclusive_file_lock(scheduler_lock_path(), timeout_seconds=5.0):
        record = load_schedule(schedule_id)
        record["status"] = "queued"
        record["status_detail"] = str(detail)[:1000]
        record["next_run_at"] = entry["eligible_at"]
        result = record.get("result", {}) if isinstance(record.get("result"), dict) else {}
        result["queue_reason"] = reason
        result["queue_count"] = int(result.get("queue_count", 0)) + 1
        record["result"] = result
        record["updated_at"] = now.isoformat(timespec="seconds")
        atomic_write_json(schedule_path(schedule_id), record)
    register_systemd_schedule(record, run_systemctl=run_systemctl)
    return True



def rearm_queued_schedule(
    schedule_id: str,
    *,
    when: datetime,
    detail: str,
    now: datetime,
    run_systemctl: Callable[[list[str]], subprocess.CompletedProcess[str]] | None = None,
) -> dict[str, Any]:
    with exclusive_file_lock(scheduler_lock_path(), timeout_seconds=5.0):
        record = load_schedule(schedule_id)
        if when > schedule_deadline(record):
            raise ValueError("Queue-Wartezeit überschreitet die Deadline dieses Termins.")
        record["status"] = "queued"
        record["next_run_at"] = when.isoformat(timespec="seconds")
        record["status_detail"] = str(detail)[:1000]
        record["updated_at"] = now.isoformat(timespec="seconds")
        atomic_write_json(schedule_path(schedule_id), record)
    return register_systemd_schedule(record, run_systemctl=run_systemctl)

def queue_turn(schedule_id: str, *, now: datetime) -> tuple[bool, str, datetime | None]:
    entry = next((item for item in list_queue_entries() if item["schedule_id"] == schedule_id), None)
    if entry is None:
        return True, "Kein Queue-Eintrag vorhanden.", None
    deadline = datetime.fromisoformat(entry["deadline"])
    eligible_at = datetime.fromisoformat(entry["eligible_at"])
    if now > deadline:
        return False, "Queue-Deadline ist überschritten.", None
    if now < eligible_at:
        return False, "Queue-Eintrag ist noch nicht freigegeben.", eligible_at
    position, total = queue_position(schedule_id, now=now)
    if position == 1:
        return True, f"Queue-Priorität erlaubt den Start (1/{total}).", None
    if position is None:
        return False, "Queue-Eintrag ist derzeit nicht ausführbar.", now + timedelta(minutes=1)
    return False, f"Höher priorisierte Schedulerläufe warten ({position}/{total}).", now + timedelta(minutes=1)


def scheduler_preflight_wait(record: dict[str, Any], *, now: datetime) -> tuple[str | None, str, datetime | None, dict[str, Any]]:
    policy = load_scheduler_policy()
    blackout = active_blackout(now, policy)
    if blackout:
        return "blackout", f"Wartungsfenster aktiv: {blackout['label']}", datetime.fromisoformat(blackout["active_until"]), blackout
    options = record.get("options") if isinstance(record.get("options"), dict) else {}
    from pathlib import Path
    ready, detail, metrics = resource_readiness(Path(str(options.get("output_dir", "."))), policy)
    if not ready:
        eligible = now + timedelta(minutes=int(policy["conflict_retry_minutes"]))
        return "resource", detail, eligible, metrics
    return None, "Governance-Preflight bestanden.", None, metrics


def cleanup_completed_schedules(
    *,
    project_path: Path | None = None,
    older_than_days: int = 30,
    keep_recent: int = 50,
    now: datetime | None = None,
) -> dict[str, Any]:
    from .scheduler import list_schedules
    current = now or datetime.now().astimezone()
    age = max(1, min(int(older_than_days), 3650))
    keep = max(0, min(int(keep_recent), 500))
    terminal = [
        item for item in list_schedules(project_path=project_path)
        if str(item.get("status")) in FINAL_STATUSES and not item.get("next_run_at")
    ]
    terminal.sort(key=lambda item: str(item.get("updated_at") or item.get("created_at") or ""), reverse=True)
    removed: list[str] = []
    cutoff = current - timedelta(days=age)
    for record in terminal[keep:]:
        raw = str(record.get("updated_at") or record.get("created_at") or "")
        try:
            timestamp = datetime.fromisoformat(raw)
        except ValueError:
            continue
        if timestamp.astimezone(current.tzinfo) > cutoff:
            continue
        schedule_id = str(record["schedule_id"])
        remove_queue_entry(schedule_id)
        remove_finished_units(schedule_id)
        try:
            schedule_path(schedule_id).unlink(missing_ok=True)
            removed.append(schedule_id)
        except OSError:
            continue
    if removed:
        fsync_directory(schedules_dir())
    return {"removed": removed, "removed_count": len(removed), "retained_terminal": len(terminal) - len(removed)}
