#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, sys, time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from videobatch_fast.fault_lab import report_payload, run_fault_lab
from videobatch_fast.paths import state_dir
from videobatch_fast.safe_io import atomic_write_json

def main()->int:
    parser=argparse.ArgumentParser(description='Führt das zerstörungsfreie VideoBatch-Fehlerlabor aus.')
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    results=run_fault_lab()
    payload=report_payload(results)
    payload['created_at']=time.strftime('%Y-%m-%dT%H:%M:%S%z')
    target=args.output or state_dir()/'fault_lab'/'latest.json'
    target.parent.mkdir(parents=True,exist_ok=True)
    atomic_write_json(target,payload)
    print(f"FEHLERLABOR: {payload['passed']}/{payload['total']} bestanden")
    for item in results:
        print(f"{'✓' if item.status=='pass' else '✕'} {item.scenario_id}: {item.message}")
    print(f"Bericht: {target}")
    return 0 if payload['status']=='passed' else 1
if __name__=='__main__': raise SystemExit(main())
