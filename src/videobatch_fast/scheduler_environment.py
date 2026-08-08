from __future__ import annotations

import hashlib
import json
import os
import platform
import re
import subprocess
import time
import uuid
from functools import lru_cache
from pathlib import Path
from typing import Any

from .paths import state_dir
from .probe import ffmpeg_path
from .safe_io import atomic_write_json, exclusive_file_lock

ENVIRONMENT_SCHEMA_VERSION = 1
EPOCH_SCHEMA_VERSION = 1
_MAX_PROFILE_TEXT = 160
_NETWORK_FS = {"nfs", "nfs4", "cifs", "smb3", "sshfs", "fuse.sshfs", "davfs", "davfs2", "9p"}
_HARDWARE_ENCODER_TOKENS = ("nvenc", "qsv", "vaapi", "amf", "videotoolbox", "v4l2m2m")


def _clean(value: object, limit: int = _MAX_PROFILE_TEXT) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()[:limit]


def _cpu_model() -> str:
    processor = _clean(platform.processor())
    if processor:
        return processor
    try:
        for line in Path("/proc/cpuinfo").read_text(encoding="utf-8", errors="replace").splitlines():
            if line.lower().startswith("model name") and ":" in line:
                return _clean(line.split(":", 1)[1])
    except OSError:
        pass
    return _clean(platform.machine()) or "unknown"


def _binary_cache_key(binary: str) -> tuple[str, int, int]:
    try:
        stat = Path(binary).stat()
        return binary, int(stat.st_mtime_ns), int(stat.st_size)
    except OSError:
        return binary, 0, 0


