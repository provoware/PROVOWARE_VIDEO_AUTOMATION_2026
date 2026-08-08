from __future__ import annotations

import json
import math
import statistics
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from .paths import state_dir
from .safe_io import atomic_write_json, exclusive_file_lock, fsync_directory
from .scheduler_environment import compare_environment_profiles, list_environment_epochs, maybe_rebaseline_environment

CALIBRATION_SCHEMA_VERSION = 1
MAX_OBSERVATIONS = 500
MAX_OBSERVATION_BYTES = 256 * 1024
BACKTEST_WINDOWS = (30, 90, 180)
_SEGMENT_KEYS = ("codec", "profile", "resolution")


def _aware(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def sample_datetime(sample: dict[str, Any]) -> datetime:
    return _aware(str(sample.get("updated_at", ""))) or datetime(1970, 1, 1, tzinfo=timezone.utc)


def recency_weight(sample: dict[str, Any], *, reference: datetime) -> float:
    observed = sample_datetime(sample)
    anchor = reference if reference.tzinfo is not None else reference.replace(tzinfo=timezone.utc)
    age_days = max(0.0, (anchor.astimezone(timezone.utc) - observed.astimezone(timezone.utc)).total_seconds() / 86400.0)
    if age_days <= 30.0:
        return 1.0
    if age_days <= 90.0:
        return 0.75
    if age_days <= 180.0:
        return 0.50
    return 0.25


def weighted_percentile(values: Iterable[float], weights: Iterable[float], fraction: float) -> float:
    pairs = [
        (float(value), max(0.0, float(weight)))
        for value, weight in zip(values, weights)
        if math.isfinite(float(value)) and float(value) >= 0.0 and math.isfinite(float(weight)) and float(weight) > 0.0
    ]
    if not pairs:
        raise ValueError("Keine gültigen gewichteten Prognosewerte vorhanden.")
    distinct_weights = {round(weight, 12) for _value, weight in pairs}
    ordered_values = sorted(value for value, _weight in pairs)
    if len(distinct_weights) == 1:
        if len(ordered_values) == 1:
            return ordered_values[0]
        position = (len(ordered_values) - 1) * max(0.0, min(float(fraction), 1.0))
        lower = int(math.floor(position))
        upper = int(math.ceil(position))
        if lower == upper:
            return ordered_values[lower]
        weight = position - lower
        return ordered_values[lower] * (1.0 - weight) + ordered_values[upper] * weight
    ordered = sorted(pairs, key=lambda item: item[0])
    total = sum(weight for _value, weight in ordered)
    target = max(0.0, min(float(fraction), 1.0)) * total
    cumulative = 0.0
    for value, weight in ordered:
        cumulative += weight
        if cumulative >= target:
            return value
    return ordered[-1][0]


def _environment_prior(target: dict[str, Any], prior: list[dict[str, Any]]) -> list[dict[str, Any]]:
    environment = target.get("environment") if isinstance(target.get("environment"), dict) else {}
    environment_id = str(environment.get("fingerprint_sha256", ""))
    epoch_id = str(environment.get("epoch_id", ""))
    if not environment_id:
        return prior
    same_environment = [
        item for item in prior
        if isinstance(item.get("environment"), dict) and item["environment"].get("fingerprint_sha256") == environment_id
    ]
    if same_environment:
        same_epoch = [item for item in same_environment if epoch_id and item["environment"].get("epoch_id") == epoch_id]
        return same_epoch or same_environment
    legacy = [item for item in prior if not (isinstance(item.get("environment"), dict) and item["environment"].get("fingerprint_sha256"))]
    return legacy


def _select_prior(target: dict[str, Any], prior: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], str]:
    pool = _environment_prior(target, prior)
    exact_signature = tuple(target.get("signature", ()))
    compatible_signature = tuple(target.get("compatible_signature", ()))
    exact = [item for item in pool if tuple(item.get("signature", ())) == exact_signature]
    if exact:
        return exact, "exact"
    compatible = [item for item in pool if tuple(item.get("compatible_signature", ())) == compatible_signature]
    if compatible:
        return compatible, "compatible"
    return list(pool), "global"


