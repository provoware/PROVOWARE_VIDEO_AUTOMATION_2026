from __future__ import annotations

import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from .scheduler_forecast import estimate_schedule, load_render_samples
from .scheduler_policy import active_blackout, load_scheduler_policy
from .scheduler_recurrence import occurrence_at_index

ALLOWED_HORIZONS = {24, 48, 168}
_ACTIVE = {"pending", "queued", "running", "paused"}


def _priority(record: dict[str, Any]) -> int:
    governance = record.get("governance") if isinstance(record.get("governance"), dict) else {}
    return int(governance.get("priority", 50) or 50)


def _candidates(record: dict[str, Any], *, now: datetime, horizon_end: datetime) -> list[dict[str, Any]]:
    status = str(record.get("status", "pending"))
    if status not in _ACTIVE:
        return []
    recurrence = record.get("recurrence") if isinstance(record.get("recurrence"), dict) else {}
    maximum = int(recurrence.get("max_occurrences", 1) or 1)
    first = int(record.get("occurrence_index", 1) or 1)
    result: list[dict[str, Any]] = []
    for index in range(first, maximum + 1):
        if index == first and record.get("occurrence_planned_at"):
            planned = datetime.fromisoformat(str(record["occurrence_planned_at"]))
        else:
            planned = occurrence_at_index(record, index)
        if planned is None:
            result.append({"schedule_id": record["schedule_id"], "occurrence_index": index, "status": "dst_skipped"})
            continue
        planned = planned.astimezone(now.tzinfo)
        if planned > horizon_end:
            break
        if planned + timedelta(minutes=int(record.get("max_lateness_minutes", 180))) < now:
            continue
        result.append({
            "schedule_id": str(record["schedule_id"]),
            "occurrence_index": index,
            "planned_at": planned,
            "priority": _priority(record),
            "record": record,
            "status": "paused" if status == "paused" else "candidate",
        })
    return result


def _output_free_bytes(record: dict[str, Any]) -> int | None:
    options = record.get("options") if isinstance(record.get("options"), dict) else {}
    raw = Path(str(options.get("output_dir", "."))).expanduser()
    candidate = raw
    while not candidate.exists() and candidate != candidate.parent:
        candidate = candidate.parent
    try:
        return int(shutil.disk_usage(candidate).free)
    except OSError:
        return None


def _after_blackout(when: datetime, policy: dict[str, Any]) -> tuple[datetime, dict[str, Any] | None]:
    current = when
    last: dict[str, Any] | None = None
    for _ in range(4):
        blackout = active_blackout(current, policy)
        if not blackout:
            return current, last
        last = blackout
        current = datetime.fromisoformat(str(blackout["active_until"])).astimezone(when.tzinfo)
    return current, last


def simulate_scheduler(
    schedules: list[dict[str, Any]],
    *,
    horizon_hours: int,
    now: datetime | None = None,
    samples: list[dict[str, Any]] | None = None,
    policy: dict[str, Any] | None = None,
) -> dict[str, Any]:
    horizon = int(horizon_hours)
    if horizon not in ALLOWED_HORIZONS:
        raise ValueError("Simulation unterstützt ausschließlich 24, 48 oder 168 Stunden.")
    current = now if now is not None else datetime.now().astimezone()
    if current.tzinfo is None:
        current = current.astimezone()
    end = current + timedelta(hours=horizon)
    history = list(samples if samples is not None else load_render_samples())
    canonical_policy = policy or load_scheduler_policy()
    candidates: list[dict[str, Any]] = []
    forecasts: dict[str, dict[str, Any]] = {}
    for record in schedules:
        schedule_id = str(record.get("schedule_id", ""))
        forecasts[schedule_id] = estimate_schedule(record, samples=history)
        candidates.extend(_candidates(record, now=current, horizon_end=end))
    candidates.sort(key=lambda item: (item.get("planned_at", end), -int(item.get("priority", 50)), item["schedule_id"], item["occurrence_index"]))
    renderer_free_at = current
    renderer_uncertain = False
    events: list[dict[str, Any]] = []
    for item in candidates:
        if item["status"] == "dst_skipped":
            events.append({**item, "projected_start": None, "projected_end": None, "reason": "DST-Termin existiert lokal nicht."})
            continue
        record = item.pop("record")
        planned = item["planned_at"]
        forecast = forecasts[item["schedule_id"]]
        if item["status"] == "paused":
            events.append({**item, "planned_at": planned.isoformat(), "projected_start": None, "projected_end": None, "reason": "Serie ist pausiert.", "forecast": forecast})
            continue
        ready = max(current, planned)
        ready, blackout = _after_blackout(ready, canonical_policy)
        constraints: list[str] = []
        if blackout:
            constraints.append(f"Wartungsfenster: {blackout.get('label', 'Wartung')}")
        if renderer_uncertain and renderer_free_at > ready:
            events.append({
                **item, "planned_at": planned.isoformat(), "projected_start": None, "projected_end": None,
                "reason": "Startzeit ist wegen fehlender Laufzeitdaten eines vorherigen Jobs unsicher.",
                "constraints": constraints + ["Vorherige ETA unbekannt"], "forecast": forecast,
            })
            continue
        start = max(ready, renderer_free_at)
        if start > ready:
            constraints.append("Render-Slot durch vorherigen Lauf belegt")
        deadline = planned + timedelta(minutes=int(record.get("max_lateness_minutes", 180)))
        if start > deadline:
            events.append({
                **item, "planned_at": planned.isoformat(), "projected_start": None, "projected_end": None,
                "reason": "Prognostizierter Start liegt hinter der Catch-up-Deadline.", "constraints": constraints,
                "forecast": forecast, "status": "missed",
            })
            continue
        runtime = forecast.get("runtime_seconds_p50")
        if runtime is None:
            projected_end = None
            renderer_free_at = start
            renderer_uncertain = True
        else:
            projected_end = start + timedelta(seconds=float(runtime))
            renderer_free_at = projected_end
            renderer_uncertain = False
        free_bytes = _output_free_bytes(record)
        output_bytes = forecast.get("output_bytes_p75")
        storage_risk = bool(free_bytes is not None and output_bytes is not None and free_bytes - int(output_bytes) < int(canonical_policy["min_free_output_bytes"]))
        if storage_risk:
            constraints.append("Speicherprognose unterschreitet Freispeicherreserve")
        events.append({
            **item,
            "planned_at": planned.isoformat(timespec="seconds"),
            "projected_start": start.isoformat(timespec="seconds"),
            "projected_end": projected_end.isoformat(timespec="seconds") if projected_end else None,
            "reason": " · ".join(constraints) if constraints else "Keine prognostizierte Blockade.",
            "constraints": constraints,
            "forecast": forecast,
            "storage_free_bytes": free_bytes,
            "storage_risk": storage_risk,
            "status": "risk" if storage_risk else "forecast",
        })
    return {
        "generated_at": current.isoformat(timespec="seconds"),
        "horizon_hours": horizon,
        "horizon_end": end.isoformat(timespec="seconds"),
        "event_count": len(events),
        "risk_count": sum(1 for item in events if item.get("status") in {"risk", "missed"}),
        "events": events,
    }
