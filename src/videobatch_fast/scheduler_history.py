from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from .paths import state_dir
from .safe_io import atomic_write_json, exclusive_file_lock, fsync_directory

HISTORY_SCHEMA_VERSION = 1
MAX_HISTORY_ENTRIES = 500
MAX_HISTORY_FILE_BYTES = 512 * 1024


def history_dir() -> Path:
    path = state_dir() / "scheduler" / "history"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _history_lock() -> Path:
    return state_dir() / "scheduler" / ".history.lock"


def append_scheduler_history(
    record: dict[str, Any],
    *,
    outcome: str,
    detail: str,
    occurrence_index: int,
    planned_at: str,
    finished_at: str | None = None,
    result: dict[str, Any] | None = None,
) -> Path:
    timestamp = finished_at or datetime.now().astimezone().isoformat(timespec="seconds")
    entry = {
        "schema_version": HISTORY_SCHEMA_VERSION,
        "history_id": uuid.uuid4().hex[:16],
        "schedule_id": str(record.get("schedule_id", "")),
        "project_path": str(record.get("project_path", "")),
        "occurrence_index": int(occurrence_index),
        "planned_at": str(planned_at),
        "finished_at": timestamp,
        "outcome": str(outcome),
        "detail": str(detail)[:2000],
        "result": dict(result or {}),
    }
    filename = f"{timestamp.replace(':', '').replace('+', '_').replace('-', '')}_{entry['history_id']}.json"
    with exclusive_file_lock(_history_lock(), timeout_seconds=5.0):
        path = atomic_write_json(history_dir() / filename, entry)
        _prune_history_locked()
        return path


def _prune_history_locked() -> None:
    directory = history_dir()
    files = sorted(directory.glob("*.json"), key=lambda item: item.name, reverse=True)
    changed = False
    for path in files[MAX_HISTORY_ENTRIES:]:
        path.unlink(missing_ok=True)
        changed = True
    if changed:
        fsync_directory(directory)


def _read_entry(path: Path) -> dict[str, Any] | None:
    try:
        if path.stat().st_size > MAX_HISTORY_FILE_BYTES:
            return None
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return None
    if not isinstance(value, dict) or int(value.get("schema_version", -1)) != HISTORY_SCHEMA_VERSION:
        return None
    return value


def list_scheduler_history(*, project_path: Path | None = None, limit: int = 200) -> list[dict[str, Any]]:
    selected = Path(project_path).expanduser().resolve() if project_path is not None else None
    result: list[dict[str, Any]] = []
    maximum = max(1, min(int(limit), MAX_HISTORY_ENTRIES))
    for path in sorted(history_dir().glob("*.json"), key=lambda item: item.name, reverse=True):
        entry = _read_entry(path)
        if entry is None:
            continue
        if selected is not None:
            try:
                if Path(str(entry.get("project_path", ""))).expanduser().resolve() != selected:
                    continue
            except OSError:
                continue
        result.append(entry)
        if len(result) >= maximum:
            break
    return result