def _forecast_target(target: dict[str, Any], prior: list[dict[str, Any]]) -> dict[str, Any] | None:
    selected, match = _select_prior(target, prior)
    if not selected:
        return None
    reference = sample_datetime(target)
    weights = [recency_weight(item, reference=reference) for item in selected]
    seconds = [float(item.get("seconds_per_job", 0.0)) for item in selected]
    job_count = max(1, int(target.get("job_count", 1) or 1))
    runtime = weighted_percentile(seconds, weights, 0.50) * job_count
    output_pairs = [
        (float(item["output_bytes_per_job"]), weights[index])
        for index, item in enumerate(selected)
        if item.get("output_bytes_per_job") is not None
    ]
    output = None
    if output_pairs:
        output = weighted_percentile(
            [item[0] for item in output_pairs], [item[1] for item in output_pairs], 0.75
        ) * job_count
    return {"runtime_seconds": runtime, "output_bytes": output, "match": match, "sample_count": len(selected)}


def rolling_backtest(samples: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ordered = sorted(samples, key=lambda item: (sample_datetime(item), str(item.get("operation_id", ""))))
    outcomes: list[dict[str, Any]] = []
    for index, target in enumerate(ordered):
        if index < 3:
            continue
        predicted = _forecast_target(target, ordered[:index])
        actual = float(target.get("runtime_seconds", 0.0) or 0.0)
        if predicted is None or actual <= 0.0:
            continue
        runtime_prediction = float(predicted["runtime_seconds"])
        error = runtime_prediction - actual
        abs_pct = abs(error) / actual
        actual_output = target.get("output_bytes_per_job")
        output_prediction = predicted.get("output_bytes")
        output_actual_total = None
        output_abs_pct = None
        if actual_output is not None:
            output_actual_total = float(actual_output) * max(1, int(target.get("job_count", 1) or 1))
            if output_prediction is not None and output_actual_total > 0:
                output_abs_pct = abs(float(output_prediction) - output_actual_total) / output_actual_total
        outcomes.append({
            "operation_id": str(target.get("operation_id", "")),
            "updated_at": str(target.get("updated_at", "")),
            "segment": dict(target.get("segment") or {}),
            "environment": dict(target.get("environment") or {}) if isinstance(target.get("environment"), dict) else {},
            "match": predicted["match"],
            "training_samples": predicted["sample_count"],
            "predicted_runtime_seconds": runtime_prediction,
            "actual_runtime_seconds": actual,
            "error_seconds": error,
            "abs_pct_error": abs_pct,
            "predicted_output_bytes": output_prediction,
            "actual_output_bytes": output_actual_total,
            "output_abs_pct_error": output_abs_pct,
        })
    return outcomes


def _percentile(values: list[float], fraction: float) -> float | None:
    clean = sorted(float(value) for value in values if math.isfinite(float(value)))
    if not clean:
        return None
    if len(clean) == 1:
        return clean[0]
    position = (len(clean) - 1) * max(0.0, min(float(fraction), 1.0))
    low = int(math.floor(position))
    high = int(math.ceil(position))
    if low == high:
        return clean[low]
    ratio = position - low
    return clean[low] * (1.0 - ratio) + clean[high] * ratio


def accuracy_metrics(outcomes: list[dict[str, Any]]) -> dict[str, Any]:
    if not outcomes:
        return {
            "count": 0, "mae_seconds": None, "rmse_seconds": None, "median_abs_pct_error": None,
            "p90_abs_pct_error": None, "bias_pct": None, "output_median_abs_pct_error": None,
        }
    errors = [float(item["error_seconds"]) for item in outcomes]
    absolute = [abs(value) for value in errors]
    percentages = [float(item["abs_pct_error"]) for item in outcomes]
    signed_pct = [
        float(item["error_seconds"]) / float(item["actual_runtime_seconds"])
        for item in outcomes if float(item.get("actual_runtime_seconds", 0.0) or 0.0) > 0.0
    ]
    output_pct = [
        float(item["output_abs_pct_error"]) for item in outcomes if item.get("output_abs_pct_error") is not None
    ]
    return {
        "count": len(outcomes),
        "mae_seconds": round(statistics.fmean(absolute), 2),
        "rmse_seconds": round(math.sqrt(statistics.fmean([value * value for value in errors])), 2),
        "median_abs_pct_error": round(float(statistics.median(percentages)), 4),
        "p90_abs_pct_error": round(float(_percentile(percentages, 0.90) or 0.0), 4),
        "bias_pct": round(float(statistics.median(signed_pct)), 4) if signed_pct else None,
        "output_median_abs_pct_error": round(float(statistics.median(output_pct)), 4) if output_pct else None,
    }


def _error_drift(outcomes: list[dict[str, Any]]) -> dict[str, Any]:
    if len(outcomes) < 10:
        return {"status": "insufficient", "recent_error": None, "baseline_error": None, "ratio": None}
    recent = outcomes[-5:]
    baseline = outcomes[-15:-5] if len(outcomes) >= 15 else outcomes[:-5]
    if len(baseline) < 5:
        return {"status": "insufficient", "recent_error": None, "baseline_error": None, "ratio": None}
    recent_error = float(statistics.median(float(item["abs_pct_error"]) for item in recent))
    baseline_error = float(statistics.median(float(item["abs_pct_error"]) for item in baseline))
    ratio = recent_error / max(baseline_error, 0.01)
    if recent_error >= 0.30 and ratio >= 1.50:
        status = "drift"
    elif recent_error >= 0.20 and ratio >= 1.25:
        status = "watch"
    else:
        status = "stable"
    return {
        "status": status,
        "recent_error": round(recent_error, 4),
        "baseline_error": round(baseline_error, 4),
        "ratio": round(ratio, 3),
    }


def calibration_profile(samples: list[dict[str, Any]]) -> dict[str, Any]:
    outcomes = rolling_backtest(samples)
    metrics = accuracy_metrics(outcomes)
    return {**metrics, "drift": _error_drift(outcomes)}


def calibrated_confidence(base: str, profile: dict[str, Any]) -> str:
    ranks = {"none": 0, "low": 1, "medium": 2, "high": 3}
    if ranks.get(base, 0) <= 1 or int(profile.get("count", 0) or 0) < 4:
        return base
    median_error = profile.get("median_abs_pct_error")
    p90_error = profile.get("p90_abs_pct_error")
    drift = str((profile.get("drift") or {}).get("status", "insufficient"))
    cap = "high"
    if median_error is None or p90_error is None:
        cap = "medium"
    elif float(median_error) > 0.30 or float(p90_error) > 0.60 or drift == "drift":
        cap = "low"
    elif float(median_error) > 0.15 or float(p90_error) > 0.35 or drift == "watch":
        cap = "medium"
    return min((base, cap), key=lambda value: ranks.get(value, 0))


def _segment_key(outcome: dict[str, Any]) -> tuple[str, ...]:
    segment = outcome.get("segment") if isinstance(outcome.get("segment"), dict) else {}
    return tuple(str(segment.get(key, "")) for key in _SEGMENT_KEYS)


def _segment_reports(outcomes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, ...], list[dict[str, Any]]] = {}
    for outcome in outcomes:
        groups.setdefault(_segment_key(outcome), []).append(outcome)
    result: list[dict[str, Any]] = []
    for key, items in groups.items():
        metrics = accuracy_metrics(items)
        result.append({
            "codec": key[0] or "–", "profile": key[1] or "–", "resolution": key[2] or "–",
            **metrics,
        })
    result.sort(key=lambda item: (-int(item["count"]), item["codec"], item["profile"], item["resolution"]))
    return result[:30]


