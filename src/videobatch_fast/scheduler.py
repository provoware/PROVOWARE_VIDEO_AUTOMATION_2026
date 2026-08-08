from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import time
import uuid
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

from .models import BatchOptions
from .paths import config_dir, state_dir
from .safe_io import atomic_write_json, atomic_write_text, exclusive_file_lock, fsync_directory
from .scheduler_contract import normalize_governance
from .scheduler_history import append_scheduler_history
from .scheduler_queue import remove_queue_entry
from .scheduler_recurrence import (
    local_timezone_name,
    next_valid_occurrence,
    normalize_recurrence,
    recurrence_label,
)

SCHEDULER_SCHEMA_VERSION = 3
LEGACY_SCHEDULER_SCHEMA_VERSION = 1
PREVIOUS_SCHEDULER_SCHEMA_VERSION = 2
MAX_SCHEDULE_BYTES = 2 * 1024 * 1024
MAX_SCHEDULE_AHEAD_DAYS = 366
DEFAULT_MAX_LATENESS_MINUTES = 180
ALLOWED_AFTER_ACTIONS = {"none", "suspend"}
FINAL_STATUSES = {"success", "failed", "blocked", "missed", "cancelled", "conflict", "dead_letter"}
_ID_RE = re.compile(r"^[a-f0-9]{16}$")

def scheduler_root() -> Path:
    path = state_dir() / "scheduler"
    path.mkdir(parents=True, exist_ok=True)
    return path

def schedules_dir() -> Path:
    path = scheduler_root() / "schedules"
    path.mkdir(parents=True, exist_ok=True)
    return path

def schedule_path(schedule_id: str) -> Path:
    return schedules_dir() / f"{_validate_schedule_id(schedule_id)}.json"

def scheduler_lock_path() -> Path:
    return scheduler_root() / ".scheduler.lock"

def systemd_user_dir() -> Path:
    base = config_dir()
    # XDG_CONFIG_HOME/VideoBatchFast -> XDG_CONFIG_HOME/systemd/user
    path = base.parent / "systemd" / "user" if base.name == "VideoBatchFast" else base / "systemd" / "user"
    path.mkdir(parents=True, exist_ok=True)
    return path

def _validate_schedule_id(value: str) -> str:
    selected = str(value).strip().lower()
    if not _ID_RE.fullmatch(selected):
        raise ValueError("Ungültige Scheduler-ID.")
    return selected

def _utc_now() -> datetime:
    return datetime.now().astimezone()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _identity_payload(record: dict[str, Any]) -> dict[str, Any]:
    schema = int(record.get("schema_version", LEGACY_SCHEDULER_SCHEMA_VERSION))
    keys = [
        "schema_version", "schedule_id", "created_at", "scheduled_at", "max_lateness_minutes",
        "project_path", "project_sha256", "project_render_fingerprint", "options", "sources",
        "inhibit_sleep", "after_action", "launcher",
    ]
    if schema >= 2:
        keys.append("recurrence")
    if schema >= 3:
        keys.append("governance")
    return {key: record.get(key) for key in keys}


def schedule_fingerprint(record: dict[str, Any]) -> str:
    return hashlib.sha256(_canonical_bytes(_identity_payload(record))).hexdigest()


def _resolved_regular_file(raw: Path, *, label: str) -> Path:
    candidate = Path(raw).expanduser()
    if candidate.is_symlink():
        raise ValueError(f"{label} darf kein symbolischer Link sein.")
    resolved = candidate.resolve()
    if not resolved.is_file():
        raise ValueError(f"{label} ist keine reguläre Datei: {resolved}")
    return resolved


