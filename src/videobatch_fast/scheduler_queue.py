from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from .paths import state_dir
from .safe_io import atomic_write_json, exclusive_file_lock

QUEUE_SCHEMA_VERSION = 1
MAX_QUEUE_BYTES = 512 * 1024
MAX_QUEUE_ENTRIES = 200
ALLOWED_REASONS = {"render_conflict", "blackout", "resource", "reconcile"}


def queue_path() -> Path:
    path = state_dir() / "scheduler"
    path.mkdir(parents=True, exist_ok=True)
    return path / "queue.json"


def queue_lock_path() -> Path:
    return queue_path().with_suffix(".lock")


def _empty() -> dict[str, Any]:
    return {"schema_version": QUEUE_SCHEMA_VERSION, "entries": []}


def _validate_entry(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError("Queue-Eintrag ist ungültig.")
    schedule_id = str(raw.get("schedule_id", "")).strip().lower()
    if len(schedule_id) != 16 or any(char not in "0123456789abcdef" for char in schedule_id):
        raise ValueError("Queue-Eintrag enthält eine ungültige Scheduler-ID.")
    reason = str(raw.get("reason", "render_conflict"))
    if reason not in ALLOWED_REASONS:
        raise ValueError("Queue-Eintrag enthält einen unbekannten Grund.")
    priority = int(raw.get("priority", 50))
    if priority < 0 or priority > 100:
        raise ValueError("Queue-Priorität liegt außerhalb 0 bis 100.")
    queued_at = datetime.fromisoformat(str(raw["queued_at"]))
    eligible_at = datetime.fromisoformat(str(raw["eligible_at"]))
    deadline = datetime.fromisoformat(str(raw["deadline"]))
    return {
        "schedule_id": schedule_id,
        "priority": priority,
        "reason": reason,
        "detail": str(raw.get("detail", ""))[:500],
        "queued_at": queued_at.isoformat(timespec="seconds"),
        "eligible_at": eligible_at.isoformat(timespec="seconds"),
        "deadline": deadline.isoformat(timespec="seconds"),
    }


def _read_unlocked() -> dict[str, Any]:
    path = queue_path()
    if not path.exists():
        return _empty()
    if path.stat().st_size > MAX_QUEUE_BYTES:
        raise ValueError("Scheduler-Queue überschreitet das sichere Größenlimit.")
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or int(raw.get("schema_version", -1)) != QUEUE_SCHEMA_VERSION:
        raise ValueError("Scheduler-Queue besitzt eine unbekannte Schemaversion.")
    entries = raw.get("entries")
    if not isinstance(entries, list) or len(entries) > MAX_QUEUE_ENTRIES:
        raise ValueError("Scheduler-Queue ist ungültig oder zu groß.")
    return {"schema_version": QUEUE_SCHEMA_VERSION, "entries": [_validate_entry(item) for item in entries]}


def list_queue_entries() -> list[dict[str, Any]]:
    with exclusive_file_lock(queue_lock_path(), timeout_seconds=5.0):
        entries = list(_read_unlocked()["entries"])
    entries.sort(key=lambda item: (item["eligible_at"], -int(item["priority"]), item["queued_at"], item["schedule_id"]))
    return entries


def enqueue_schedule(
    schedule_id: str,
    *,
    priority: int,
    reason: str,
    detail: str,
    queued_at: datetime,
    eligible_at: datetime,
    deadline: datetime,
) -> dict[str, Any]:
    entry = _validate_entry({
        "schedule_id": schedule_id, "priority": priority, "reason": reason, "detail": detail,
        "queued_at": queued_at.isoformat(timespec="seconds"),
        "eligible_at": eligible_at.isoformat(timespec="seconds"),
        "deadline": deadline.isoformat(timespec="seconds"),
    })
    with exclusive_file_lock(queue_lock_path(), timeout_seconds=5.0):
        payload = _read_unlocked()
        existing = [item for item in payload["entries"] if item["schedule_id"] != entry["schedule_id"]]
        if len(existing) >= MAX_QUEUE_ENTRIES:
            raise RuntimeError("Scheduler-Queue ist voll.")
        existing.append(entry)
        atomic_write_json(queue_path(), {"schema_version": QUEUE_SCHEMA_VERSION, "entries": existing})
    return entry


def remove_queue_entry(schedule_id: str) -> bool:
    selected = str(schedule_id).strip().lower()
    with exclusive_file_lock(queue_lock_path(), timeout_seconds=5.0):
        payload = _read_unlocked()
        kept = [item for item in payload["entries"] if item["schedule_id"] != selected]
        if len(kept) == len(payload["entries"]):
            return False
        atomic_write_json(queue_path(), {"schema_version": QUEUE_SCHEMA_VERSION, "entries": kept})
        return True


def queue_position(schedule_id: str, *, now: datetime | None = None) -> tuple[int | None, int]:
    selected = str(schedule_id).strip().lower()
    current = now or datetime.now().astimezone()
    eligible = []
    for item in list_queue_entries():
        when = datetime.fromisoformat(item["eligible_at"])
        deadline = datetime.fromisoformat(item["deadline"])
        if current > deadline or current < when:
            continue
        eligible.append(item)
    eligible.sort(key=lambda item: (-int(item["priority"]), item["queued_at"], item["schedule_id"]))
    for index, item in enumerate(eligible, start=1):
        if item["schedule_id"] == selected:
            return index, len(eligible)
    return None, len(eligible)


def prune_queue(*, active_schedule_ids: set[str], now: datetime | None = None) -> int:
    current = now or datetime.now().astimezone()
    with exclusive_file_lock(queue_lock_path(), timeout_seconds=5.0):
        payload = _read_unlocked()
        kept = []
        for item in payload["entries"]:
            deadline = datetime.fromisoformat(item["deadline"])
            if item["schedule_id"] in active_schedule_ids and current <= deadline:
                kept.append(item)
        removed = len(payload["entries"]) - len(kept)
        if removed:
            atomic_write_json(queue_path(), {"schema_version": QUEUE_SCHEMA_VERSION, "entries": kept})
        return removed
