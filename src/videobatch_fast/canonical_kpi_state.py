from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping

from .canonical_kpi import KPI_STATES, KpiSnapshot

KPI_KEYS = ("media", "queue", "effects", "scheduler")
_RECORD_FIELDS = (
    "value",
    "detail",
    "status",
    "state",
    "cause",
    "action_label",
    "recovery_action",
    "action_enabled",
)


def _bounded_text(value: Any, limit: int) -> str:
    return str(value or "").strip()[:limit]


def _valid_timestamp(value: Any) -> str:
    raw = _bounded_text(value, 64)
    if not raw:
        return ""
    try:
        datetime.fromisoformat(raw)
    except ValueError:
        return ""
    return raw


def normalize_kpi_history(raw: Any) -> dict[str, dict[str, Any]]:
    source = raw if isinstance(raw, Mapping) else {}
    result: dict[str, dict[str, Any]] = {}
    for key in KPI_KEYS:
        value = source.get(key)
        if not isinstance(value, Mapping):
            continue
        state = _bounded_text(value.get("state"), 24)
        if state not in KPI_STATES:
            continue
        result[key] = {
            "value": _bounded_text(value.get("value"), 120),
            "detail": _bounded_text(value.get("detail"), 600),
            "status": _bounded_text(value.get("status"), 120),
            "state": state,
            "cause": _bounded_text(value.get("cause"), 1200),
            "action_label": _bounded_text(value.get("action_label"), 120),
            "recovery_action": _bounded_text(value.get("recovery_action"), 80),
            "action_enabled": bool(value.get("action_enabled", True)),
            "updated_at": _valid_timestamp(value.get("updated_at")),
        }
    return result


def _snapshot_record(snapshot: KpiSnapshot, updated_at: str) -> dict[str, Any]:
    return {
        "value": snapshot.value[:120],
        "detail": snapshot.detail[:600],
        "status": snapshot.status[:120],
        "state": snapshot.state,
        "cause": snapshot.cause[:1200],
        "action_label": snapshot.action_label[:120],
        "recovery_action": snapshot.recovery_action[:80],
        "action_enabled": bool(snapshot.action_enabled),
        "updated_at": updated_at,
    }


def merge_kpi_history(
    history: Any,
    snapshots: Mapping[str, KpiSnapshot],
    *,
    now: str | None = None,
) -> tuple[dict[str, dict[str, Any]], bool]:
    normalized = normalize_kpi_history(history)
    timestamp = now or datetime.now().astimezone().isoformat(timespec="seconds")
    changed = False
    merged: dict[str, dict[str, Any]] = {}
    for key in KPI_KEYS:
        snapshot = snapshots[key]
        existing = normalized.get(key, {})
        candidate = _snapshot_record(snapshot, "")
        same = bool(existing) and all(existing.get(field) == candidate.get(field) for field in _RECORD_FIELDS)
        updated_at = str(existing.get("updated_at", "")) if same else timestamp
        record = _snapshot_record(snapshot, updated_at)
        merged[key] = record
        if record != existing:
            changed = True
    return merged, changed


def format_kpi_timestamp(value: str) -> str:
    try:
        parsed = datetime.fromisoformat(str(value))
    except ValueError:
        return "noch nicht gespeichert"
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone()
    return parsed.strftime("%d.%m.%Y · %H:%M:%S")