@lru_cache(maxsize=8)
def _ffmpeg_identity_cached(binary: str, mtime_ns: int, size: int) -> dict[str, str]:
    del mtime_ns, size
    if not binary:
        return {"version": "not-found", "build_sha256": "", "binary": ""}
    try:
        version = subprocess.run(
            [binary, "-version"], capture_output=True, text=True, timeout=5, check=False, errors="replace"
        ).stdout.splitlines()
        build = subprocess.run(
            [binary, "-buildconf"], capture_output=True, text=True, timeout=5, check=False, errors="replace"
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return {"version": "unknown", "build_sha256": "", "binary": Path(binary).name}
    first = version[0] if version else ""
    version_text = _clean(first.replace("ffmpeg version ", "").split(" Copyright", 1)[0], 120) or "unknown"
    build_hash = hashlib.sha256(build.encode("utf-8", errors="replace")).hexdigest() if build else ""
    return {"version": version_text, "build_sha256": build_hash, "binary": Path(binary).name}


def ffmpeg_identity() -> dict[str, str]:
    binary = ffmpeg_path()
    return _ffmpeg_identity_cached(*_binary_cache_key(binary)) if binary else {
        "version": "not-found", "build_sha256": "", "binary": ""
    }


def _existing_path(path: Path) -> Path:
    candidate = path.expanduser()
    while not candidate.exists() and candidate != candidate.parent:
        candidate = candidate.parent
    return candidate


def _mount_identity(path: Path) -> tuple[str, str, str]:
    target = _existing_path(path).resolve()
    best: tuple[int, str, str, str] | None = None
    try:
        lines = Path("/proc/self/mountinfo").read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return "unknown", "unknown", ""
    for line in lines:
        left, marker, right = line.partition(" - ")
        if not marker:
            continue
        fields = left.split()
        detail = right.split()
        if len(fields) < 5 or len(detail) < 2:
            continue
        mountpoint = fields[4].replace("\\040", " ")
        try:
            mount = Path(mountpoint).resolve()
            target.relative_to(mount)
        except (OSError, ValueError):
            continue
        score = len(str(mount))
        if best is None or score > best[0]:
            best = (score, detail[0], detail[1], str(mount))
    if best is None:
        return "unknown", "unknown", ""
    return best[1], best[2], best[3]


def _medium_class(fs_type: str, source: str, mountpoint: str) -> str:
    fs = fs_type.lower()
    source_lower = source.lower()
    mount_lower = mountpoint.lower()
    if fs in _NETWORK_FS or source_lower.startswith("//") or ":/" in source_lower:
        return "network"
    if mount_lower.startswith(("/media/", "/run/media/")):
        return "removable"
    if source_lower.startswith(("/dev/sd", "/dev/mmc", "/dev/disk/by-id/usb-")) and mountpoint not in {"", "/"}:
        return "removable"
    if fs == "unknown":
        return "unknown"
    return "local"


def _encoder_path(codec: str) -> str:
    value = _clean(codec, 80).lower()
    for token in _HARDWARE_ENCODER_TOKENS:
        if token in value:
            return token
    return "software"


def _profile_payload(profile: dict[str, Any]) -> dict[str, Any]:
    return {
        "machine": profile.get("machine", ""),
        "cpu_model": profile.get("cpu_model", ""),
        "cpu_count": profile.get("cpu_count", 0),
        "thread_limit": profile.get("thread_limit", 0),
        "ffmpeg_version": profile.get("ffmpeg_version", ""),
        "ffmpeg_build_sha256": profile.get("ffmpeg_build_sha256", ""),
        "encoder_path": profile.get("encoder_path", ""),
        "target_fs": profile.get("target_fs", ""),
        "target_medium": profile.get("target_medium", ""),
    }


def environment_fingerprint(profile: dict[str, Any]) -> str:
    canonical = json.dumps(_profile_payload(profile), sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _option(options: Any, name: str, default: Any = "") -> Any:
    if isinstance(options, dict):
        return options.get(name, default)
    return getattr(options, name, default)


def capture_render_environment(options: Any, *, persist_epoch: bool = False) -> dict[str, Any]:
    output_dir = Path(str(_option(options, "output_dir", "") or ".")).expanduser()
    codec = _clean(_option(options, "codec", ""), 80)
    max_threads = max(0, int(_option(options, "max_threads", 0) or 0))
    ffmpeg = ffmpeg_identity()
    fs_type, source, mountpoint = _mount_identity(output_dir)
    profile: dict[str, Any] = {
        "schema_version": ENVIRONMENT_SCHEMA_VERSION,
        "machine": _clean(platform.machine(), 80).lower() or "unknown",
        "cpu_model": _cpu_model(),
        "cpu_count": max(1, int(os.cpu_count() or 1)),
        "thread_limit": max_threads,
        "ffmpeg_version": ffmpeg["version"],
        "ffmpeg_build_sha256": ffmpeg["build_sha256"],
        "encoder_path": _encoder_path(codec),
        "codec": codec,
        "target_fs": _clean(fs_type, 60).lower() or "unknown",
        "target_medium": _medium_class(fs_type, source, mountpoint),
    }
    profile["fingerprint_sha256"] = environment_fingerprint(profile)
    epoch = current_epoch(profile) if persist_epoch else peek_current_epoch(profile)
    profile["epoch_id"] = str(epoch.get("epoch_id", ""))
    return profile


def _epoch_path() -> Path:
    return state_dir() / "scheduler" / "forecast_epochs.json"


def _epoch_lock() -> Path:
    return state_dir() / "scheduler" / ".forecast-epochs.lock"


def _load_epoch_registry() -> dict[str, Any]:
    path = _epoch_path()
    if not path.is_file() or path.is_symlink():
        return {"schema_version": EPOCH_SCHEMA_VERSION, "environments": {}}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return {"schema_version": EPOCH_SCHEMA_VERSION, "environments": {}}
    if not isinstance(payload, dict) or int(payload.get("schema_version", -1)) != EPOCH_SCHEMA_VERSION:
        return {"schema_version": EPOCH_SCHEMA_VERSION, "environments": {}}
    environments = payload.get("environments")
    payload["environments"] = environments if isinstance(environments, dict) else {}
    return payload


def _new_epoch(environment_id: str, *, reason: str, detail: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "epoch_id": f"ep-{int(time.time())}-{uuid.uuid4().hex[:8]}",
        "environment_id": environment_id,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "reason": reason,
        "detail": dict(detail or {}),
    }


def peek_current_epoch(profile: dict[str, Any]) -> dict[str, Any]:
    environment_id = str(profile.get("fingerprint_sha256") or environment_fingerprint(profile))
    registry = _load_epoch_registry()
    entry = registry.get("environments", {}).get(environment_id)
    if isinstance(entry, dict) and isinstance(entry.get("epochs"), list) and entry.get("active_epoch_id"):
        for epoch in entry["epochs"]:
            if isinstance(epoch, dict) and epoch.get("epoch_id") == entry["active_epoch_id"]:
                return dict(epoch)
    return {"epoch_id": "", "environment_id": environment_id, "reason": "unbaselined", "active": False}


def current_epoch(profile: dict[str, Any]) -> dict[str, Any]:
    environment_id = str(profile.get("fingerprint_sha256") or environment_fingerprint(profile))
    with exclusive_file_lock(_epoch_lock(), timeout_seconds=5.0):
        registry = _load_epoch_registry()
        environments = registry["environments"]
        entry = environments.get(environment_id)
        if isinstance(entry, dict) and isinstance(entry.get("epochs"), list) and entry.get("active_epoch_id"):
            for epoch in entry["epochs"]:
                if isinstance(epoch, dict) and epoch.get("epoch_id") == entry["active_epoch_id"]:
                    return dict(epoch)
        epoch = _new_epoch(environment_id, reason="environment_baseline")
        environments[environment_id] = {"active_epoch_id": epoch["epoch_id"], "epochs": [epoch]}
        atomic_write_json(_epoch_path(), registry)
        return dict(epoch)


def list_environment_epochs(environment_id: str | None = None) -> list[dict[str, Any]]:
    registry = _load_epoch_registry()
    result: list[dict[str, Any]] = []
    for key, entry in registry.get("environments", {}).items():
        if environment_id is not None and key != environment_id:
            continue
        if not isinstance(entry, dict):
            continue
        for epoch in entry.get("epochs", []):
            if isinstance(epoch, dict):
                result.append({**epoch, "active": epoch.get("epoch_id") == entry.get("active_epoch_id")})
    result.sort(key=lambda item: str(item.get("created_at", "")))
    return result


def _history_runtime_observations(profile: dict[str, Any], history_dir: Path, *, limit: int = 30) -> list[dict[str, Any]]:
    environment_id = str(profile.get("fingerprint_sha256", ""))
    epoch_id = str(profile.get("epoch_id", ""))
    result: list[dict[str, Any]] = []
    if not history_dir.is_dir():
        return result
    import statistics

    for path in sorted(history_dir.glob("*.json"), key=lambda item: item.name, reverse=True):
        if len(result) >= max(10, min(int(limit), 100)):
            break
        try:
            if path.is_symlink() or not path.is_file() or path.stat().st_size > 4 * 1024 * 1024:
                continue
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError, json.JSONDecodeError):
            continue
        if not isinstance(payload, dict) or str(payload.get("state")) != "completed":
            continue
        environment = payload.get("render_environment") if isinstance(payload.get("render_environment"), dict) else {}
        if environment.get("fingerprint_sha256") != environment_id or environment.get("epoch_id") != epoch_id:
            continue
        elapsed: list[float] = []
        for job in payload.get("jobs", []):
            if not isinstance(job, dict) or str(job.get("state")) != "completed":
                continue
            try:
                value = float(job.get("elapsed_seconds", 0.0) or 0.0)
            except (TypeError, ValueError):
                continue
            if value > 0.0:
                elapsed.append(value)
        if elapsed:
            result.append({
                "finished_at": str(payload.get("updated_at", "")),
                "environment": dict(environment),
                "actual": {"seconds_per_job": float(statistics.median(elapsed))},
            })
    return list(reversed(result))


def maybe_rebaseline_from_job_history(profile: dict[str, Any], history_dir: Path) -> dict[str, Any] | None:
    observations = _history_runtime_observations(profile, history_dir)
    return maybe_rebaseline_environment(profile, observations)


def maybe_rebaseline_environment(
    profile: dict[str, Any], observations: list[dict[str, Any]], *, min_samples: int = 10
) -> dict[str, Any] | None:
    environment_id = str(profile.get("fingerprint_sha256", ""))
    epoch_id = str(profile.get("epoch_id", ""))
    matching: list[dict[str, Any]] = []
    for item in observations:
        environment = item.get("environment") if isinstance(item.get("environment"), dict) else {}
        actual = item.get("actual") if isinstance(item.get("actual"), dict) else {}
        if environment.get("fingerprint_sha256") != environment_id or environment.get("epoch_id") != epoch_id:
            continue
        try:
            value = float(actual.get("seconds_per_job", 0.0) or 0.0)
        except (TypeError, ValueError):
            continue
        if value > 0.0:
            matching.append({"seconds_per_job": value, "finished_at": str(item.get("finished_at", ""))})
    matching.sort(key=lambda item: item["finished_at"])
    if len(matching) < max(10, int(min_samples)):
        return None
    recent = [item["seconds_per_job"] for item in matching[-5:]]
    baseline = [item["seconds_per_job"] for item in matching[-15:-5]] if len(matching) >= 15 else [item["seconds_per_job"] for item in matching[:-5]]
    if len(baseline) < 5:
        return None
    import statistics

    recent_median = float(statistics.median(recent))
    baseline_median = float(statistics.median(baseline))
    signed_shift = (recent_median - baseline_median) / max(baseline_median, 0.001)
    if abs(signed_shift) < 0.35:
        return None
    with exclusive_file_lock(_epoch_lock(), timeout_seconds=5.0):
        registry = _load_epoch_registry()
        entry = registry["environments"].get(environment_id)
        if not isinstance(entry, dict) or entry.get("active_epoch_id") != epoch_id:
            return None
        epoch = _new_epoch(environment_id, reason="runtime_drift_rebaseline", detail={
            "previous_epoch_id": epoch_id,
            "baseline_seconds_per_job": round(baseline_median, 3),
            "recent_seconds_per_job": round(recent_median, 3),
            "signed_shift_pct": round(signed_shift, 4),
            "supporting_samples": len(matching),
        })
        epochs = entry.get("epochs") if isinstance(entry.get("epochs"), list) else []
        epochs.append(epoch)
        entry["epochs"] = epochs[-20:]
        entry["active_epoch_id"] = epoch["epoch_id"]
        atomic_write_json(_epoch_path(), registry)
        return dict(epoch)


def safe_capture_render_environment(options: Any, *, persist_epoch: bool = False) -> dict[str, Any]:
    try:
        return capture_render_environment(options, persist_epoch=persist_epoch)
    except (OSError, ValueError, RuntimeError):
        fallback = {
            "schema_version": ENVIRONMENT_SCHEMA_VERSION,
            "machine": _clean(platform.machine(), 80).lower() or "unknown",
            "cpu_model": _cpu_model(),
            "cpu_count": max(1, int(os.cpu_count() or 1)),
            "thread_limit": max(0, int(_option(options, "max_threads", 0) or 0)),
            "ffmpeg_version": "unknown",
            "ffmpeg_build_sha256": "",
            "encoder_path": _encoder_path(str(_option(options, "codec", ""))),
            "codec": _clean(_option(options, "codec", ""), 80),
            "target_fs": "unknown",
            "target_medium": "unknown",
            "epoch_id": "",
        }
        fallback["fingerprint_sha256"] = environment_fingerprint(fallback)
        return fallback


def compare_environment_profiles(current: dict[str, Any], previous: dict[str, Any] | None) -> dict[str, Any]:
    if not previous:
        return {"changed": False, "changed_fields": [], "current_environment_id": current.get("fingerprint_sha256"), "previous_environment_id": None}
    fields = tuple(_profile_payload(current))
    changed = [key for key in fields if current.get(key) != previous.get(key)]
    return {
        "changed": bool(changed),
        "changed_fields": changed,
        "current_environment_id": current.get("fingerprint_sha256"),
        "previous_environment_id": previous.get("fingerprint_sha256"),
    }
