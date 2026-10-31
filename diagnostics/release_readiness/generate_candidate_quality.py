#!/usr/bin/env python3
"""Derive candidate-only quality/status from explicit run evidence.

Never modifies the historical RC24 evidence or release status artifacts.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
INPUT = ROOT / "CANDIDATE_PR240_CI_EVIDENCE.json"
OUTPUT = ROOT / "CANDIDATE_PR240_QUALITY_STATUS.json"
RELEASE_MANIFEST = ROOT.parents[1] / "RELEASE_MANIFEST.json"
ACCEPTANCE_DIR = ROOT / "CANDIDATE_PR240_ACCEPTANCE"


def _physical_acceptance_valid(snapshot: dict) -> bool:
    """Reuse the existing manifest-bound physical acceptance validator."""
    required = ("kubuntu_26_04_wayland.json", "long_render.json")
    try:
        raw = RELEASE_MANIFEST.read_bytes()
        current = json.loads(raw)
        candidate_dir = ACCEPTANCE_DIR / str(current["version"])
        if not all((candidate_dir / name).is_file() for name in required):
            return False
        if any(current.get(key) != snapshot.get(key)
               for key in ("file_count", "files_sha256")):
            return False
        check = subprocess.run(
            [
                sys.executable,
                str(ROOT.parents[1] / "scripts/validate_stable_acceptance.py"),
                "--evidence-dir", str(candidate_dir),
                "--candidate", str(current["version"]),
                "--manifest-sha256", hashlib.sha256(raw).hexdigest(),
            ],
            check=False, capture_output=True, text=True, timeout=20,
        )
    except (OSError, KeyError, ValueError, subprocess.TimeoutExpired):
        return False
    return check.returncode == 0


def build() -> dict:
    evidence = json.loads(INPUT.read_text(encoding="utf-8"))
    if evidence.get("kind") != "development_candidate_ci_evidence":
        raise ValueError("Unbekannter Kandidaten-Nachweistyp")
    checks = evidence.get("checks")
    if not isinstance(checks, list) or len(checks) != 8:
        raise ValueError("Acht einzelne Prüfungen sind erforderlich")
    source = evidence.get("source_commit")
    if not isinstance(source, str) or re.fullmatch(r"[0-9a-f]{40}", source) is None:
        raise ValueError("Ungültiger vollständiger Kandidaten-Commit")
    names = [item.get("name") for item in checks if isinstance(item, dict)]
    if len(names) != 8 or len(set(names)) != 8:
        raise ValueError("Die acht Prüfnamen müssen eindeutig sein")
    for item in checks:
        if item.get("source_commit") != source:
            raise ValueError("Ein Prüfnachweis gehört zu einem anderen Commit")
        if item.get("conclusion") not in {"success", "failure", "cancelled", "timed_out"}:
            raise ValueError("Unbekanntes oder unvollständiges Prüfergebnis")
        run_id = item.get("run_id")
        if type(run_id) is not int or run_id < 1:
            raise ValueError("Fehlende GitHub-Prüflaufnummer")
        expected = ("https://github.com/provoware/PROVOWARE_VIDEO_AUTOMATION_2026/"
                    f"actions/runs/{run_id}")
        if item.get("url") != expected:
            raise ValueError("GitHub-URL passt nicht zur Prüflaufnummer")
    if evidence.get("release_approval") is not False or evidence.get("stable_ready") is not False:
        raise ValueError("Entwicklungsnachweise sind keine Release-Freigabe")
    manifest = evidence.get("source_release_manifest")
    if not isinstance(manifest, dict) or type(manifest.get("file_count")) is not int:
        raise ValueError("Kandidaten-Manifest ist unvollständig")
    if manifest["file_count"] <= 0 or not isinstance(manifest.get("files_sha256"), str):
        raise ValueError("Kandidaten-Manifest enthält keine gültigen Zahlen")
    if re.fullmatch(r"[0-9a-f]{64}", manifest["files_sha256"]) is None:
        raise ValueError("Kandidaten-Manifest enthält keine gültige SHA-256-Prüfsumme")
    measured = evidence.get("latest_observed_candidate_ci")
    if not isinstance(measured, dict):
        raise ValueError("Messnachweise fehlen")
    measured_source = measured.get("source_commit")
    if not isinstance(measured_source, str) or re.fullmatch(r"[0-9a-f]{40}", measured_source) is None:
        raise ValueError("Der gemessene Quellcommit fehlt")
    regression = measured.get("core_regression")
    if not isinstance(regression, dict):
        raise ValueError("Kern-Testnachweis fehlt")
    if regression.get("source_commit") not in (None, measured_source):
        raise ValueError("Widersprüchliche Testherkunft")
    if measured.get("offline_quality", {}).get("result") != "passed":
        raise ValueError("Offline-Qualitätsnachweis nicht erfolgreich")
    if type(regression.get("passed")) is not int or regression["passed"] <= 0:
        raise ValueError("Keine belegte positive Kern-Testzahl")
    if type(regression.get("failed")) is not int or regression["failed"] != 0:
        raise ValueError("Kernregression enthält fehlgeschlagene oder ungültige Tests")
    results = {item["name"]: item["conclusion"] for item in checks}
    failures = sorted(name for name, value in results.items() if value != "success")
    physical_valid = _physical_acceptance_valid(manifest)
    prereqs_passed = all(
        value == "success"
        for name, value in results.items()
        if name != "Release contract sync"  # Self-referential gate.
    )
    preflight_ready = physical_valid and prereqs_passed and source == measured_source
    if not physical_valid:
        failures.append("Physische Kubuntu-/Wayland-Abnahme")
    return {
        "schema_version": 1,
        "kind": "candidate_only_status",
        "candidate_commit": source,
        "measured_source_commit": measured_source,
        "manifest": evidence["source_release_manifest"],
        "historical_release_evidence_separate": True,
        "ci_checks": results,
        "verified_core_partition": {
            "passed": regression["passed"],
            "failed": regression["failed"],
            "job_id": regression["job_id"],
            "workflow_run_id": regression["workflow_run_id"],
        },
        "quality_tools": measured["offline_quality"],
        "blocking_checks": sorted(failures),
        "physical_ui_acceptance": "passed" if physical_valid else "open",
        "release_approved": False,
        "ready_to_merge": preflight_ready,
        "note": "CI records describe the cited candidate snapshot; never extrapolate to later commits.",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    rendered = json.dumps(build(), ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.check:
        if not OUTPUT.is_file() or OUTPUT.read_text(encoding="utf-8") != rendered:
            print("Kandidaten-Qualitätsbericht fehlt oder weicht vom Nachweis ab")
            return 1
        print("Kandidaten-Qualitätsbericht konsistent")
        return 0
    OUTPUT.write_text(rendered, encoding="utf-8")
    print(f"Kandidaten-Qualitätsbericht erzeugt: {OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
