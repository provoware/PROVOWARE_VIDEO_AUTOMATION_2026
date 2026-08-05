from __future__ import annotations

import hashlib
import json
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .models import JobResult, PairJob
from .paths import state_dir
from .safe_io import atomic_write_json, quarantine_file, read_json

SCHEMA_VERSION = 1
DEFAULT_MAX_ENTRIES = 100
DEFAULT_MAX_ATTEMPTS = 2


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def _job_payload(job: PairJob) -> dict[str, Any]:
    return {
        "index": job.index,
        "audio": str(job.audio.expanduser()),
        "media": str(job.media.expanduser()),
        "media_sequence": [str(path.expanduser()) for path in job.media_sequence],
        "output": str(job.output.expanduser()),
        "fast_path": job.fast_path,
    }


def job_identity(job: PairJob) -> str:
    stable = {
        "audio": str(job.audio.expanduser()),
        "media": str(job.media.expanduser()),
        "media_sequence": [str(path.expanduser()) for path in job.media_sequence],
        "output": str(job.output.expanduser()),
    }
    encoded = json.dumps(stable, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True, slots=True)
class RetryQueueSummary:
    path: Path
    total: int
    retryable: int
    blocked: int
    failed: int
    not_started: int
    max_entries: int
    max_attempts: int
    dropped_total: int

    def as_payload(self) -> dict[str, Any]:
        return {
            "path": str(self.path),
            "total": self.total,
            "retryable": self.retryable,
            "blocked": self.blocked,
            "failed": self.failed,
            "not_started": self.not_started,
            "max_entries": self.max_entries,
            "max_attempts": self.max_attempts,
            "dropped_total": self.dropped_total,
        }


