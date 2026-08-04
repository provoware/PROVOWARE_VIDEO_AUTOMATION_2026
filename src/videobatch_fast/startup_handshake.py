from __future__ import annotations

import json
import os
import time
from pathlib import Path

from .safe_io import atomic_write_json


def ready_marker_from_environment() -> Path | None:
    value = os.environ.get("VIDEOBATCH_UI_READY_FILE", "").strip()
    return Path(value).expanduser() if value else None


def signal_ui_ready(*, existing_instance: bool = False) -> Path | None:
    """Signal the bootstrap only after the UI is usable or an existing instance was focused."""
    path = ready_marker_from_environment()
    if path is None:
        return None
    startup_status = os.environ.get("VIDEOBATCH_STARTUP_STATUS", "ready").strip().lower() or "ready"
    payload = {
        "schema_version": 2,
        "pid": os.getpid(),
        "timestamp_ns": time.time_ns(),
        "safe_mode": os.environ.get("VIDEOBATCH_SAFE_MODE", "0") == "1",
        "existing_instance": bool(existing_instance),
        "startup_status": startup_status,
        "report_path": os.environ.get("VIDEOBATCH_STARTUP_REPORT", ""),
    }
    atomic_write_json(path, payload)
    return path


def read_ready_marker(path: Path) -> dict[str, object] | None:
    if not path.is_file() or path.is_symlink():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict) or data.get("schema_version") not in {1, 2}:
        return None
    return data