def _runtime_level_drift(samples: list[dict[str, Any]]) -> dict[str, Any]:
    ordered = sorted(samples, key=sample_datetime)
    if len(ordered) < 10:
        return {"status": "insufficient", "recent_seconds_per_job": None, "baseline_seconds_per_job": None, "shift_pct": None}
    recent = [float(item["seconds_per_job"]) for item in ordered[-5:]]
    baseline_items = ordered[-15:-5] if len(ordered) >= 15 else ordered[:-5]
    baseline = [float(item["seconds_per_job"]) for item in baseline_items]
    if len(baseline) < 5:
        return {"status": "insufficient", "recent_seconds_per_job": None, "baseline_seconds_per_job": None, "shift_pct": None}
    recent_median = float(statistics.median(recent))
    baseline_median = float(statistics.median(baseline))
    shift = abs(recent_median - baseline_median) / max(baseline_median, 0.001)
    status = "drift" if shift >= 0.35 else ("watch" if shift >= 0.20 else "stable")
    return {
        "status": status,
        "recent_seconds_per_job": round(recent_median, 2),
        "baseline_seconds_per_job": round(baseline_median, 2),
        "shift_pct": round(shift, 4),
    }


def calibration_dir() -> Path:
    path = state_dir() / "scheduler" / "forecast_calibration"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _calibration_lock() -> Path:
    return state_dir() / "scheduler" / ".forecast-calibration.lock"


