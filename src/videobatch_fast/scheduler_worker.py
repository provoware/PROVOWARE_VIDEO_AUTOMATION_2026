from __future__ import annotations

import argparse
import json
import subprocess
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from .app_events import AppEvent
from .audio_waveform import analyze_audio
from .jobs import build_jobs
from .models import BatchOptions
from .project_state import normalize_project_state
from .runner import BatchRunner
from .render_coordination import RenderBusyError
from .scheduler import (
    batch_options_from_payload,
    complete_schedule_occurrence,
    load_schedule,
    remove_finished_units,  # compatibility hook for historical tests/extensions
    source_snapshot_is_current,
    terminate_schedule,
    update_schedule_status,
)
from .scheduler_recurrence import should_run_occurrence
from .scheduler_calibration import append_forecast_observation
from .scheduler_deadletter import mark_dead_letter
from .scheduler_forecast import estimate_schedule
from .scheduler_governance import (
    queue_schedule_wait, queue_turn, rearm_queued_schedule, scheduler_preflight_wait,
)
from .scheduler_policy import load_scheduler_policy
from .scheduler_queue import remove_queue_entry
from .validation import validate_pairs


def _project_payload(path: Path) -> dict[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("Projektdatei enthält kein JSON-Objekt.")
    return normalize_project_state(raw)


def _after_success(action: str) -> tuple[bool, str]:
    if action == "none":
        return True, "Keine Energieaktion angefordert."
    if action == "suspend":
        result = subprocess.run(
            ["systemctl", "suspend"],
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
            errors="replace",
        )
        if result.returncode == 0:
            return True, "Energiesparen wurde nach erfolgreichem Lauf angefordert."
        return False, f"Energiesparen konnte nicht ausgelöst werden: {result.stderr.strip()}"
    return False, "Unbekannte Energieaktion."


def _resolve_queue_gate(schedule_id: str, record: dict[str, Any], current: datetime) -> tuple[int | None, dict[str, Any]]:
    if str(record.get("status")) != "queued":
        return None, record
    allowed, queue_detail, wait_until = queue_turn(schedule_id, now=current)
    if allowed:
        remove_queue_entry(schedule_id)
        return None, load_schedule(schedule_id)
    if wait_until is None:
        complete_schedule_occurrence(schedule_id, "conflict", queue_detail, finished_at=current)
        return 19, record
    try:
        rearm_queued_schedule(schedule_id, when=wait_until, detail=queue_detail, now=current)
    except ValueError:
        complete_schedule_occurrence(schedule_id, "conflict", queue_detail, finished_at=current)
    return 19, record


def _resolve_start_gate(schedule_id: str, current: datetime) -> tuple[int | None, dict[str, Any]]:
    record = load_schedule(schedule_id)
    if str(record.get("status")) not in {"pending", "queued", "running"}:
        return 0, record
    queue_code, record = _resolve_queue_gate(schedule_id, record, current)
    if queue_code is not None:
        return queue_code, record
    should_run, timing_detail = should_run_occurrence(record, now=current)
    if not should_run:
        complete_schedule_occurrence(schedule_id, "missed", timing_detail, finished_at=current)
        return 12, record
    wait_reason, wait_detail, wait_until, _metrics = scheduler_preflight_wait(record, now=current)
    if wait_reason is not None and wait_until is not None:
        queued = queue_schedule_wait(schedule_id, reason=wait_reason, detail=wait_detail, now=current, eligible_at=wait_until)
        if not queued:
            outcome = "missed" if wait_reason == "blackout" else "blocked"
            complete_schedule_occurrence(schedule_id, outcome, wait_detail, finished_at=current)
        return 20, record
    current_ok, detail = source_snapshot_is_current(record)
    if not current_ok:
        mark_dead_letter(
            schedule_id, code="source_changed", detail=detail,
            next_action="Zeitplan neu speichern oder duplizieren, damit Quellen und Renderzustand erneut eingefroren werden.",
            now=current,
        )
        return 13, record
    return None, record


def _handle_render_busy(schedule_id: str, current: datetime) -> int:
    retry_minutes = int(load_scheduler_policy()["conflict_retry_minutes"])
    queued = queue_schedule_wait(
        schedule_id, reason="render_conflict",
        detail="Ein anderer Renderlauf ist aktiv; Termin wartet priorisiert in der Scheduler-Queue.",
        now=current, eligible_at=current + timedelta(minutes=retry_minutes),
    )
    if not queued:
        complete_schedule_occurrence(
            schedule_id, "conflict",
            "Ein anderer Renderlauf blieb bis zum Ende des zulässigen Zeitfensters aktiv.",
            finished_at=current,
        )
    return 19



def _output_bytes(jobs) -> int | None:
    total = 0
    seen = False
    for job in jobs:
        path = Path(job.output)
        try:
            if path.is_symlink() or not path.is_file():
                continue
            total += int(path.stat().st_size)
            seen = True
        except OSError:
            continue
    return total if seen else None


def _record_forecast_accuracy(
    record: dict[str, Any], forecast: dict[str, Any], final_payload: dict[str, object], jobs, *, outcome: str, operation_id: str
) -> None:
    try:
        elapsed = float(final_payload.get("elapsed", 0.0) or 0.0)
    except (TypeError, ValueError):
        return
    if elapsed <= 0.0:
        return
    try:
        append_forecast_observation(
            record, forecast=forecast, actual_runtime_seconds=elapsed, actual_output_bytes=_output_bytes(jobs),
            outcome=outcome, operation_id=operation_id, finished_at=datetime.now().astimezone(),
        )
    except (OSError, ValueError, RuntimeError):
        # Kalibrierung ist Evidence, aber darf einen erfolgreich gerenderten Batch niemals umklassifizieren.
        return

def execute_schedule(schedule_id: str, *, now: datetime | None = None) -> int:
    current = (now or datetime.now().astimezone()).astimezone()
    gate_code, record = _resolve_start_gate(schedule_id, current)
    if gate_code is not None:
        return gate_code
    forecast_snapshot = estimate_schedule(record, now=current)
    update_schedule_status(
        schedule_id, "running", "Geplanter Renderlauf wurde gestartet.",
        started_at=current.isoformat(timespec="seconds"),
    )
    final_payload: dict[str, object] = {}

    def callback(event: AppEvent) -> None:
        nonlocal final_payload
        if event.name == "batch_finished":
            final_payload = dict(event.payload)

    try:
        try:
            project = _project_payload(Path(str(record["project_path"])).expanduser())
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            mark_dead_letter(
                schedule_id, code="project_invalid",
                detail=f"Projektzustand ist dauerhaft nicht ausführbar: {type(exc).__name__}: {exc}",
                next_action="Projektdatei reparieren und den Zeitplan anschließend neu speichern oder duplizieren.",
                now=current,
            )
            return 21
        options: BatchOptions = batch_options_from_payload(record["options"])
        audios = [Path(value).expanduser() for value in project.get("audio_paths", [])]
        media = [Path(value).expanduser() for value in project.get("media_paths", [])]
        analyses = {path: analyze_audio(path) for path in audios} if options.slideshow_scene_sync else {}
        jobs = build_jobs(audios, media, options, scene_analyses=analyses)
        blockers = [issue for issue in validate_pairs(jobs, options) if issue.blocking]
        if blockers:
            summary = " · ".join(f"{item.title}: {item.message}" for item in blockers[:5])
            terminate_schedule(schedule_id, "blocked", f"Vorbereitung unvollständig: {summary}")
            return 14
        if not jobs:
            terminate_schedule(schedule_id, "blocked", "Der geplante Zustand erzeugt keine Renderaufträge.")
            return 15
        runner = BatchRunner(callback)
        try:
            runner.start(jobs, options)
        except RenderBusyError:
            return _handle_render_busy(schedule_id, current)
        while not runner.wait(timeout=0.5):
            time.sleep(0.05)
        successes = int(final_payload.get("successes", 0) or 0)
        failures = int(final_payload.get("failures", 0) or 0)
        unprocessed = int(final_payload.get("unprocessed", 0) or 0)
        total = int(final_payload.get("total", len(jobs)) or len(jobs))
        terminal = str(final_payload.get("terminal_event", "batch_failed_internal"))
        result = {"successes": successes, "failures": failures, "unprocessed": unprocessed, "terminal_event": terminal}
        if successes == total and failures == 0 and unprocessed == 0 and terminal == "batch_finished":
            _record_forecast_accuracy(
                record, forecast_snapshot, final_payload, jobs, outcome="success", operation_id=str(getattr(runner, "operation_id", ""))
            )
            energy_ok, energy_detail = _after_success(str(record.get("after_action", "none")))
            complete_schedule_occurrence(
                schedule_id, "success", f"{successes}/{total} Aufträge erfolgreich. {energy_detail}",
                finished_at=datetime.now().astimezone(), result={**result, "energy_action_ok": energy_ok},
            )
            return 0
        _record_forecast_accuracy(
            record, forecast_snapshot, final_payload, jobs, outcome="failed", operation_id=str(getattr(runner, "operation_id", ""))
        )
        complete_schedule_occurrence(
            schedule_id, "failed",
            f"Geplanter Lauf beendet: {successes} erfolgreich, {failures} fehlerhaft, {unprocessed} nicht gestartet.",
            finished_at=datetime.now().astimezone(), result=result,
        )
        return 17
    except Exception as exc:
        complete_schedule_occurrence(
            schedule_id, "failed", f"Scheduler-Lauf fehlgeschlagen: {type(exc).__name__}: {exc}",
            finished_at=datetime.now().astimezone(),
        )
        return 18


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="Führt genau einen eingefrorenen VideoBatch-Schedulerplan aus.")
    result.add_argument("--schedule-id", required=True)
    return result


def main() -> int:
    args = parser().parse_args()
    return execute_schedule(args.schedule_id)


if __name__ == "__main__":
    raise SystemExit(main())
