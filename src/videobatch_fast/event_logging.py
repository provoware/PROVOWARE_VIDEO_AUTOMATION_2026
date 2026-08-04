from __future__ import annotations

import json
import os
import re
import time
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .paths import state_dir
from .safe_io import atomic_write_json

ANSI_RE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
SECRET_RE = re.compile(r"(?i)(token|password|secret|api[_-]?key)\s*[:=]\s*\S+")
HOME = str(Path.home())


def safe_text(value: Any, limit: int = 4000) -> str:
    text = ANSI_RE.sub("", str(value)).replace("\x00", "")
    text = SECRET_RE.sub(lambda m: f"{m.group(1)}=<entfernt>", text)
    if HOME and HOME != "/":
        text = text.replace(HOME, "~")
    text = "".join(ch if ch in "\n\t" or ord(ch) >= 32 else " " for ch in text)
    return text[:limit]


@dataclass(frozen=True, slots=True)
class EventRecord:
    timestamp: str
    session_id: str
    operation_id: str
    event_id: str
    level: str
    title: str
    message: str
    detail: str
    solution: str
    status: str


class EventLogger:
    def __init__(self, session_id: str | None = None) -> None:
        self.session_id = session_id or uuid.uuid4().hex[:12]
        self.root = state_dir() / "events"
        self.root.mkdir(parents=True, exist_ok=True)
        self.jsonl_path = self.root / f"session_{self.session_id}.jsonl"
        self.human_path = self.root / f"session_{self.session_id}.log"
        self.latest_path = self.root / "latest_session.json"
        self._prepare_log_file(self.jsonl_path)
        self._prepare_log_file(self.human_path)
        self._prune_logs()


    @staticmethod
    def _prepare_log_file(path: Path) -> None:
        if not path.exists():
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            os.close(fd)
        else:
            try:
                os.chmod(path, 0o600)
            except OSError:
                pass

    def _prune_logs(self, max_files: int = 40, max_bytes: int = 5 * 1024 * 1024) -> None:
        for path in (self.jsonl_path, self.human_path):
            try:
                if path.stat().st_size > max_bytes:
                    rotated = path.with_name(f"{path.stem}.{int(time.time())}{path.suffix}")
                    os.replace(path, rotated)
                    self._prepare_log_file(path)
            except OSError:
                pass
        files = sorted(
            (item for item in self.root.glob("session_*") if item.is_file()),
            key=lambda item: item.stat().st_mtime,
            reverse=True,
        )
        for old in files[max_files:]:
            try:
                old.unlink()
            except OSError:
                pass

    def write(
        self,
        event_id: str,
        title: str,
        message: str,
        *,
        level: str = "info",
        detail: str = "",
        solution: str = "",
        status: str = "recorded",
        operation_id: str = "general",
    ) -> EventRecord:
        record = EventRecord(
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            session_id=self.session_id,
            operation_id=safe_text(operation_id, 120),
            event_id=safe_text(event_id, 120),
            level=safe_text(level, 40),
            title=safe_text(title, 240),
            message=safe_text(message),
            detail=safe_text(detail, 8000),
            solution=safe_text(solution, 2000),
            status=safe_text(status, 80),
        )
        payload = asdict(record)
        with self.jsonl_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")
            handle.flush()
        with self.human_path.open("a", encoding="utf-8") as handle:
            marker = {"success": "✓", "warning": "!", "error": "✕", "technical": ">"}.get(level, "•")
            handle.write(f"{record.timestamp} {marker} {record.title}\n{record.message}\n")
            if record.solution:
                handle.write(f"Lösung: {record.solution}\n")
            if record.detail:
                handle.write(f"Details: {record.detail}\n")
            handle.write("\n")
            handle.flush()
        self._write_latest(payload)
        return record

    def _write_latest(self, payload: dict[str, Any]) -> None:
        atomic_write_json(self.latest_path, payload)
