from __future__ import annotations

import json
import math
import statistics
from datetime import datetime
from pathlib import Path
from typing import Any

from .paths import state_dir
from .scheduler_calibration import calibration_profile, calibrated_confidence, recency_weight, weighted_percentile
from .scheduler_environment import safe_capture_render_environment

MAX_JOURNAL_BYTES = 4 * 1024 * 1024
MAX_HISTORY_SAMPLES = 250
_SIGNATURE_KEYS = ("codec", "profile", "resolution", "fps", "assignment_mode", "quick_mode")
_COMPATIBLE_KEYS = ("codec", "profile", "resolution", "assignment_mode")


def _signature(options: dict[str, Any], keys: tuple[str, ...] = _SIGNATURE_KEYS) -> tuple[str, ...]:
    return tuple(str(options.get(key, "")) for key in keys)


def _percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(value for value in values if math.isfinite(value) and value >= 0.0)
    if not ordered:
        raise ValueError("Keine gültigen Prognosewerte vorhanden.")
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * max(0.0, min(float(fraction), 1.0))
    lower = int(math.floor(position))
    upper = int(math.ceil(position))
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def _history_dir() -> Path:
    return state_dir() / "jobs" / "history"


def _read_history_file(path: Path) -> dict[str, Any] | None:
    try:
        if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_JOURNAL_BYTES:
            return None
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return None
    if not isinstance(raw, dict) or int(raw.get("schema_version", -1)) != 2:
        return None
    return raw


def _output_size(job: dict[str, Any]) -> int | None:
    raw = str(job.get("output", "")).strip()
    if not raw:
        return None
    path = Path(raw).expanduser()
    try:
        if path.is_symlink() or not path.is_file():
            return None
        return int(path.stat().st_size)
    except OSError:
        return None


def load_render_samples(*, limit: int = MAX_HISTORY_SAMPLES) -> list[dict[str, Any]]:
    directory = _history_dir()
    if not directory.is_dir():
        return []
    result: list[dict[str, Any]] = []
    maximum = max(1, min(int(limit), MAX_HISTORY_SAMPLES))
    for path in sorted(directory.glob("*.json"), key=lambda item: item.name, reverse=True):
        payload = _read_history_file(path)
        if payload is None or str(payload.get("state")) != "completed":
            continue
        jobs = payload.get("jobs")
        options = payload.get("options")
        if not isinstance(jobs, list) or not isinstance(options, dict):
            continue
        elapsed: list[float] = []
        output_sizes: list[int] = []
        for raw_job in jobs:
            if not isinstance(raw_job, dict) or str(raw_job.get("state")) != "completed":
                continue
            try:
                seconds = float(raw_job.get("elapsed_seconds", 0.0))
            except (TypeError, ValueError):
                continue
            if not math.isfinite(seconds) or seconds <= 0.0:
                continue
            elapsed.append(seconds)
            size = _output_size(raw_job)
            if size is not None and size >= 0:
                output_sizes.append(size)
        if not elapsed:
            continue
        result.append({
            "operation_id": str(payload.get("operation_id", "")),
            "signature": _signature(options),
            "compatible_signature": _signature(options, _COMPATIBLE_KEYS),
            "segment": {key: str(options.get(key, "")) for key in ("codec", "profile", "resolution")},
            "job_count": len(elapsed),
            "runtime_seconds": float(sum(elapsed)),
            "seconds_per_job": float(statistics.median(elapsed)),
            "output_bytes_per_job": float(statistics.median(output_sizes)) if output_sizes else None,
            "updated_at": str(payload.get("updated_at", "")),
            "environment": dict(payload.get("render_environment") or {}) if isinstance(payload.get("render_environment"), dict) else {},
        })
        if len(result) >= maximum:
            break
    return result


