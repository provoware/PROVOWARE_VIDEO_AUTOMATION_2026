from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from .safe_io import atomic_write_json, exclusive_file_lock
from .scheduler import load_schedule, remove_finished_units, schedule_path, scheduler_lock_path
from .scheduler_history import append_scheduler_history
from .scheduler_queue import remove_queue_entry


def mark_dead_letter(
    schedule_id: str,
    *,
    code: str,
    detail: str,
    next_action: str,
    now: datetime | None = None,
) -> dict[str, Any]:
    current = now or datetime.now().astimezone()
    with exclusive_file_lock(scheduler_lock_path(), timeout_seconds=5.0):
        record = load_schedule(schedule_id)
        planned_at = str(record.get("occurrence_planned_at") or record.get("scheduled_at") or "")
        append_scheduler_history(
            record,
            outcome="dead_letter",
            detail=detail,
            occurrence_index=int(record.get("occurrence_index", 1) or 1),
            planned_at=planned_at,
            finished_at=current.isoformat(timespec="seconds"),
            result={"dead_letter_code": str(code), "next_action": str(next_action)[:500]},
        )
        record["status"] = "dead_letter"
        record["status_detail"] = str(detail)[:1000]
        record["next_run_at"] = None
        record["dead_letter"] = {
            "code": str(code)[:80],
            "detail": str(detail)[:1000],
            "next_action": str(next_action)[:500],
            "created_at": current.isoformat(timespec="seconds"),
        }
        record["updated_at"] = current.isoformat(timespec="seconds")
        atomic_write_json(schedule_path(schedule_id), record)
    remove_queue_entry(schedule_id)
    remove_finished_units(schedule_id)
    return record


def dead_letter_summary(record: dict[str, Any]) -> dict[str, str] | None:
    if str(record.get("status")) != "dead_letter":
        return None
    raw = record.get("dead_letter") if isinstance(record.get("dead_letter"), dict) else {}
    return {
        "code": str(raw.get("code") or "unknown"),
        "detail": str(raw.get("detail") or record.get("status_detail") or "Dauerhaft nicht ausführbarer Termin."),
        "next_action": str(raw.get("next_action") or "Zeitplan prüfen, korrigieren oder neu anlegen."),
    }
