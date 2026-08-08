from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any, Iterable

from .models import BatchOptions, JobResult, PairJob
from .paths import state_dir
from .safe_io import atomic_write_json, fsync_directory, read_json
from .scheduler_environment import maybe_rebaseline_from_job_history, safe_capture_render_environment

SCHEMA_VERSION = 2


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def _options_payload(options: BatchOptions) -> dict[str, Any]:
    return {
        "output_dir": str(options.output_dir),
        "output_mode": options.output_mode,
        "resolution": options.resolution,
        "codec": options.codec,
        "profile": options.profile,
        "verification": options.verification,
        "keep_lists": options.keep_lists,
        "audio_bitrate": options.audio_bitrate,
        "fps": options.fps,
        "max_threads": options.max_threads,
        "visual_effect": options.visual_effect,
        "transition": options.transition,
        "quick_mode": options.quick_mode,
        "assignment_mode": options.assignment_mode,
        "slideshow_transition": options.slideshow_transition,
        "slideshow_scene_sync": options.slideshow_scene_sync,
    }


def _job_payload(job: PairJob) -> dict[str, Any]:
    return {
        "index": job.index,
        "audio": str(job.audio),
        "media": str(job.media),
        "media_sequence": [str(path) for path in job.media_sequence],
        "output": str(job.output),
        "fast_path": job.fast_path,
        "state": "pending",
        "attempt": 0,
        "last_error": "",
        "updated_at": _now(),
    }


class BatchJournal:
    """Durable batch state. Active files survive crashes and power loss."""

    def __init__(self, operation_id: str, jobs: Iterable[PairJob], options: BatchOptions | None = None) -> None:
        root = state_dir() / "jobs"
        self.active_dir = root / "active"
        self.history_dir = root / "history"
        self.active_dir.mkdir(parents=True, exist_ok=True)
        self.history_dir.mkdir(parents=True, exist_ok=True)
        self.path = self.active_dir / f"{operation_id}.json"
        self.operation_id = operation_id
        self.data: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "operation_id": operation_id,
            "state": "running",
            "created_at": _now(),
            "updated_at": _now(),
            "jobs": [_job_payload(job) for job in jobs],
            "options": _options_payload(options) if options is not None else {},
            "render_environment": safe_capture_render_environment(options, persist_epoch=True) if options is not None else {},
            "terminal_event": "",
        }
        self._write()

    def _write(self) -> None:
        self.data["updated_at"] = _now()
        atomic_write_json(self.path, self.data)

    def mark_started(self, index: int) -> None:
        item = self._item(index)
        item["state"] = "running"
        item["attempt"] = int(item.get("attempt", 0)) + 1
        item["updated_at"] = _now()
        self._write()

    def mark_finished(self, result: JobResult) -> None:
        item = self._item(result.job.index)
        item["state"] = "completed" if result.success else "failed"
        item["returncode"] = result.returncode
        item["elapsed_seconds"] = round(result.elapsed_seconds, 3)
        item["last_error"] = "" if result.success else result.message
        item["retried"] = result.retried
        item["fallback_mode"] = result.fallback_mode
        item["updated_at"] = _now()
        self._write()

    def finish(self, *, terminal_event: str, cancelled: bool, internal_error: str = "") -> Path:
        has_failed_jobs = any(
            isinstance(item, dict) and item.get("state") == "failed" for item in self.data.get("jobs", [])
        )
        self.data["state"] = (
            "cancelled"
            if cancelled
            else ("failed" if internal_error else ("completed_with_failures" if has_failed_jobs else "completed"))
        )
        self.data["terminal_event"] = terminal_event
        self.data["internal_error"] = internal_error[-16_000:]
        self._write()
        destination = self.history_dir / self.path.name
        os.replace(self.path, destination)
        fsync_directory(self.active_dir)
        fsync_directory(self.history_dir)
        self.path = destination
        environment = self.data.get("render_environment") if isinstance(self.data.get("render_environment"), dict) else {}
        if self.data.get("state") == "completed" and environment.get("fingerprint_sha256") and environment.get("epoch_id"):
            try:
                maybe_rebaseline_from_job_history(environment, self.history_dir)
            except (OSError, ValueError, RuntimeError):
                pass
        return destination

    def _item(self, index: int) -> dict[str, Any]:
        jobs = self.data.get("jobs", [])
        for item in jobs:
            if isinstance(item, dict) and int(item.get("index", -1)) == index:
                return item
        raise KeyError(f"Unbekannter Auftrag {index}")


def recoverable_batches() -> list[dict[str, Any]]:
    active = state_dir() / "jobs" / "active"
    if not active.is_dir():
        return []
    recovered: list[dict[str, Any]] = []
    for path in sorted(active.glob("*.json")):
        try:
            payload = read_json(path)
        except (OSError, ValueError, TypeError):
            continue
        if not isinstance(payload, dict):
            continue
        payload = dict(payload)
        payload["journal_path"] = str(path)
        payload["recoverable_jobs"] = sum(
            1 for item in payload.get("jobs", []) if isinstance(item, dict) and item.get("state") in {"pending", "running", "failed"}
        )
        recovered.append(payload)
    return recovered


def recovery_input_paths(payloads: Iterable[dict[str, Any]]) -> tuple[list[Path], list[Path]]:
    """Return existing inputs for unfinished jobs only, preserving their journal order."""
    audio: list[Path] = []
    media: list[Path] = []
    for payload in payloads:
        for item in payload.get("jobs", []):
            if not isinstance(item, dict) or item.get("state") not in {"pending", "running", "failed"}:
                continue
            audio_path = Path(str(item.get("audio", ""))).expanduser()
            media_path = Path(str(item.get("media", ""))).expanduser()
            sequence = item.get("media_sequence", [])
            sequence_paths = [Path(str(value)).expanduser() for value in sequence] if isinstance(sequence, list) else []
            if audio_path.is_file() and audio_path not in audio:
                audio.append(audio_path)
            candidates = sequence_paths or [media_path]
            for candidate in candidates:
                if candidate.is_file() and candidate not in media:
                    media.append(candidate)
    return audio, media


def recovery_options(payloads: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """Return the newest usable options snapshot without trusting arbitrary keys."""
    allowed = {
        "output_dir", "output_mode", "resolution", "codec", "profile", "verification",
        "keep_lists", "audio_bitrate", "fps", "max_threads", "visual_effect", "transition", "quick_mode",
        "assignment_mode", "slideshow_transition", "slideshow_scene_sync",
    }
    snapshots = [item.get("options") for item in payloads if isinstance(item, dict)]
    for snapshot in reversed(snapshots):
        if isinstance(snapshot, dict):
            return {str(key): value for key, value in snapshot.items() if str(key) in allowed}
    return {}


def acknowledge_recovery(journal_path: Path | str, *, action: str) -> Path:
    """Persist the recovery decision and move the journal to immutable history."""
    source = Path(journal_path).expanduser()
    payload = read_json(source)
    if not isinstance(payload, dict):
        raise ValueError(f"Recovery-Journal ist kein Objekt: {source}")
    payload = dict(payload)
    payload["state"] = "recovered"
    payload["recovery_action"] = str(action)[:80]
    payload["recovered_at"] = _now()
    atomic_write_json(source, payload)
    history = source.parent.parent / "history"
    history.mkdir(parents=True, exist_ok=True)
    destination = history / source.name
    if destination.exists() or destination.is_symlink():
        destination = history / f"{source.stem}__recovered_{time.strftime('%Y%m%d_%H%M%S')}{source.suffix}"
    os.replace(source, destination)
    fsync_directory(source.parent)
    fsync_directory(history)
    return destination
