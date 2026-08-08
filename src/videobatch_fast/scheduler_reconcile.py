from __future__ import annotations

import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable

from .scheduler import (
    build_systemd_units,
    list_schedules,
    register_systemd_schedule,
    remove_finished_units,
    systemd_user_dir,
    unit_names,
)
from .scheduler_governance import ACTIVE_STATUSES, cleanup_completed_schedules, queue_schedule_wait
from .scheduler_queue import prune_queue


def _probe(runner: Callable[[list[str]], subprocess.CompletedProcess[str]], args: list[str]) -> bool:
    try:
        return runner(args).returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def _unit_drift(record: dict[str, Any]) -> list[str]:
    if not record.get("next_run_at"):
        return []
    service_name, timer_name = unit_names(str(record["schedule_id"]))
    expected_service, expected_timer = build_systemd_units(record)
    directory = systemd_user_dir()
    drift: list[str] = []
    for name, expected in ((service_name, expected_service), (timer_name, expected_timer)):
        path = directory / name
        try:
            if not path.is_file() or path.is_symlink() or path.read_text(encoding="utf-8") != expected:
                drift.append(name)
        except OSError:
            drift.append(name)
    return drift


def reconcile_scheduler_state(
    *,
    project_path: Path | None = None,
    repair: bool = False,
    now: datetime | None = None,
    run_systemctl: Callable[[list[str]], subprocess.CompletedProcess[str]] | None = None,
) -> dict[str, Any]:
    from .scheduler import _systemctl
    current = now or datetime.now().astimezone()
    runner = run_systemctl or _systemctl
    all_schedules = list_schedules()
    schedules = all_schedules if project_path is None else list_schedules(project_path=project_path)
    rows: list[dict[str, Any]] = []
    active_ids = {str(item["schedule_id"]) for item in all_schedules if str(item.get("status")) in ACTIVE_STATUSES | {"paused"}}
    queue_pruned = prune_queue(active_schedule_ids=active_ids, now=current)
    repaired = 0
    for record in schedules:
        schedule_id = str(record["schedule_id"])
        status = str(record.get("status", "pending"))
        _service, timer = unit_names(schedule_id)
        drift = _unit_drift(record) if status in ACTIVE_STATUSES else []
        enabled = _probe(runner, ["is-enabled", "--quiet", timer]) if status in ACTIVE_STATUSES else False
        active = _probe(runner, ["is-active", "--quiet", timer]) if status in ACTIVE_STATUSES else False
        issues: list[str] = []
        action = "none"
        if status in {"pending", "queued"} and (drift or not enabled or not active):
            issues.append("Timer fehlt, ist deaktiviert oder weicht vom Plan ab.")
            if repair:
                register_systemd_schedule(record, run_systemctl=runner)
                repaired += 1
                action = "rearmed"
        elif status == "running" and not active:
            issues.append("Lauf war als aktiv markiert, aber systemd meldet keinen aktiven Timer.")
            if repair:
                eligible = current + timedelta(minutes=1)
                if queue_schedule_wait(
                    schedule_id, reason="reconcile", detail="Nach Neustart/Abbruch erneut in Scheduler-Queue eingeordnet.",
                    now=current, eligible_at=eligible, run_systemctl=runner,
                ):
                    repaired += 1
                    action = "queued"
                else:
                    from .scheduler import complete_schedule_occurrence
                    complete_schedule_occurrence(
                        schedule_id, "blocked",
                        "Abgebrochener Lauf lag außerhalb des sicheren Recovery-Zeitfensters; dieser Termin wird nicht erneut gestartet.",
                        finished_at=current, run_systemctl=runner,
                    )
                    repaired += 1
                    action = "advanced"
        elif status == "paused":
            directory = systemd_user_dir()
            service_name, timer_name = unit_names(schedule_id)
            if (directory / service_name).exists() or (directory / timer_name).exists() or _probe(runner, ["is-enabled", "--quiet", timer_name]):
                issues.append("Pausierter Plan besitzt noch aktive systemd-Artefakte.")
                if repair:
                    remove_finished_units(schedule_id)
                    repaired += 1
                    action = "disabled"
        elif status not in ACTIVE_STATUSES and status != "paused":
            directory = systemd_user_dir()
            service_name, timer_name = unit_names(schedule_id)
            if (directory / service_name).exists() or (directory / timer_name).exists():
                issues.append("Abgeschlossener Plan besitzt verwaiste systemd-Artefakte.")
                if repair:
                    remove_finished_units(schedule_id)
                    repaired += 1
                    action = "cleaned"
        rows.append({
            "schedule_id": schedule_id, "status": status, "enabled": enabled, "active": active,
            "unit_drift": drift, "issues": issues, "action": action,
        })
    cleanup = cleanup_completed_schedules(project_path=project_path, now=current) if repair else {"removed_count": 0}
    return {
        "checked_at": current.isoformat(timespec="seconds"),
        "schedules_checked": len(rows),
        "issues": sum(len(row["issues"]) for row in rows),
        "repaired": repaired,
        "queue_pruned": queue_pruned,
        "cleanup_removed": int(cleanup.get("removed_count", 0)),
        "rows": rows,
    }
