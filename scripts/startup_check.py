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
from videobatch_fast.safe_io import atomic_write_json
from videobatch_fast.validation import validate_runtime

_STEP_LABELS = {
    "config": "Konfiguration",
    "registries": "Register",
    "runtime": "Medienwerkzeuge",
    "plugin_sandbox": "Plugin-Isolierung",
    "plugins": "Plugins",
}


def _step(step_id: str, status: str, message: str, solution: str, *, impact: str = "") -> dict[str, str]:
    return {
        "id": step_id,
        "label": _STEP_LABELS[step_id],
        "status": status,
        "message": message,
        "impact": impact or "Keine Einschränkung erkannt.",
        "protection": "Start bleibt kontrolliert; unsichere oder fehlende Funktionen werden nicht automatisch ausgeführt.",
        "solution": solution,
        "alternative": "Mit den verfügbaren Kernfunktionen weiterarbeiten und betroffene Funktion später erneut prüfen.",
    }


def _status_marker(status: str) -> str:
    return {"passed": "✓", "warning": "!", "failed": "✕"}.get(status, "?")


def main() -> int:
    started = time.monotonic()
    steps = []
    ensure_app_dirs()
    config = load_config()
    steps.append(_step("config", "passed", f"Schema {config['schema_version']} geladen", "Keine Aktion nötig."))
    registry_errors = validate_registries()
    steps.append(_step(
        "registries",
        "passed" if not registry_errors else "failed",
        "Registries konsistent" if not registry_errors else "; ".join(registry_errors),
        "Registry-Dateien aus dem Paket wiederherstellen oder Release-Paket frisch prüfen.",
        impact="Betroffene Auswahllisten werden blockiert." if registry_errors else "Keine Einschränkung erkannt.",
    ))
    runtime = validate_runtime(startup=True)
    runtime_blockers = [issue for issue in runtime if issue.blocking]
    runtime_status = "failed" if runtime_blockers else "warning" if runtime else "passed"
    runtime_message = "FFmpeg und FFprobe bereit" if not runtime else "; ".join(issue.message for issue in runtime)
    steps.append(_step(
        "runtime",
        runtime_status,
        runtime_message,
        "FFmpeg/FFprobe installieren oder den mitgelieferten Runtime-Ordner erneut vorbereiten.",
        impact="Medienprüfung oder Rendern startet erst nach erneuter Werkzeugprüfung." if runtime else "Keine Einschränkung erkannt.",
    ))
    plugins = scan_plugins(quarantine_invalid=True)
    invalid_plugins = [item for item in plugins if not item.valid]
    sandbox = probe_sandbox_support()
    sandbox_status = "passed" if sandbox.available else "warning"
    steps.append(_step(
        "plugin_sandbox",
        sandbox_status,
        sandbox.message if sandbox.available else f"Plugin-Ausführung deaktiviert: {sandbox.message}",
        "bubblewrap/Firejail oder die dokumentierte OS-Isolierung aktivieren; bis dahin Plugins deaktiviert lassen.",
        impact="Plugins bleiben deaktiviert." if not sandbox.available else "Keine Einschränkung erkannt.",
    ))
    steps.append(_step(
        "plugins",
        "warning" if invalid_plugins else "passed",
        f"{len(plugins)} Plugin(s) geprüft · {len(invalid_plugins)} deaktiviert",
        "Plugin-Signatur, Manifest-Capabilities und sichtbare Freigabe prüfen.",
        impact="Ungültige Plugins wurden quarantänisiert." if invalid_plugins else "Keine Einschränkung erkannt.",
    ))
    failed = [item for item in steps if item["status"] == "failed"]
    warned = [item for item in steps if item["status"] == "warning"]
    status = "degraded" if failed else "warning" if warned else "ready"
    report = {
        "schema_version": 3,
        "tool_language": "de-DE-simple",
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
        print(f"[{index}/{len(steps)}] {_status_marker(step['status'])} {step['label']}: {step['message']}")
        if step["status"] != "passed":
            print(f"    Auswirkung: {step['impact']}")
            print(f"    Lösung: {step['solution']}")
    print(f"STARTSTATUS: {report['status']} · {report['elapsed']:.2f} s")
    print(f"Bericht: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