def append_forecast_observation(
    record: dict[str, Any],
    *,
    forecast: dict[str, Any],
    actual_runtime_seconds: float,
    actual_output_bytes: int | None,
    outcome: str,
    operation_id: str = "",
    finished_at: datetime | None = None,
) -> Path | None:
    actual_runtime = float(actual_runtime_seconds)
    if not math.isfinite(actual_runtime) or actual_runtime <= 0.0:
        return None
    options = record.get("options") if isinstance(record.get("options"), dict) else {}
    predicted_runtime = forecast.get("runtime_seconds_p50")
    predicted_output = forecast.get("output_bytes_p75")
    runtime_error = None
    if predicted_runtime is not None:
        runtime_error = (float(predicted_runtime) - actual_runtime) / actual_runtime
    output_error = None
    if predicted_output is not None and actual_output_bytes is not None and int(actual_output_bytes) > 0:
        output_error = (float(predicted_output) - float(actual_output_bytes)) / float(actual_output_bytes)
    finished = finished_at or datetime.now().astimezone()
    observation = {
        "schema_version": CALIBRATION_SCHEMA_VERSION,
        "observation_id": uuid.uuid4().hex[:16],
        "schedule_id": str(record.get("schedule_id", "")),
        "operation_id": str(operation_id),
        "project_path": str(record.get("project_path", "")),
        "finished_at": finished.isoformat(timespec="seconds"),
        "outcome": str(outcome),
        "segment": {key: str(options.get(key, "")) for key in _SEGMENT_KEYS},
        "environment": dict(forecast.get("environment") or {}) if isinstance(forecast.get("environment"), dict) else {},
        "prediction": {
            "runtime_seconds_p50": predicted_runtime,
            "runtime_seconds_p75": forecast.get("runtime_seconds_p75"),
            "runtime_seconds_p90": forecast.get("runtime_seconds_p90"),
            "output_bytes_p75": predicted_output,
            "confidence": str(forecast.get("confidence", "none")),
            "match": str(forecast.get("match", "none")),
            "sample_count": int(forecast.get("sample_count", 0) or 0),
            "job_count": int(forecast.get("job_count", 1) or 1),
            "environment_match": str(forecast.get("environment_match", "legacy")),
        },
        "actual": {
            "runtime_seconds": round(actual_runtime, 3),
            "seconds_per_job": round(actual_runtime / max(1, int(forecast.get("job_count", 1) or 1)), 3),
            "output_bytes": int(actual_output_bytes) if actual_output_bytes is not None else None,
        },
        "error": {
            "runtime_signed_pct": round(runtime_error, 6) if runtime_error is not None else None,
            "runtime_abs_pct": round(abs(runtime_error), 6) if runtime_error is not None else None,
            "output_signed_pct": round(output_error, 6) if output_error is not None else None,
            "output_abs_pct": round(abs(output_error), 6) if output_error is not None else None,
        },
    }
    filename = f"{finished.strftime('%Y%m%dT%H%M%S')}_{observation['observation_id']}.json"
    with exclusive_file_lock(_calibration_lock(), timeout_seconds=5.0):
        path = atomic_write_json(calibration_dir() / filename, observation)
        files = sorted(calibration_dir().glob("*.json"), key=lambda item: item.name, reverse=True)
        changed = False
        for stale in files[MAX_OBSERVATIONS:]:
            stale.unlink(missing_ok=True)
            changed = True
        if changed:
            fsync_directory(calibration_dir())
    environment = observation.get("environment") if isinstance(observation.get("environment"), dict) else {}
    if environment.get("fingerprint_sha256") and environment.get("epoch_id"):
        try:
            maybe_rebaseline_environment(environment, list_forecast_observations(limit=MAX_OBSERVATIONS))
        except (OSError, ValueError, RuntimeError):
            pass
    return path


def _read_observation(path: Path) -> dict[str, Any] | None:
    try:
        if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_OBSERVATION_BYTES:
            return None
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict) or int(payload.get("schema_version", -1)) != CALIBRATION_SCHEMA_VERSION:
        return None
    return payload