def _project_job_count(record: dict[str, Any]) -> int:
    try:
        path = Path(str(record.get("project_path", ""))).expanduser()
        if path.is_symlink() or not path.is_file() or path.stat().st_size > 16 * 1024 * 1024:
            raise ValueError
        payload = json.loads(path.read_text(encoding="utf-8"))
        audios = payload.get("audio_paths", []) if isinstance(payload, dict) else []
        if isinstance(audios, list) and audios:
            return len(audios)
    except (OSError, ValueError, json.JSONDecodeError):
        pass
    sources = record.get("sources") if isinstance(record.get("sources"), list) else []
    return max(1, len(sources) // 2) if sources else 1


def _remaining_occurrences(record: dict[str, Any]) -> int:
    recurrence = record.get("recurrence") if isinstance(record.get("recurrence"), dict) else {}
    maximum = max(1, int(recurrence.get("max_occurrences", 1) or 1))
    completed = max(0, int(record.get("occurrences_completed", 0) or 0))
    return max(0, maximum - completed)


def _environment_pool(history: list[dict[str, Any]], current: dict[str, Any]) -> tuple[list[dict[str, Any]], str, str | None]:
    environment_id = str(current.get("fingerprint_sha256", ""))
    epoch_id = str(current.get("epoch_id", ""))
    aware = [item for item in history if isinstance(item.get("environment"), dict) and item["environment"].get("fingerprint_sha256")]
    if not aware:
        return history, "legacy", None
    same_environment = [item for item in aware if item["environment"].get("fingerprint_sha256") == environment_id]
    if same_environment:
        same_epoch = [item for item in same_environment if epoch_id and item["environment"].get("epoch_id") == epoch_id]
        if same_epoch:
            return same_epoch, "exact_epoch", None
        return same_environment, "previous_epoch", "low"
    legacy = [item for item in history if not (isinstance(item.get("environment"), dict) and item["environment"].get("fingerprint_sha256"))]
    if legacy:
        return legacy, "legacy_fallback", "low"
    return [], "environment_mismatch", "low"


def _cap_confidence(value: str, cap: str | None) -> str:
    if cap is None:
        return value
    ranks = {"none": 0, "low": 1, "medium": 2, "high": 3}
    return min((value, cap), key=lambda item: ranks.get(item, 0))


def estimate_schedule(
    record: dict[str, Any], *, samples: list[dict[str, Any]] | None = None, now: datetime | None = None
) -> dict[str, Any]:
    options = record.get("options") if isinstance(record.get("options"), dict) else {}
    history = list(samples if samples is not None else load_render_samples())
    environment = safe_capture_render_environment(options)
    history, environment_match, environment_confidence_cap = _environment_pool(history, environment)
    exact_signature = _signature(options)
    compatible_signature = _signature(options, _COMPATIBLE_KEYS)
    exact = [item for item in history if tuple(item.get("signature", ())) == exact_signature]
    compatible = [item for item in history if tuple(item.get("compatible_signature", ())) == compatible_signature]
    if exact:
        selected, match = exact, "exact"
    elif compatible:
        selected, match = compatible, "compatible"
    else:
        selected, match = history, "global"
    job_count = _project_job_count(record)
    remaining = _remaining_occurrences(record)
    if not selected:
        return {
            "available": False,
            "confidence": "none",
            "base_confidence": "none",
            "match": "none",
            "sample_count": 0,
            "job_count": job_count,
            "remaining_occurrences": remaining,
            "runtime_seconds_p50": None,
            "runtime_seconds_p75": None,
            "runtime_seconds_p90": None,
            "output_bytes_p75": None,
            "series_output_bytes_p75": None,
            "calibration": calibration_profile([]),
            "sample_age_weighting": True,
            "environment": environment,
            "environment_match": environment_match,
            "environment_confidence_cap": environment_confidence_cap,
        }
    sample_count = len(selected)
    if match == "exact" and sample_count >= 8:
        base_confidence = "high"
    elif (match == "exact" and sample_count >= 3) or (match == "compatible" and sample_count >= 6):
        base_confidence = "medium"
    else:
        base_confidence = "low"
    reference = now or datetime.now().astimezone()
    weights = [recency_weight(item, reference=reference) for item in selected]
    seconds_per_job = [float(item["seconds_per_job"]) for item in selected]
    outputs = [
        (float(item["output_bytes_per_job"]), weights[index])
        for index, item in enumerate(selected) if item.get("output_bytes_per_job") is not None
    ]
    p50 = weighted_percentile(seconds_per_job, weights, 0.50) * job_count
    p75 = weighted_percentile(seconds_per_job, weights, 0.75) * job_count
    p90 = weighted_percentile(seconds_per_job, weights, 0.90) * job_count
    output_p75 = None
    if outputs:
        output_p75 = weighted_percentile(
            [item[0] for item in outputs], [item[1] for item in outputs], 0.75
        ) * job_count
    calibration = calibration_profile(selected)
    confidence = _cap_confidence(calibrated_confidence(base_confidence, calibration), environment_confidence_cap)
    return {
        "available": True,
        "confidence": confidence,
        "base_confidence": base_confidence,
        "match": match,
        "sample_count": sample_count,
        "job_count": job_count,
        "remaining_occurrences": remaining,
        "runtime_seconds_p50": round(p50, 1),
        "runtime_seconds_p75": round(p75, 1),
        "runtime_seconds_p90": round(p90, 1),
        "output_bytes_p75": int(output_p75) if output_p75 is not None else None,
        "series_output_bytes_p75": int(output_p75 * remaining) if output_p75 is not None else None,
        "calibration": calibration,
        "sample_age_weighting": True,
        "environment": environment,
        "environment_match": environment_match,
        "environment_confidence_cap": environment_confidence_cap,
    }
