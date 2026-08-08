from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from .scheduler_calibration import build_forecast_quality_report, list_forecast_observations
from .scheduler_diagnostics import diagnose_schedule
from .scheduler_forecast import estimate_schedule, load_render_samples
from .scheduler_history import list_scheduler_history
from .scheduler_policy import active_blackout, load_scheduler_policy
from .scheduler_queue import list_queue_entries
from .scheduler_simulation import ALLOWED_HORIZONS, simulate_scheduler


def priority_label(value: int) -> str:
    priority = int(value)
    if priority >= 80:
        return "Hoch"
    if priority <= 20:
        return "Niedrig"
    return "Normal"


def schedule_priority(record: dict[str, Any]) -> int:
    governance = record.get("governance") if isinstance(record.get("governance"), dict) else {}
    return int(governance.get("priority", 50) or 50)


def operation_reason(record: dict[str, Any], queue_entry: dict[str, Any] | None = None) -> str:
    status = str(record.get("status", "pending"))
    if queue_entry is not None:
        labels = {
            "render_conflict": "Wartet auf freien Render-Slot",
            "blackout": "Wartet auf Ende des Wartungsfensters",
            "resource": "Wartet auf ausreichende Ressourcen",
            "reconcile": "Wartet nach Systemabgleich",
        }
        return labels.get(str(queue_entry.get("reason")), str(queue_entry.get("detail", "Queue")))
    if status == "paused":
        return "Serie wurde pausiert"
    if status == "running":
        return "Renderlauf ist aktiv"
    if status == "dead_letter":
        return str(record.get("status_detail") or "Dauerhaft nicht ausführbarer Termin")
    if status == "pending":
        return str(record.get("status_detail") or "Wartet auf nächsten Termin")
    return str(record.get("status_detail") or status)


def _first_simulation_event(simulation: dict[str, Any], schedule_id: str) -> dict[str, Any] | None:
    for event in simulation.get("events", []):
        if str(event.get("schedule_id")) == schedule_id:
            return event
    return None


def build_operations_snapshot(
    *,
    schedules: list[dict[str, Any]],
    project_path: Path | None = None,
    now: datetime | None = None,
    horizon_hours: int = 24,
) -> dict[str, Any]:
    current = now or datetime.now().astimezone()
    horizon = int(horizon_hours)
    if horizon not in ALLOWED_HORIZONS:
        raise ValueError("Operations-Prognose unterstützt nur 24, 48 oder 168 Stunden.")
    schedule_ids = {str(record.get("schedule_id", "")) for record in schedules}
    queue = {item["schedule_id"]: item for item in list_queue_entries() if item["schedule_id"] in schedule_ids}
    samples = load_render_samples()
    simulation = simulate_scheduler(schedules, horizon_hours=horizon, now=current, samples=samples)
    rows: list[dict[str, Any]] = []
    for record in schedules:
        schedule_id = str(record.get("schedule_id", ""))
        entry = queue.get(schedule_id)
        forecast = estimate_schedule(record, samples=samples)
        simulation_event = _first_simulation_event(simulation, schedule_id)
        diagnostic = diagnose_schedule(record, now=current, queue_entry=entry, simulation_event=simulation_event)
        rows.append({
            "schedule_id": schedule_id,
            "status": str(record.get("status", "pending")),
            "priority": schedule_priority(record),
            "next_run_at": record.get("next_run_at"),
            "queue_reason": entry.get("reason") if entry else None,
            "queue_eligible_at": entry.get("eligible_at") if entry else None,
            "reason": diagnostic["reason"],
            "next_action": diagnostic["next_action"],
            "diagnostic_code": diagnostic["code"],
            "diagnostic_severity": diagnostic["severity"],
            "occurrence_index": int(record.get("occurrence_index", 1) or 1),
            "max_occurrences": int((record.get("recurrence") or {}).get("max_occurrences", 1) or 1),
            "forecast": forecast,
            "projected_start": simulation_event.get("projected_start") if simulation_event else None,
            "projected_end": simulation_event.get("projected_end") if simulation_event else None,
        })
    rows.sort(key=lambda item: (-int(item["priority"]), str(item.get("next_run_at") or "9999"), item["schedule_id"]))
    policy = load_scheduler_policy()
    blackout = active_blackout(current, policy)
    history = list_scheduler_history(project_path=project_path, limit=30)
    observations = list_forecast_observations(project_path=project_path, limit=100)
    forecast_quality = build_forecast_quality_report(samples=samples, observations=observations)
    return {
        "generated_at": current.isoformat(timespec="seconds"),
        "active_blackout": blackout,
        "policy": policy,
        "queue_size": len(queue),
        "active_count": sum(1 for row in rows if row["status"] in {"pending", "queued", "running"}),
        "paused_count": sum(1 for row in rows if row["status"] == "paused"),
        "dead_letter_count": sum(1 for row in rows if row["status"] == "dead_letter"),
        "rows": rows,
        "recent_history": history,
        "simulation": simulation,
        "forecast_quality": forecast_quality,
    }