def list_forecast_observations(*, project_path: Path | None = None, limit: int = 100) -> list[dict[str, Any]]:
    selected = project_path.expanduser().resolve() if project_path is not None else None
    maximum = max(1, min(int(limit), MAX_OBSERVATIONS))
    result: list[dict[str, Any]] = []
    directory = calibration_dir()
    for path in sorted(directory.glob("*.json"), key=lambda item: item.name, reverse=True):
        payload = _read_observation(path)
        if payload is None:
            continue
        if selected is not None:
            try:
                if Path(str(payload.get("project_path", ""))).expanduser().resolve() != selected:
                    continue
            except OSError:
                continue
        result.append(payload)
        if len(result) >= maximum:
            break
    return result


def _observation_metrics(observations: list[dict[str, Any]]) -> dict[str, Any]:
    runtime = [
        float((item.get("error") or {}).get("runtime_abs_pct"))
        for item in observations
        if isinstance(item.get("error"), dict) and (item.get("error") or {}).get("runtime_abs_pct") is not None
    ]
    output = [
        float((item.get("error") or {}).get("output_abs_pct"))
        for item in observations
        if isinstance(item.get("error"), dict) and (item.get("error") or {}).get("output_abs_pct") is not None
    ]
    return {
        "count": len(observations),
        "runtime_median_abs_pct_error": round(float(statistics.median(runtime)), 4) if runtime else None,
        "runtime_p90_abs_pct_error": round(float(_percentile(runtime, 0.90) or 0.0), 4) if runtime else None,
        "output_median_abs_pct_error": round(float(statistics.median(output)), 4) if output else None,
    }


def _environment_quality(samples: list[dict[str, Any]]) -> dict[str, Any]:
    ordered = sorted(samples, key=sample_datetime)
    aware = [item for item in ordered if isinstance(item.get("environment"), dict) and item["environment"].get("fingerprint_sha256")]
    if not aware:
        return {"status": "legacy", "environment_count": 0, "current": {}, "previous": {}, "comparison": {}, "epochs": [], "cause": "legacy_samples"}
    current = dict(aware[-1]["environment"])
    current_id = current.get("fingerprint_sha256")
    previous = {}
    current_run_count = 0
    for item in reversed(aware):
        environment = item.get("environment") if isinstance(item.get("environment"), dict) else {}
        if environment.get("fingerprint_sha256") == current_id and not previous:
            current_run_count += 1
            continue
        if environment.get("fingerprint_sha256") != current_id:
            previous = dict(environment)
            break
    ids = {str(item["environment"].get("fingerprint_sha256")) for item in aware}
    comparison = compare_environment_profiles(current, previous or None)
    epochs = list_environment_epochs(str(current_id)) if current_id else []
    changed_recently = bool(previous) and current_run_count < 5
    return {
        "status": "changed" if changed_recently else "stable",
        "environment_count": len(ids),
        "current_run_count": current_run_count,
        "current": current,
        "previous": previous,
        "comparison": comparison,
        "epochs": epochs[-10:],
        "cause": "environment_change" if changed_recently else "same_environment",
    }


def _drift_cause(environment: dict[str, Any], runtime_drift: dict[str, Any], error_drift: dict[str, Any]) -> str:
    if environment.get("status") == "changed":
        return "environment_change"
    if runtime_drift.get("status") == "drift":
        return "performance_drift_same_environment"
    if error_drift.get("status") == "drift":
        return "forecast_model_drift"
    if runtime_drift.get("status") == "watch" or error_drift.get("status") == "watch":
        return "watch"
    return "stable"


def build_forecast_quality_report(
    *, samples: list[dict[str, Any]], observations: list[dict[str, Any]] | None = None
) -> dict[str, Any]:
    outcomes = rolling_backtest(samples)
    windows: dict[str, Any] = {}
    for size in BACKTEST_WINDOWS:
        selected = outcomes[-size:]
        windows[str(size)] = accuracy_metrics(selected)
    direct = list(observations if observations is not None else list_forecast_observations(limit=100))
    error_drift = _error_drift(outcomes)
    runtime_drift = _runtime_level_drift(samples)
    environment = _environment_quality(samples)
    return {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "sample_count": len(samples),
        "backtest_count": len(outcomes),
        "windows": windows,
        "segments": _segment_reports(outcomes),
        "error_drift": error_drift,
        "runtime_drift": runtime_drift,
        "environment": environment,
        "drift_cause": _drift_cause(environment, runtime_drift, error_drift),
        "actual_vs_predicted": {
            "metrics": _observation_metrics(direct),
            "recent": direct[:30],
        },
        "method": "rolling_origin_no_future_leakage",
        "sample_decay": "<=30d:1.0; <=90d:0.75; <=180d:0.5; >180d:0.25",
    }