def project_render_fingerprint(project_path: Path) -> str:
    project = _resolved_regular_file(project_path, label="Projektdatei")
    if project.stat().st_size > 16 * 1024 * 1024:
        raise ValueError("Die Projektdatei überschreitet das sichere Größenlimit.")
    raw = json.loads(project.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("Projektdatei enthält kein JSON-Objekt.")

    def normalized_paths(key: str) -> list[str]:
        values = raw.get(key, [])
        if not isinstance(values, list):
            raise ValueError(f"Projektfeld {key} ist keine Liste.")
        normalized: list[str] = []
        for value in values:
            candidate = Path(str(value)).expanduser()
            if not candidate.is_absolute():
                candidate = project.parent / candidate
            normalized.append(str(candidate.resolve()))
        return normalized

    # BatchOptions are separately frozen in the schedule. The project binding
    # therefore covers the ordered render inputs only and intentionally ignores
    # volatile metadata such as updated_at/KPI history.
    payload = {
        "audio_paths": normalized_paths("audio_paths"),
        "media_paths": normalized_paths("media_paths"),
    }
    return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


def _source_snapshot(paths: list[Path]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    seen: set[Path] = set()
    for raw in paths:
        path = _resolved_regular_file(Path(raw), label="Quelle")
        if path in seen:
            continue
        seen.add(path)
        stat = path.stat()
        result.append({"path": str(path), "size": stat.st_size, "mtime_ns": stat.st_mtime_ns})
    return result


def batch_options_payload(options: BatchOptions) -> dict[str, Any]:
    payload = asdict(options)
    payload["output_dir"] = str(Path(options.output_dir).expanduser().resolve())
    return payload


def batch_options_from_payload(payload: dict[str, Any]) -> BatchOptions:
    if not isinstance(payload, dict):
        raise ValueError("Scheduler-Optionen fehlen.")
    allowed = set(BatchOptions.__dataclass_fields__)
    values = {key: payload[key] for key in allowed if key in payload}
    values["output_dir"] = Path(str(values.get("output_dir", ""))).expanduser()
    return BatchOptions(**values)


def find_project_launcher(start: Path | None = None) -> Path:
    current = (start or Path(__file__)).resolve()
    for parent in (current, *current.parents):
        candidate = parent / "videobatch.sh"
        if candidate.is_file() and not candidate.is_symlink():
            return candidate
    raise FileNotFoundError("VideoBatch-Starter videobatch.sh wurde nicht gefunden.")


def create_schedule_record(
    *,
    project_path: Path,
    source_paths: list[Path],
    options: BatchOptions,
    scheduled_at: datetime,
    inhibit_sleep: bool = True,
    after_action: str = "none",
    max_lateness_minutes: int = DEFAULT_MAX_LATENESS_MINUTES,
    recurrence: dict[str, Any] | None = None,
    timezone_name: str | None = None,
    priority: int = 50,
    launcher: Path | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    current = (now or _utc_now()).astimezone()
    when = scheduled_at.astimezone() if scheduled_at.tzinfo else scheduled_at.replace(tzinfo=current.tzinfo)
    if when <= current + timedelta(seconds=10):
        raise ValueError("Die Startzeit muss mindestens 10 Sekunden in der Zukunft liegen.")
    if when > current + timedelta(days=MAX_SCHEDULE_AHEAD_DAYS):
        raise ValueError("Die Startzeit darf höchstens 366 Tage in der Zukunft liegen.")
    project = _resolved_regular_file(project_path, label="Projektdatei")
    if project.stat().st_size > 16 * 1024 * 1024:
        raise ValueError("Die Projektdatei überschreitet das sichere Größenlimit.")
    selected_after = str(after_action).strip().lower()
    if selected_after not in ALLOWED_AFTER_ACTIONS:
        raise ValueError("Unzulässige Energieaktion nach dem Renderlauf.")
    lateness = int(max_lateness_minutes)
    if lateness < 5 or lateness > 24 * 60:
        raise ValueError("Die zulässige Verspätung muss zwischen 5 Minuten und 24 Stunden liegen.")
    chosen_launcher = _resolved_regular_file(Path(launcher or find_project_launcher()), label="VideoBatch-Starter")
    if not os.access(chosen_launcher, os.X_OK):
        raise ValueError("Der VideoBatch-Starter ist nicht ausführbar.")
    recurrence_payload = normalize_recurrence(
        recurrence,
        scheduled_at=when,
        timezone_name=timezone_name or local_timezone_name(),
    )
    schedule_id = uuid.uuid4().hex[:16]
    record: dict[str, Any] = {
        "schema_version": SCHEDULER_SCHEMA_VERSION,
        "schedule_id": schedule_id,
        "created_at": current.isoformat(timespec="seconds"),
        "scheduled_at": when.isoformat(timespec="seconds"),
        "next_run_at": when.isoformat(timespec="seconds"),
        "occurrence_planned_at": when.isoformat(timespec="seconds"),
        "occurrence_index": 1,
        "occurrences_completed": 0,
        "recurrence": recurrence_payload,
        "governance": normalize_governance({"priority": priority}),
        "max_lateness_minutes": lateness,
        "project_path": str(project),
        "project_sha256": _sha256(project),
        "project_render_fingerprint": project_render_fingerprint(project),
        "options": batch_options_payload(options),
        "sources": _source_snapshot(source_paths),
        "inhibit_sleep": bool(inhibit_sleep),
        "after_action": selected_after,
        "launcher": str(chosen_launcher),
        "status": "pending",
        "status_detail": "Wartet auf den geplanten Startzeitpunkt.",
        "attempts": 0,
        "result": {},
    }
    record["schedule_fingerprint"] = schedule_fingerprint(record)
    return record


def _upgrade_legacy_schedule(record: dict[str, Any]) -> dict[str, Any]:
    upgraded = dict(record)
    schema = int(upgraded.get("schema_version", LEGACY_SCHEDULER_SCHEMA_VERSION))
    scheduled = datetime.fromisoformat(str(upgraded.get("scheduled_at", "")))
    if schema == LEGACY_SCHEDULER_SCHEMA_VERSION:
        upgraded["next_run_at"] = str(upgraded["scheduled_at"])
        upgraded["occurrence_planned_at"] = str(upgraded["scheduled_at"])
        upgraded["occurrence_index"] = 1
        upgraded["occurrences_completed"] = 0
        upgraded["recurrence"] = normalize_recurrence(
            {"kind": "once", "max_occurrences": 1, "catch_up_policy": "run_once"},
            scheduled_at=scheduled, timezone_name=local_timezone_name(),
        )
    upgraded["schema_version"] = SCHEDULER_SCHEMA_VERSION
    upgraded["governance"] = normalize_governance(upgraded.get("governance"))
    upgraded["schedule_fingerprint"] = schedule_fingerprint(upgraded)
    return upgraded


def validate_schedule_record(record: Any) -> dict[str, Any]:
    if not isinstance(record, dict):
        raise ValueError("Scheduler-Datei enthält kein JSON-Objekt.")
    schema = int(record.get("schema_version", -1))
    if schema not in {LEGACY_SCHEDULER_SCHEMA_VERSION, PREVIOUS_SCHEDULER_SCHEMA_VERSION, SCHEDULER_SCHEMA_VERSION}:
        raise ValueError("Nicht unterstützte Scheduler-Schemaversion.")
    _validate_schedule_id(str(record.get("schedule_id", "")))
    render_fingerprint = str(record.get("project_render_fingerprint", ""))
    if len(render_fingerprint) != 64:
        raise ValueError("Scheduler enthält keinen gültigen Render-Fingerprint.")
    expected = str(record.get("schedule_fingerprint", ""))
    if len(expected) != 64 or expected != schedule_fingerprint(record):
        raise ValueError("Scheduler-Fingerprint stimmt nicht; Planung wurde verändert.")
    scheduled = datetime.fromisoformat(str(record.get("scheduled_at", "")))
    if str(record.get("after_action", "")) not in ALLOWED_AFTER_ACTIONS:
        raise ValueError("Scheduler enthält eine unzulässige Energieaktion.")
    batch_options_from_payload(record.get("options", {}))
    sources = record.get("sources")
    if not isinstance(sources, list) or not sources:
        raise ValueError("Scheduler enthält keine Quellen.")
    for item in sources:
        if not isinstance(item, dict) or not str(item.get("path", "")):
            raise ValueError("Scheduler enthält einen ungültigen Quelleneintrag.")
        if int(item.get("size", -1)) < 0 or int(item.get("mtime_ns", -1)) < 0:
            raise ValueError("Scheduler enthält ungültige Quellmetadaten.")
    if schema < SCHEDULER_SCHEMA_VERSION:
        return _upgrade_legacy_schedule(record)
    governance = record.get("governance")
    if normalize_governance(governance) != governance:
        raise ValueError("Scheduler enthält keine kanonische Governance-Regel.")
    recurrence = record.get("recurrence")
    if not isinstance(recurrence, dict):
        raise ValueError("Scheduler enthält keine gültige Wiederholungsregel.")
    normalized = normalize_recurrence(recurrence, scheduled_at=scheduled)
    if normalized != recurrence:
        raise ValueError("Scheduler enthält keine kanonische Wiederholungsregel.")
    occurrence_index = int(record.get("occurrence_index", 1))
    if occurrence_index < 1 or occurrence_index > int(recurrence["max_occurrences"]):
        raise ValueError("Scheduler enthält einen ungültigen Laufindex.")
    for field in ("next_run_at", "occurrence_planned_at"):
        value = record.get(field)
        if value is not None:
            datetime.fromisoformat(str(value))
    return record


def load_schedule(schedule_id: str) -> dict[str, Any]:
    path = schedule_path(schedule_id)
    if path.stat().st_size > MAX_SCHEDULE_BYTES:
        raise ValueError("Scheduler-Datei überschreitet das sichere Größenlimit.")
    return validate_schedule_record(json.loads(path.read_text(encoding="utf-8")))


def save_schedule(record: dict[str, Any]) -> Path:
    canonical = validate_schedule_record(record)
    with exclusive_file_lock(scheduler_lock_path(), timeout_seconds=5.0):
        return atomic_write_json(schedule_path(str(canonical["schedule_id"])), canonical)


def update_schedule_status(schedule_id: str, status: str, detail: str, **result: Any) -> dict[str, Any]:
    with exclusive_file_lock(scheduler_lock_path(), timeout_seconds=5.0):
        record = load_schedule(schedule_id)
        record["status"] = str(status)
        record["status_detail"] = str(detail)[:1000]
        record["updated_at"] = _utc_now().isoformat(timespec="seconds")
        if result:
            current_result = record.get("result", {}) if isinstance(record.get("result"), dict) else {}
            current_result.update(result)
            record["result"] = current_result
        atomic_write_json(schedule_path(schedule_id), record)
        return record


def _systemd_quote(value: str) -> str:
    selected = str(value).replace("\\", "\\\\").replace('"', '\\"').replace("%", "%%")
    if "\n" in selected or "\r" in selected:
        raise ValueError("Systemd-Argument enthält einen Zeilenumbruch.")
    return f'"{selected}"'


def unit_names(schedule_id: str) -> tuple[str, str]:
    selected = _validate_schedule_id(schedule_id)
    return f"videobatch-schedule-{selected}.service", f"videobatch-schedule-{selected}.timer"


def build_systemd_units(record: dict[str, Any], *, inhibit_binary: str = "/usr/bin/systemd-inhibit") -> tuple[str, str]:
    record = validate_schedule_record(record)
    if not record.get("next_run_at"):
        raise ValueError("Abgeschlossener Zeitplan besitzt keinen nächsten Termin.")
    service_name, _timer_name = unit_names(str(record["schedule_id"]))
    launcher = str(record["launcher"])
    args = [launcher, "scheduler-run", "--schedule-id", str(record["schedule_id"])]
    if bool(record.get("inhibit_sleep")):
        args = [
            inhibit_binary,
            "--what=sleep:shutdown",
            "--who=VideoBatchFast",
            "--why=Geplanter VideoBatch-Renderlauf",
            "--mode=block",
            *args,
        ]
    exec_start = " ".join(_systemd_quote(item) for item in args)
    service = "\n".join(
        [
            "[Unit]",
            "Description=VideoBatch Fast geplanter Renderlauf",
            "After=default.target",
            "",
            "[Service]",
            "Type=oneshot",
            f"ExecStart={exec_start}",
            "Nice=10",
            "IOSchedulingClass=best-effort",
            "IOSchedulingPriority=6",
            "NoNewPrivileges=yes",
            "",
        ]
    )
    when = datetime.fromisoformat(str(record.get("next_run_at") or record["scheduled_at"]))
    calendar = when.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    timer = "\n".join(
        [
            "[Unit]",
            "Description=VideoBatch Fast Startzeituhr",
            "",
            "[Timer]",
            f"OnCalendar={calendar}",
            "AccuracySec=1s",
            "Persistent=true",
            f"Unit={service_name}",
            "",
            "[Install]",
            "WantedBy=timers.target",
            "",
        ]
    )
    return service, timer


def _systemctl(arguments: list[str], *, timeout: float = 15.0) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["systemctl", "--user", *arguments],
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout,
        errors="replace",
        env={**os.environ, "SYSTEMD_PAGER": "cat", "PAGER": "cat"},
    )


def register_systemd_schedule(
    record: dict[str, Any],
    *,
    run_systemctl: Callable[[list[str]], subprocess.CompletedProcess[str]] | None = None,
) -> dict[str, Any]:
    record = validate_schedule_record(record)
    if not record.get("next_run_at"):
        raise RuntimeError("Abgeschlossener Zeitplan kann nicht erneut aktiviert werden.")
    if shutil.which("systemctl") is None or shutil.which("systemd-inhibit") is None:
        raise RuntimeError("systemctl oder systemd-inhibit fehlt.")
    service_name, timer_name = unit_names(str(record["schedule_id"]))
    service_text, timer_text = build_systemd_units(record, inhibit_binary=shutil.which("systemd-inhibit") or "/usr/bin/systemd-inhibit")
    directory = systemd_user_dir()
    service_path = directory / service_name
    timer_path = directory / timer_name
    runner = run_systemctl or _systemctl
    with exclusive_file_lock(scheduler_lock_path(), timeout_seconds=5.0):
        atomic_write_text(service_path, service_text, mode=0o644)
        atomic_write_text(timer_path, timer_text, mode=0o644)
        reload_result = runner(["daemon-reload"])
        if reload_result.returncode != 0:
            service_path.unlink(missing_ok=True)
            timer_path.unlink(missing_ok=True)
            fsync_directory(directory)
            raise RuntimeError(f"systemd --user konnte nicht neu geladen werden: {reload_result.stderr.strip()}")
        enable_result = runner(["enable", "--now", timer_name])
        if enable_result.returncode != 0:
            runner(["disable", "--now", timer_name])
            service_path.unlink(missing_ok=True)
            timer_path.unlink(missing_ok=True)
            fsync_directory(directory)
            runner(["daemon-reload"])
            raise RuntimeError(f"Startzeituhr konnte nicht aktiviert werden: {enable_result.stderr.strip()}")
        record["systemd"] = {"service": service_name, "timer": timer_name}
        if str(record.get("status")) != "queued":
            record["status"] = "pending"
            record["status_detail"] = "Startzeituhr ist im systemd-Benutzermanager aktiviert."
        atomic_write_json(schedule_path(str(record["schedule_id"])), record)
    return record


def cancel_schedule(
    schedule_id: str,
    *,
    run_systemctl: Callable[[list[str]], subprocess.CompletedProcess[str]] | None = None,
) -> dict[str, Any]:
    selected = _validate_schedule_id(schedule_id)
    service_name, timer_name = unit_names(selected)
    runner = run_systemctl or _systemctl
    with exclusive_file_lock(scheduler_lock_path(), timeout_seconds=5.0):
        record = load_schedule(selected)
        append_scheduler_history(
            record,
            outcome="cancelled",
            detail="Zeitplan wurde vom Nutzer aufgehoben.",
            occurrence_index=int(record.get("occurrence_index", 1)),
            planned_at=str(record.get("occurrence_planned_at") or record.get("next_run_at") or record["scheduled_at"]),
        )
        runner(["disable", "--now", timer_name])
        directory = systemd_user_dir()
        (directory / timer_name).unlink(missing_ok=True)
        (directory / service_name).unlink(missing_ok=True)
        fsync_directory(directory)
        runner(["daemon-reload"])
        remove_queue_entry(selected)
        record["status"] = "cancelled"
        record["next_run_at"] = None
        record["status_detail"] = "Planung wurde vom Nutzer aufgehoben."
        record["updated_at"] = _utc_now().isoformat(timespec="seconds")
        atomic_write_json(schedule_path(selected), record)
    return record


def list_schedules(*, project_path: Path | None = None) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    selected_project = Path(project_path).expanduser().resolve() if project_path is not None else None
    for path in sorted(schedules_dir().glob("*.json")):
        try:
            record = load_schedule(path.stem)
        except (OSError, ValueError, json.JSONDecodeError):
            continue
        if selected_project is not None and Path(str(record.get("project_path", ""))).expanduser().resolve() != selected_project:
            continue
        result.append(record)
    result.sort(key=lambda item: str(item.get("next_run_at") or item.get("scheduled_at", "")))
    return result


def next_active_schedule(project_path: Path | None = None) -> dict[str, Any] | None:
    for record in list_schedules(project_path=project_path):
        if str(record.get("status")) in {"pending", "queued", "running"}:
            return record
    return None


def schedule_display_time(record: dict[str, Any]) -> str:
    value = record.get("next_run_at") or record.get("scheduled_at")
    if not value:
        return "–"
    when = datetime.fromisoformat(str(value))
    recurrence = record.get("recurrence") if isinstance(record.get("recurrence"), dict) else {}
    timezone_name = str(recurrence.get("timezone") or local_timezone_name())
    try:
        from zoneinfo import ZoneInfo
        when = when.astimezone(ZoneInfo(timezone_name))
    except Exception:
        when = when.astimezone()
    return when.strftime("%Y-%m-%d %H:%M")


def schedule_recurrence_label(record: dict[str, Any]) -> str:
    recurrence = record.get("recurrence") if isinstance(record.get("recurrence"), dict) else {"kind": "once"}
    return recurrence_label(recurrence)


def terminate_schedule(
    schedule_id: str,
    outcome: str,
    detail: str,
    *,
    result: dict[str, Any] | None = None,
    finished_at: datetime | None = None,
) -> dict[str, Any]:
    selected = _validate_schedule_id(schedule_id)
    finished = (finished_at or _utc_now()).isoformat(timespec="seconds")
    with exclusive_file_lock(scheduler_lock_path(), timeout_seconds=5.0):
        record = load_schedule(selected)
        planned = str(record.get("occurrence_planned_at") or record.get("next_run_at") or record["scheduled_at"])
        append_scheduler_history(
            record, outcome=outcome, detail=detail, occurrence_index=int(record.get("occurrence_index", 1)),
            planned_at=planned, finished_at=finished, result=result,
        )
        record["status"] = str(outcome)
        record["status_detail"] = str(detail)[:1000]
        record["updated_at"] = finished
        record["next_run_at"] = None
        record["occurrences_completed"] = int(record.get("occurrence_index", 1))
        if result:
            record["result"] = {**(record.get("result") or {}), **result}
        atomic_write_json(schedule_path(selected), record)
    remove_queue_entry(selected)
    remove_finished_units(selected)
    return record


def complete_schedule_occurrence(
    schedule_id: str,
    outcome: str,
    detail: str,
    *,
    result: dict[str, Any] | None = None,
    finished_at: datetime | None = None,
    run_systemctl: Callable[[list[str]], subprocess.CompletedProcess[str]] | None = None,
) -> dict[str, Any]:
    selected = _validate_schedule_id(schedule_id)
    finished_dt = finished_at or _utc_now()
    finished = finished_dt.isoformat(timespec="seconds")
    rearm = False
    with exclusive_file_lock(scheduler_lock_path(), timeout_seconds=5.0):
        record = load_schedule(selected)
        index = int(record.get("occurrence_index", 1))
        planned = str(record.get("occurrence_planned_at") or record.get("next_run_at") or record["scheduled_at"])
        append_scheduler_history(
            record, outcome=outcome, detail=detail, occurrence_index=index, planned_at=planned, finished_at=finished, result=result,
        )
        cancelled = str(record.get("status")) == "cancelled"
        pause_after = bool(record.pop("pause_after_current", False))
        next_item = None if cancelled else next_valid_occurrence(record, after_index=index)
        if cancelled:
            record["status"] = "cancelled"
            record["status_detail"] = "Serie wurde während des aktiven Laufs beendet; kein Folgetermin wird aktiviert."
            record["next_run_at"] = None
            record["occurrences_completed"] = index
        elif next_item is None:
            record["status"] = str(outcome)
            record["status_detail"] = str(detail)[:1000]
            record["next_run_at"] = None
            record["occurrences_completed"] = index
        else:
            next_index, next_when, skipped = next_item
            for skipped_index in skipped:
                append_scheduler_history(
                    record, outcome="dst_skipped",
                    detail="Lokale Uhrzeit existiert wegen der Sommerzeitumstellung nicht; Termin sicher übersprungen.",
                    occurrence_index=skipped_index, planned_at=f"DST-skip:{skipped_index}", finished_at=finished,
                )
            record["occurrence_index"] = next_index
            record["occurrences_completed"] = next_index - 1
            record["next_run_at"] = next_when.isoformat(timespec="seconds")
            record["occurrence_planned_at"] = next_when.isoformat(timespec="seconds")
            if pause_after:
                record["status"] = "paused"
                record["status_detail"] = "Aktueller Lauf abgeschlossen; Serie bleibt für Folgetermine pausiert."
            else:
                record["status"] = "pending"
                record["status_detail"] = f"Nächster Lauf: {next_when.isoformat(timespec='minutes')}"
                rearm = True
        record["updated_at"] = finished
        current_result = record.get("result", {}) if isinstance(record.get("result"), dict) else {}
        current_result.update({"last_outcome": outcome, "last_finished_at": finished, **(result or {})})
        record["result"] = current_result
        atomic_write_json(schedule_path(selected), record)
    remove_queue_entry(selected)
    if rearm:
        register_systemd_schedule(record, run_systemctl=run_systemctl)
    else:
        remove_finished_units(selected)
    return record


def defer_schedule_for_conflict(
    schedule_id: str,
    *,
    now: datetime | None = None,
    retry_minutes: int = 10,
    run_systemctl: Callable[[list[str]], subprocess.CompletedProcess[str]] | None = None,
) -> bool:
    selected = _validate_schedule_id(schedule_id)
    current = (now or _utc_now()).astimezone()
    with exclusive_file_lock(scheduler_lock_path(), timeout_seconds=5.0):
        record = load_schedule(selected)
        planned = datetime.fromisoformat(str(record.get("occurrence_planned_at") or record["scheduled_at"]))
        deadline = planned + timedelta(minutes=int(record.get("max_lateness_minutes", DEFAULT_MAX_LATENESS_MINUTES)))
        retry_at = current + timedelta(minutes=max(1, min(int(retry_minutes), 60)))
        if retry_at > deadline:
            return False
        record["next_run_at"] = retry_at.isoformat(timespec="seconds")
        record["status"] = "pending"
        record["status_detail"] = f"Anderer Renderlauf aktiv; neuer Versuch um {retry_at.isoformat(timespec='minutes')}."
        current_result = record.get("result", {}) if isinstance(record.get("result"), dict) else {}
        current_result["conflict_retries"] = int(current_result.get("conflict_retries", 0)) + 1
        record["result"] = current_result
        record["updated_at"] = current.isoformat(timespec="seconds")
        atomic_write_json(schedule_path(selected), record)
    register_systemd_schedule(record, run_systemctl=run_systemctl)
    return True


def source_snapshot_is_current(record: dict[str, Any]) -> tuple[bool, str]:
    project = Path(str(record["project_path"])).expanduser()
    try:
        current_render_fingerprint = project_render_fingerprint(project)
    except (OSError, ValueError, json.JSONDecodeError):
        return False, "Projektdatei ist nicht mehr sicher lesbar."
    if current_render_fingerprint != str(record["project_render_fingerprint"]):
        return False, "Renderrelevante Projektquellen wurden nach der Planung verändert."
    for item in record["sources"]:
        path = Path(str(item["path"])).expanduser()
        try:
            stat = path.stat()
        except OSError:
            return False, f"Quelle fehlt: {path}"
        if not path.is_file() or path.is_symlink():
            return False, f"Quelle ist nicht mehr regulär: {path}"
        if stat.st_size != int(item["size"]) or stat.st_mtime_ns != int(item["mtime_ns"]):
            return False, f"Quelle wurde seit der Planung verändert: {path.name}"
    return True, "Projekt und Quellen entsprechen dem geplanten Zustand."


def remove_finished_units(schedule_id: str) -> None:
    selected = _validate_schedule_id(schedule_id)
    service_name, timer_name = unit_names(selected)
    directory = systemd_user_dir()
    try:
        _systemctl(["disable", timer_name])
    except (OSError, subprocess.SubprocessError):
        pass
    changed = False
    for name in (timer_name, service_name):
        target = directory / name
        try:
            if target.exists():
                target.unlink()
                changed = True
        except OSError:
            pass
    if changed:
        try:
            fsync_directory(directory)
            _systemctl(["daemon-reload"])
        except (OSError, subprocess.SubprocessError):
            pass