class RetryQueueStore:
    """Durable, bounded list of failed and not-yet-started jobs.

    This store never starts work itself. It only preserves transparent retry
    candidates and marks entries ineligible after the configured attempt limit.
    """

    def __init__(
        self,
        path: Path | None = None,
        *,
        max_entries: int = DEFAULT_MAX_ENTRIES,
        max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    ) -> None:
        if max_entries < 1:
            raise ValueError("Die Wiederanlaufliste muss mindestens einen Eintrag erlauben.")
        if max_attempts < 1:
            raise ValueError("Die Wiederholungsgrenze muss mindestens eins betragen.")
        self.path = Path(path) if path is not None else state_dir() / "jobs" / "retry_queue.json"
        self.max_entries = max_entries
        self.max_attempts = max_attempts
        self._lock = threading.Lock()
        self._data = self._load()

    def _empty(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "updated_at": _now(),
            "max_entries": self.max_entries,
            "max_attempts": self.max_attempts,
            "dropped_total": 0,
            "entries": [],
        }

    def _load(self) -> dict[str, Any]:
        if not self.path.is_file():
            return self._empty()
        try:
            payload = read_json(self.path)
        except (OSError, ValueError, TypeError):
            quarantine_file(self.path, label="retry-queue-corrupt")
            return self._empty()
        if not isinstance(payload, dict) or not isinstance(payload.get("entries"), list):
            quarantine_file(self.path, label="retry-queue-invalid")
            return self._empty()
        entries = [item for item in payload["entries"] if isinstance(item, dict) and item.get("job_id")]
        data = self._empty()
        data["dropped_total"] = max(0, int(payload.get("dropped_total", 0) or 0))
        data["entries"] = entries[-self.max_entries :]
        if len(entries) > self.max_entries:
            data["dropped_total"] += len(entries) - self.max_entries
        return data

    def _write(self) -> None:
        self._data["updated_at"] = _now()
        self._data["max_entries"] = self.max_entries
        self._data["max_attempts"] = self.max_attempts
        atomic_write_json(self.path, self._data)

    def _find_index(self, job_id: str) -> int | None:
        entries = self._data["entries"]
        for index, item in enumerate(entries):
            if item.get("job_id") == job_id:
                return index
        return None

    def _upsert(self, entry: dict[str, Any]) -> dict[str, Any]:
        entries = self._data["entries"]
        existing = self._find_index(str(entry["job_id"]))
        if existing is not None:
            entries.pop(existing)
        entries.append(entry)
        overflow = max(0, len(entries) - self.max_entries)
        if overflow:
            del entries[:overflow]
            self._data["dropped_total"] = int(self._data.get("dropped_total", 0)) + overflow
        self._write()
        return dict(entry)

    def record_failure(
        self,
        result: JobResult,
        *,
        operation_id: str,
        protection: str,
        failure_kind: str = "processing",
    ) -> dict[str, Any]:
        with self._lock:
            job_id = job_identity(result.job)
            existing_index = self._find_index(job_id)
            existing = self._data["entries"][existing_index] if existing_index is not None else {}
            attempts = max(0, int(existing.get("attempts", 0) or 0)) + 1
            first_error = str(existing.get("first_error", "") or result.message)
            retry_allowed = attempts < self.max_attempts
            entry = {
                "job_id": job_id,
                **_job_payload(result.job),
                "state": "failed" if retry_allowed else "limit_reached",
                "failure_kind": str(failure_kind)[:80],
                "attempts": attempts,
                "max_attempts": self.max_attempts,
                "retry_allowed": retry_allowed,
                "first_error": first_error[:4000],
                "latest_error": str(result.message)[:4000],
                "returncode": int(result.returncode),
                "protection": str(protection)[:4000],
                "operation_id": str(operation_id)[:80],
                "updated_at": _now(),
            }
            return self._upsert(entry)

    def record_not_started(
        self,
        job: PairJob,
        *,
        operation_id: str,
        reason: str,
        protection: str,
    ) -> dict[str, Any]:
        with self._lock:
            job_id = job_identity(job)
            existing_index = self._find_index(job_id)
            existing = self._data["entries"][existing_index] if existing_index is not None else {}
            attempts = max(0, int(existing.get("attempts", 0) or 0))
            retry_allowed = attempts < self.max_attempts
            first_error = str(existing.get("first_error", "") or reason)
            entry = {
                "job_id": job_id,
                **_job_payload(job),
                "state": "not_started" if retry_allowed else "limit_reached",
                "failure_kind": "not_started",
                "attempts": attempts,
                "max_attempts": self.max_attempts,
                "retry_allowed": retry_allowed,
                "first_error": first_error[:4000],
                "latest_error": str(reason)[:4000],
                "returncode": None,
                "protection": str(protection)[:4000],
                "operation_id": str(operation_id)[:80],
                "updated_at": _now(),
            }
            return self._upsert(entry)

    def record_success(self, job: PairJob) -> bool:
        with self._lock:
            index = self._find_index(job_identity(job))
            if index is None:
                return False
            self._data["entries"].pop(index)
            self._write()
            return True

    def entries(self) -> tuple[dict[str, Any], ...]:
        with self._lock:
            return tuple(dict(item) for item in self._data["entries"])

    def eligible_entries(self) -> tuple[dict[str, Any], ...]:
        return tuple(item for item in self.entries() if bool(item.get("retry_allowed")))

    def summary(self) -> RetryQueueSummary:
        entries = self.entries()
        retryable = sum(bool(item.get("retry_allowed")) for item in entries)
        blocked = sum(item.get("state") == "limit_reached" for item in entries)
        failed = sum(item.get("state") in {"failed", "limit_reached"} for item in entries)
        not_started = sum(item.get("state") == "not_started" for item in entries)
        return RetryQueueSummary(
            path=self.path,
            total=len(entries),
            retryable=retryable,
            blocked=blocked,
            failed=failed,
            not_started=not_started,
            max_entries=self.max_entries,
            max_attempts=self.max_attempts,
            dropped_total=max(0, int(self._data.get("dropped_total", 0) or 0)),
        )
