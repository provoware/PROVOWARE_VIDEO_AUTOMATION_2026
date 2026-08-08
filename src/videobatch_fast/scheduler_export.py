from __future__ import annotations

import csv
import hashlib
import io
import json
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any

from .safe_io import atomic_commit_file
from .scheduler import list_schedules
from .scheduler_calibration import build_forecast_quality_report, list_forecast_observations
from .scheduler_forecast import load_render_samples
from .scheduler_history import list_scheduler_history
from .scheduler_environment import list_environment_epochs
from .scheduler_policy import load_scheduler_policy
from .scheduler_queue import list_queue_entries

EXPORT_SCHEMA_VERSION = 1


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _csv_bytes(rows: list[dict[str, Any]]) -> bytes:
    output = io.StringIO(newline="")
    fields = ["schedule_id", "status", "next_run_at", "occurrence_index", "priority", "project_path"]
    writer = csv.DictWriter(output, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        governance = row.get("governance") if isinstance(row.get("governance"), dict) else {}
        writer.writerow({**row, "priority": governance.get("priority", 50)})
    return output.getvalue().encode("utf-8")


def export_scheduler_state(project_path: Path, destination: Path, *, now: datetime | None = None) -> Path:
    current = now or datetime.now().astimezone()
    project = project_path.expanduser().resolve()
    schedules = list_schedules(project_path=project)
    history = list_scheduler_history(project_path=project, limit=500)
    schedule_ids = {str(item.get("schedule_id", "")) for item in schedules}
    queue = [item for item in list_queue_entries() if item.get("schedule_id") in schedule_ids]
    observations = list_forecast_observations(project_path=project, limit=500)
    forecast_quality = build_forecast_quality_report(samples=load_render_samples(), observations=observations)
    files = {
        "schedules.json": _json_bytes(schedules),
        "schedules.csv": _csv_bytes(schedules),
        "history.json": _json_bytes(history),
        "queue.json": _json_bytes(queue),
        "policy.json": _json_bytes(load_scheduler_policy()),
        "forecast-quality.json": _json_bytes(forecast_quality),
        "forecast-actual-vs-predicted.json": _json_bytes(observations),
        "forecast-environment-epochs.json": _json_bytes(list_environment_epochs()),
    }
    manifest = {
        "schema_version": EXPORT_SCHEMA_VERSION,
        "generated_at": current.isoformat(timespec="seconds"),
        "project_path": str(project),
        "files": {
            name: {"size": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}
            for name, payload in sorted(files.items())
        },
    }
    files["manifest.json"] = _json_bytes(manifest)
    target_dir = destination.expanduser().resolve()
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / f"videobatch_scheduler_export_{current.strftime('%Y%m%d_%H%M%S')}.zip"
    temporary = target_dir / f".{target.name}.tmp"
    with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, payload in sorted(files.items()):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.external_attr = 0o644 << 16
            archive.writestr(info, payload)
    return atomic_commit_file(temporary, target)
