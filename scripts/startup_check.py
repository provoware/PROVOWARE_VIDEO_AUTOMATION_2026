#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from videobatch_fast.config import load_config
from videobatch_fast.os_sandbox import probe_sandbox_support
from videobatch_fast.paths import ensure_app_dirs, state_dir
from videobatch_fast.plugins import scan_plugins
from videobatch_fast.registry import validate_registries
from videobatch_fast.validation import validate_runtime
from videobatch_fast.safe_io import atomic_write_json


def main() -> int:
    started = time.monotonic()
    steps = []
    ensure_app_dirs()
    config = load_config()
    steps.append({"id":"config", "status":"passed", "message":f"Konfiguration Schema {config['schema_version']} bereit"})
    registry_errors = validate_registries()
    steps.append({"id":"registries", "status":"passed" if not registry_errors else "failed", "message":"Registries konsistent" if not registry_errors else "; ".join(registry_errors)})
    runtime = validate_runtime(startup=True)
    runtime_blockers = [issue for issue in runtime if issue.blocking]
    runtime_status = "failed" if runtime_blockers else "warning" if runtime else "passed"
    runtime_message = "FFmpeg und FFprobe bereit" if not runtime else "; ".join(issue.message for issue in runtime)
    steps.append({"id":"runtime", "status":runtime_status, "message":runtime_message})
    plugins = scan_plugins(quarantine_invalid=True)
    invalid_plugins = [item for item in plugins if not item.valid]
    sandbox = probe_sandbox_support()
    sandbox_status = "passed" if sandbox.available else "warning"
    steps.append({
        "id": "plugin_sandbox",
        "status": sandbox_status,
        "message": sandbox.message if sandbox.available else f"Plugin-Ausführung deaktiviert: {sandbox.message}",
    })
    steps.append({"id":"plugins", "status":"warning" if invalid_plugins else "passed", "message":f"{len(plugins)} Plugin(s) geprüft · {len(invalid_plugins)} deaktiviert"})
    failed = [item for item in steps if item["status"] == "failed"]
    warned = [item for item in steps if item["status"] == "warning"]
    status = "degraded" if failed else "warning" if warned else "ready"
    report = {
        "schema_version": 2,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "elapsed": time.monotonic() - started,
        "status": status,
        "steps": steps,
        "solution": "VideoBatch öffnet sich sicher; betroffene Funktionen werden im Tool sichtbar begrenzt." if status != "ready" else "provoware - videoautomation - 2026 starten.",
    }
    directory = state_dir() / "startup"
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "latest.json"
    atomic_write_json(path, report)
    for index, step in enumerate(steps, start=1):
        marker = "✓" if step["status"] == "passed" else "!" if step["status"] == "warning" else "✕"
        print(f"[{index}/{len(steps)}] {marker} {step['message']}")
    print(f"STARTSTATUS: {report['status']} · {report['elapsed']:.2f} s")
    print(f"Bericht: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
