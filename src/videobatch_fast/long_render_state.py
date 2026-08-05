from __future__ import annotations

import json
import os
import time
import uuid
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .long_render_schema import (
    SCHEMA_VERSION,
    JobSpec,
    LoadedContract,
    LongRenderContractError,
    canonical_hash,
    utc_now,
)
from .safe_io import atomic_write_json, fsync_directory, read_json


def reservation_path(output: Path) -> Path:
    return output.with_name(f".{output.name}.longrender.lock")


def _write_exclusive(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        fsync_directory(path.parent)
    except Exception:
        path.unlink(missing_ok=True)
        raise


def ensure_reservation(output: Path, *, run_id: str, job_id: str, contract_digest: str) -> Path:
    path = reservation_path(output)
    payload = {"run_id": run_id, "job_id": job_id, "contract_digest": contract_digest}
    if path.exists():
        existing = read_json(path)
        if existing != payload:
            raise LongRenderContractError(f"Ausgabe ist durch einen anderen Lauf reserviert: {output}")
        return path
    _write_exclusive(path, payload)
    return path


def release_reservations(contract: LoadedContract) -> None:
    for job in contract.jobs:
        reservation_path(contract.target_dir / job.output_name).unlink(missing_ok=True)
    fsync_directory(contract.target_dir)


def _job_record(spec: JobSpec) -> dict[str, Any]:
    return {
        "id": spec.job_id,
        "state": "pending",
        "attempts": 0,
        "output": spec.output_name,
        "output_sha256": "",
        "output_size": 0,
        "last_error": "",
        "updated_at": utc_now(),
    }


def state_directory(contract: LoadedContract) -> Path:
    return contract.state_file.parent


def new_state(contract: LoadedContract, target: dict[str, Any], manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "run_id": uuid.uuid4().hex,
        "candidate": contract.candidate,
        "contract_digest": contract.digest,
        "state": "prepared",
        "created_at": utc_now(),
        "updated_at": utc_now(),
        "started_at": "",
        "finished_at": "",
        "resume_count": 0,
        "elapsed_seconds": 0.0,
        "target": target,
        "rehearsal_only": bool(target.get("rehearsal_target") or target.get("resource_mode") != "hard-systemd"),
        "limits": asdict(contract.limits),
        "input_manifest": manifest,
        "jobs": [_job_record(item) for item in contract.jobs],
        "events": [],
        "current_job": "",
        "last_progress": {},
        "terminal_event": "",
        "output_manifest": {},
    }


def load_state(contract: LoadedContract) -> dict[str, Any]:
    raw = read_json(contract.state_file)
    if not isinstance(raw, dict) or int(raw.get("schema_version", 0)) != SCHEMA_VERSION:
        raise LongRenderContractError("Gespeicherter Langzeitrender-Zustand ist ungültig.")
    if raw.get("contract_digest") != contract.digest:
        raise LongRenderContractError("Der Vertrag wurde seit dem ersten Lauf verändert; Wiederaufnahme blockiert.")
    return dict(raw)


def write_state(contract: LoadedContract, state: dict[str, Any]) -> None:
    state["updated_at"] = utc_now()
    atomic_write_json(contract.state_file, state)


def append_event(contract: LoadedContract, state: dict[str, Any], name: str, **payload: Any) -> None:
    event = {"time": utc_now(), "name": name, **payload}
    events = state.setdefault("events", [])
    if isinstance(events, list):
        events.append(event)
        if len(events) > 500:
            del events[:-500]
    log_path = state_directory(contract) / "events.jsonl"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    fsync_directory(log_path.parent)


def write_heartbeat(contract: LoadedContract, state: dict[str, Any]) -> None:
    evidence = state_directory(contract) / "heartbeats"
    evidence.mkdir(parents=True, exist_ok=True)
    index = len(list(evidence.glob("heartbeat-*.json"))) + 1
    payload = {
        "schema_version": 1,
        "sequence": index,
        "captured_at": utc_now(),
        "run_id": state.get("run_id"),
        "state": state.get("state"),
        "current_job": state.get("current_job"),
        "elapsed_seconds": state.get("elapsed_seconds"),
        "last_progress": state.get("last_progress", {}),
        "completed_jobs": sum(
            1 for item in state.get("jobs", []) if isinstance(item, dict) and item.get("state") == "completed"
        ),
    }
    payload["digest"] = canonical_hash(payload)
    atomic_write_json(evidence / f"heartbeat-{index:05d}.json", payload)


def job_by_id(state: dict[str, Any], job_id: str) -> dict[str, Any]:
    for item in state.get("jobs", []):
        if isinstance(item, dict) and item.get("id") == job_id:
            return item
    raise LongRenderContractError(f"Auftrag fehlt im Zustand: {job_id}")


def archive_partial(contract: LoadedContract, output: Path) -> Path:
    partials = state_directory(contract) / "partials"
    partials.mkdir(parents=True, exist_ok=True)
    destination = partials / f"{output.name}.{int(time.time())}.partial"
    os.replace(output, destination)
    fsync_directory(output.parent)
    fsync_directory(partials)
    return destination
