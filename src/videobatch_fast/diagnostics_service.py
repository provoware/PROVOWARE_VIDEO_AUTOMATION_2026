from __future__ import annotations

import os
import platform
import time
from pathlib import Path

from .paths import state_dir
from .registry import validate_registries
from .safe_io import atomic_write_json
from .versioning import build_label


def _file_info(path: Path) -> dict:
    try:
        stat = path.stat()
        return {"path": str(path), "exists": True, "size": stat.st_size, "modified": stat.st_mtime}
    except OSError:
        return {"path": str(path), "exists": False, "size": 0, "modified": 0}


def build_diagnostic_payload(*, session_id: str, project_file: Path, human_log: Path, machine_log: Path) -> dict:
    return {
        "schema_version": 1,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "tool": "provoware - videoautomation - 2026",
        "build": build_label(),
        "session_id": session_id,
        "system": {
            "platform": platform.platform(),
            "python": platform.python_version(),
            "machine": platform.machine(),
            "locale": os.environ.get("LANG", ""),
        },
        "registry_errors": validate_registries(),
        "files": {
            "project": _file_info(Path(project_file)),
            "human_log": _file_info(Path(human_log)),
            "machine_log": _file_info(Path(machine_log)),
        },
        "recommendation": "Bei Fehlern zuerst Registryfehler, letztes Maschinenereignis und vollständigen technischen Prozessauszug prüfen.",
    }


def write_diagnostic_report(*, session_id: str, project_file: Path, human_log: Path, machine_log: Path) -> Path:
    root = state_dir() / "diagnostics"
    root.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    target = root / f"diagnostic_{stamp}.json"
    payload = build_diagnostic_payload(session_id=session_id, project_file=project_file, human_log=human_log, machine_log=machine_log)
    atomic_write_json(target, payload)
    return target
