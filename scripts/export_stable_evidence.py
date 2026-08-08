#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
import platform
import sys
from pathlib import Path
from typing import Any

try:
    from release_identity import ROOT, release_identity
except ModuleNotFoundError:  # Import als scripts.export_stable_evidence
    from scripts.release_identity import ROOT, release_identity
from videobatch_fast.automated_desktop_approval import verify_automated_desktop_approval


def _atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        with temp.open("w", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def _base(kind: str) -> dict[str, Any]:
    identity = release_identity()
    return {
        "schema_version": 2,
        "evidence_type": kind,
        "candidate_id": identity["candidate_id"],
        "manifest_sha256": identity["manifest_sha256"],
        "source_sha256": identity["source_sha256"],
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "result": "passed",
    }


def export_desktop(output: Path) -> Path:
    report = verify_automated_desktop_approval(ROOT)
    if not report.valid:
        raise RuntimeError(f"Automatisierte Desktopprüfung ist nicht gültig: {report.message}")
    session = report.session_type.lower()
    if session not in {"x11", "wayland"}:
        raise RuntimeError(f"Unbekannte reale Sitzung: {session}")
    desktop = os.environ.get("XDG_CURRENT_DESKTOP", "")
    if "kde" not in desktop.lower() and "plasma" not in desktop.lower():
        raise RuntimeError("Physische Stable-Abnahme erfordert eine KDE/Plasma-Sitzung.")
    if not (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")):
        raise RuntimeError("Keine aktive grafische Sitzung erkannt.")
    raw_report = json.loads((ROOT / "AUTOMATED_DESKTOP_APPROVAL.json").read_text(encoding="utf-8"))
    profiles = raw_report.get("scaling_profiles")
    if raw_report.get("physical_acceptance") is not True:
        raise RuntimeError("Desktopbericht stammt nicht aus explizitem physischem Abnahmemodus.")
    if not isinstance(profiles, list) or len(profiles) != 9 or any(not isinstance(item, dict) or item.get("passed") is not True for item in profiles):
        raise RuntimeError("Die vollständige physische 3×3 Skalierungsmatrix ist nicht bestanden.")
    payload = _base(f"kde_{session}")
    payload["environment"] = {
        "system": platform.platform(),
        "session_or_target": f"KDE {session.upper()}",
        "desktop": desktop,
        "display": os.environ.get("DISPLAY", ""),
        "wayland_display": os.environ.get("WAYLAND_DISPLAY", ""),
    }
    payload["checks"] = {
        "physical_session": True,
        "application_started": True,
        "preview_rendered": True,
        "window_scaling_checked": True,
    }
    payload["scaling_profiles"] = profiles
    _atomic_json(output, payload)
    return output


def export_long_render(final_report: Path, output: Path) -> Path:
    data = json.loads(final_report.read_text(encoding="utf-8"))
    jobs = data.get("jobs")
    outputs = (data.get("output_manifest") or {}).get("entries") if isinstance(data.get("output_manifest"), dict) else None
    if data.get("status") != "completed" or data.get("rehearsal_only") is not False:
        raise RuntimeError("Langzeitrender ist nicht als realer vollständiger Lauf abgeschlossen.")
    if not isinstance(jobs, list) or len(jobs) != 96 or not isinstance(outputs, list) or len(outputs) != 96:
        raise RuntimeError("Langzeitrender besitzt nicht exakt 96 abgeschlossene Jobs/Ausgaben.")
    if any(not isinstance(item, dict) or item.get("state") != "completed" or not item.get("output_sha256") for item in jobs):
        raise RuntimeError("Mindestens ein Langzeitrender-Job ist nicht vollständig hashverifiziert.")
    target = data.get("target")
    if not isinstance(target, dict):
        raise RuntimeError("Langzeitrender enthält keinen gebundenen Zielnachweis.")
    target_ok = (
        target.get("external_usb") is True
        and target.get("rehearsal_target") is False
        and str(target.get("filesystem", "")) == "ext4"
        and str(target.get("source", "")).startswith("/dev/")
        and "rw" in set(target.get("mount_options") or [])
        and float(target.get("write_mib_s", 9999.0)) <= 35.0
        and float(target.get("free_gib", 0.0)) >= 500.0
        and bool(str(target.get("filesystem_uuid", "")).strip())
    )
    if not target_ok:
        raise RuntimeError("Langzeitrender-Ziel erfüllt den realen Slow-USB-/ext4-Vertrag nicht.")
    payload = _base("long_render")
    payload["environment"] = {"system": platform.platform(), "session_or_target": target}
    payload["checks"] = {
        "large_media_selection": True,
        "slow_external_target": True,
        "render_completed": True,
        "output_hash_verified": True,
    }
    payload["run_id"] = data.get("run_id")
    payload["output_manifest_digest"] = (data.get("output_manifest") or {}).get("digest")
    _atomic_json(output, payload)
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description="Exportiert maschinell erzeugte, sourcegebundene Stable-Abnahmen.")
    sub = parser.add_subparsers(dest="action", required=True)
    desktop = sub.add_parser("desktop")
    desktop.add_argument("--evidence-dir", type=Path, required=True)
    long_render = sub.add_parser("long-render")
    long_render.add_argument("--final-report", type=Path, required=True)
    long_render.add_argument("--evidence-dir", type=Path, required=True)
    args = parser.parse_args()
    if args.action == "desktop":
        report = verify_automated_desktop_approval(ROOT)
        if not report.valid:
            raise RuntimeError(report.message)
        target = args.evidence_dir / f"kde_{report.session_type.lower()}.json"
        print(export_desktop(target))
    else:
        print(export_long_render(args.final_report, args.evidence_dir / "long_render.json"))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as exc:
        print(f"EVIDENCE-EXPORT BLOCKIERT: {exc}", file=sys.stderr)
        raise SystemExit(14)
