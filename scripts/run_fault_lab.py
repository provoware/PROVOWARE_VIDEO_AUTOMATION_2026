#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from videobatch_fast.fault_lab import report_payload, run_fault_lab, scenario_names
from videobatch_fast.paths import state_dir
from videobatch_fast.safe_io import atomic_write_json


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Führt das zerstörungsfreie VideoBatch-Fehlerlabor aus.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--output", type=Path, help="Ziel für den vollständigen JSON-Bericht")
    parser.add_argument(
        "--workspace",
        type=Path,
        help="Optionaler isolierter Arbeitsordner; ohne Angabe wird ein temporärer Ordner verwendet",
    )
    parser.add_argument(
        "--scenario",
        action="append",
        choices=scenario_names(),
        help="Nur dieses Szenario ausführen; mehrfach verwendbar",
    )
    parser.add_argument(
        "--repeat",
        type=int,
        default=1,
        help="Ausgewählte Szenarien wiederholen, um sporadische Fehler sichtbar zu machen (1–25)",
    )
    parser.add_argument("--list", action="store_true", help="Verfügbare Szenarien ausgeben und beenden")
    parser.add_argument("--json-stdout", action="store_true", help="Zusätzlich den Bericht als JSON ausgeben")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    if args.list:
        for name in scenario_names():
            print(name)
        return 0
    if not 1 <= args.repeat <= 25:
        parser.error("--repeat muss zwischen 1 und 25 liegen")

    selected = set(args.scenario or scenario_names())
    results = []
    for run_number in range(1, args.repeat + 1):
        run_workspace = None
        if args.workspace is not None:
            run_workspace = args.workspace / f"run-{run_number:02d}"
        current = run_fault_lab(run_workspace, selected)
        if args.repeat > 1:
            current = [replace(item, scenario_id=f"run-{run_number:02d}/{item.scenario_id}") for item in current]
        results.extend(current)

    payload = report_payload(results)
    payload["created_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    payload["repeat"] = args.repeat
    payload["selected_scenarios"] = sorted(selected)
    target = args.output or state_dir() / "fault_lab" / "latest.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_json(target, payload)

    print(f"FEHLERLABOR: {payload['passed']}/{payload['total']} bestanden")
    for item in results:
        print(f"{'✓' if item.status == 'pass' else '✕'} {item.scenario_id}: {item.message}")
    print(f"Bericht: {target}")
    if args.json_stdout:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
