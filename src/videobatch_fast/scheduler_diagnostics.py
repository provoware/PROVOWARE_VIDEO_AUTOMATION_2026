from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from .scheduler_deadletter import dead_letter_summary
from .scheduler_policy import active_blackout, load_scheduler_policy, resource_readiness


def diagnose_schedule(
    record: dict[str, Any],
    *,
    now: datetime | None = None,
    queue_entry: dict[str, Any] | None = None,
    simulation_event: dict[str, Any] | None = None,
) -> dict[str, str]:
    current = now or datetime.now().astimezone()
    dead = dead_letter_summary(record)
    if dead:
        return {"code": f"dead_letter:{dead['code']}", "severity": "critical", "reason": dead["detail"], "next_action": dead["next_action"]}
    status = str(record.get("status", "pending"))
    if status == "paused":
        return {"code": "paused", "severity": "info", "reason": "Serie ist pausiert.", "next_action": "Serie fortsetzen, wenn wieder automatisch gerendert werden soll."}
    if status == "running":
        return {"code": "running", "severity": "info", "reason": "Der Renderlauf ist bereits aktiv.", "next_action": "Aktuellen Lauf abschließen lassen."}
    if queue_entry is not None:
        eligible = str(queue_entry.get("eligible_at", ""))
        queue_reason = str(queue_entry.get("reason", "wait"))
        labels = {
            "render_conflict": "Wartet auf freien Render-Slot",
            "blackout": "Wartet auf Ende des Wartungsfensters",
            "resource": "Wartet auf ausreichende Ressourcen",
            "reconcile": "Wartet nach Systemabgleich",
        }
        label = labels.get(queue_reason, "Wartet in der Scheduler-Queue")
        detail = str(queue_entry.get("detail") or "").strip()
        reason = f"{label}: {detail}" if detail else label
        return {"code": f"queue:{queue_reason}", "severity": "warning", "reason": reason, "next_action": f"Queue/Priorität prüfen; nächste Freigabe frühestens {eligible}."}
    policy = load_scheduler_policy()
    blackout = active_blackout(current, policy)
    if blackout:
        return {"code": "blackout", "severity": "warning", "reason": f"Wartungsfenster aktiv: {blackout['label']}", "next_action": f"Bis {blackout['active_until']} warten oder Betriebsregel bewusst ändern."}
    options = record.get("options") if isinstance(record.get("options"), dict) else {}
    ready, detail, metrics = resource_readiness(Path(str(options.get("output_dir", "."))), policy)
    if not ready:
        return {"code": "resource", "severity": "warning", "reason": detail, "next_action": f"Speicher freigeben; mindestens {metrics.get('minimum_free_bytes', 0)} Bytes Reserve einhalten."}
    try:
        from .scheduler import source_snapshot_is_current
        sources_ok, source_detail = source_snapshot_is_current(record)
    except (OSError, ValueError):
        sources_ok, source_detail = False, "Quellzustand konnte nicht sicher verifiziert werden."
    if not sources_ok:
        return {"code": "source_changed", "severity": "critical", "reason": source_detail, "next_action": "Zeitplan neu speichern oder duplizieren, damit Quellen und Renderzustand erneut eingefroren werden."}
    if simulation_event and simulation_event.get("status") == "missed":
        return {"code": "forecast_missed", "severity": "warning", "reason": str(simulation_event.get("reason")), "next_action": "Priorität, Wartungsfenster oder Catch-up-Fenster anpassen."}
    next_run = record.get("next_run_at")
    if next_run:
        return {"code": "scheduled", "severity": "ok", "reason": f"Wartet planmäßig auf {next_run}.", "next_action": "Keine Aktion erforderlich."}
    return {"code": status, "severity": "info", "reason": str(record.get("status_detail") or status), "next_action": "Zeitplanstatus prüfen."}
