from __future__ import annotations

import json
import re
import shutil
from datetime import datetime, time, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from .paths import state_dir
from .safe_io import atomic_write_json, exclusive_file_lock

POLICY_SCHEMA_VERSION = 1
MAX_POLICY_BYTES = 256 * 1024
DEFAULT_MIN_FREE_OUTPUT_BYTES = 512 * 1024 * 1024
DEFAULT_CONFLICT_RETRY_MINUTES = 5
MAX_BLACKOUT_WINDOWS = 32
_TIME_RE = re.compile(r"^(?:[01]\d|2[0-3]):[0-5]\d$")


def policy_path() -> Path:
    path = state_dir() / "scheduler"
    path.mkdir(parents=True, exist_ok=True)
    return path / "policy.json"


def policy_lock_path() -> Path:
    return policy_path().with_suffix(".lock")


def default_scheduler_policy() -> dict[str, Any]:
    return {
        "schema_version": POLICY_SCHEMA_VERSION,
        "max_parallel_renders": 1,
        "min_free_output_bytes": DEFAULT_MIN_FREE_OUTPUT_BYTES,
        "conflict_retry_minutes": DEFAULT_CONFLICT_RETRY_MINUTES,
        "blackout_windows": [],
    }


def _clock(value: str) -> time:
    selected = str(value).strip()
    if not _TIME_RE.fullmatch(selected):
        raise ValueError("Wartungsfenster-Zeit muss HH:MM entsprechen.")
    return time.fromisoformat(selected)


def normalize_blackout_window(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError("Wartungsfenster muss ein Objekt sein.")
    days_raw = raw.get("days", list(range(7)))
    if not isinstance(days_raw, list) or not days_raw:
        raise ValueError("Wartungsfenster benötigt mindestens einen Wochentag.")
    days = sorted({int(value) for value in days_raw})
    if any(value < 0 or value > 6 for value in days):
        raise ValueError("Wochentage müssen zwischen 0 (Montag) und 6 liegen.")
    start = _clock(str(raw.get("start", ""))).strftime("%H:%M")
    end = _clock(str(raw.get("end", ""))).strftime("%H:%M")
    timezone_name = str(raw.get("timezone") or "Europe/Berlin").strip()
    ZoneInfo(timezone_name)
    label = str(raw.get("label") or "Wartungsfenster").strip()[:80] or "Wartungsfenster"
    return {"days": days, "start": start, "end": end, "timezone": timezone_name, "label": label}


def normalize_scheduler_policy(raw: Any) -> dict[str, Any]:
    source = dict(raw or {}) if isinstance(raw, dict) else {}
    maximum = int(source.get("max_parallel_renders", 1))
    # The current renderer intentionally owns one process-wide lease. Raising
    # this before per-output resource partitioning exists would be unsafe.
    if maximum != 1:
        raise ValueError("VideoBatch unterstützt derzeit exakt einen parallelen Renderlauf.")
    minimum = int(source.get("min_free_output_bytes", DEFAULT_MIN_FREE_OUTPUT_BYTES))
    if minimum < 0 or minimum > 64 * 1024 * 1024 * 1024:
        raise ValueError("Freispeicher-Untergrenze liegt außerhalb des sicheren Bereichs.")
    retry = int(source.get("conflict_retry_minutes", DEFAULT_CONFLICT_RETRY_MINUTES))
    if retry < 1 or retry > 60:
        raise ValueError("Queue-Prüfintervall muss zwischen 1 und 60 Minuten liegen.")
    windows_raw = source.get("blackout_windows", [])
    if not isinstance(windows_raw, list) or len(windows_raw) > MAX_BLACKOUT_WINDOWS:
        raise ValueError("Zu viele Wartungsfenster.")
    windows = [normalize_blackout_window(item) for item in windows_raw]
    return {
        "schema_version": POLICY_SCHEMA_VERSION,
        "max_parallel_renders": maximum,
        "min_free_output_bytes": minimum,
        "conflict_retry_minutes": retry,
        "blackout_windows": windows,
    }


def load_scheduler_policy() -> dict[str, Any]:
    path = policy_path()
    if not path.exists():
        return default_scheduler_policy()
    if path.stat().st_size > MAX_POLICY_BYTES:
        raise ValueError("Scheduler-Policy überschreitet das sichere Größenlimit.")
    raw = json.loads(path.read_text(encoding="utf-8"))
    return normalize_scheduler_policy(raw)


def save_scheduler_policy(policy: dict[str, Any]) -> Path:
    canonical = normalize_scheduler_policy(policy)
    with exclusive_file_lock(policy_lock_path(), timeout_seconds=5.0):
        return atomic_write_json(policy_path(), canonical)


def _window_bounds(now: datetime, window: dict[str, Any]) -> tuple[datetime, datetime] | None:
    zone = ZoneInfo(str(window["timezone"]))
    local = now.astimezone(zone)
    start_clock = _clock(str(window["start"]))
    end_clock = _clock(str(window["end"]))
    start = datetime.combine(local.date(), start_clock, zone)
    end = datetime.combine(local.date(), end_clock, zone)
    if start_clock == end_clock:
        return start, start + timedelta(days=1)
    if end_clock < start_clock:
        if local.time() < end_clock:
            start -= timedelta(days=1)
        else:
            end += timedelta(days=1)
    if start.weekday() not in set(int(value) for value in window["days"]):
        return None
    return start, end


def active_blackout(now: datetime, policy: dict[str, Any] | None = None) -> dict[str, Any] | None:
    current = now if now.tzinfo else now.astimezone()
    canonical = normalize_scheduler_policy(policy or load_scheduler_policy())
    for window in canonical["blackout_windows"]:
        bounds = _window_bounds(current, window)
        if bounds is None:
            continue
        start, end = bounds
        local = current.astimezone(start.tzinfo)
        if start <= local < end:
            return {**window, "active_from": start.isoformat(), "active_until": end.isoformat()}
    return None


def _existing_parent(path: Path) -> Path:
    candidate = path.expanduser()
    while not candidate.exists() and candidate != candidate.parent:
        candidate = candidate.parent
    return candidate


def resource_readiness(output_dir: Path, policy: dict[str, Any] | None = None) -> tuple[bool, str, dict[str, Any]]:
    canonical = normalize_scheduler_policy(policy or load_scheduler_policy())
    parent = _existing_parent(output_dir)
    try:
        usage = shutil.disk_usage(parent)
    except OSError as exc:
        return False, f"Freier Speicher konnte nicht geprüft werden: {exc}", {"path": str(parent)}
    minimum = int(canonical["min_free_output_bytes"])
    detail = {"path": str(parent), "free_bytes": int(usage.free), "minimum_free_bytes": minimum}
    if usage.free < minimum:
        return False, "Ausgabeziel unterschreitet die konfigurierte Freispeicher-Untergrenze.", detail
    return True, "Ressourcenregel erfüllt.", detail
