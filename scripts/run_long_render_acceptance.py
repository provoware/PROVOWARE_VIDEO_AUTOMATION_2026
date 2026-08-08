#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from videobatch_fast.long_render_contract import (
    LongRenderAcceptance,
    LongRenderContractError,
    install_signal_handlers,
    load_contract,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Begrenzten, wiederaufnehmbaren Langzeitrender-Abnahmevertrag ausführen."
    )
    parser.add_argument("--contract", required=True, type=Path, help="Gebundene JSON-Vertragsdatei")
    parser.add_argument("--state-file", type=Path, help="Abweichender Pfad der atomaren Zustandsdatei")
    parser.add_argument("--resume", action="store_true", help="Vorhandenen identischen Lauf sicher fortsetzen")
    parser.add_argument(
        "--allow-rehearsal-target",
        action="store_true",
        help="Nur für CI-Probeläufe: internes Ziel zulassen; schließt das physische Stable-Gate nicht",
    )
    parser.add_argument(
        "--allow-soft-limits",
        action="store_true",
        help="Nur für CI-Probeläufe: Threadbegrenzung statt systemd-cgroup-Hartgrenzen zulassen",
    )
    parser.add_argument(
        "--evidence-dir",
        type=Path,
        help="Nach vollständig bestandenem realem Lauf sourcegebundenes long_render.json exportieren",
    )
    parser.add_argument(
        "--checkpoint-stop-after",
        type=int,
        default=0,
        help="Kontrollierter Probestopp nach N neuen Aufträgen; Zustand bleibt wiederaufnehmbar",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.checkpoint_stop_after < 0:
        print("FEHLER: --checkpoint-stop-after darf nicht negativ sein.", file=sys.stderr)
        return 2
    try:
        contract = load_contract(args.contract, state_file=args.state_file)
        controller = LongRenderAcceptance(
            contract,
            allow_rehearsal_target=args.allow_rehearsal_target,
            allow_soft_limits=args.allow_soft_limits,
        )
        install_signal_handlers(controller)
        controller.prepare(resume=args.resume)
        state = controller.run(checkpoint_stop_after=args.checkpoint_stop_after)
    except LongRenderContractError as exc:
        print(f"LANGZEITRENDER BLOCKIERT: {exc}", file=sys.stderr)
        return 2

    summary = {
        "run_id": state.get("run_id"),
        "state": state.get("state"),
        "resume_count": state.get("resume_count"),
        "elapsed_seconds": state.get("elapsed_seconds"),
        "completed_jobs": sum(
            1 for item in state.get("jobs", []) if isinstance(item, dict) and item.get("state") == "completed"
        ),
        "total_jobs": len(state.get("jobs", [])),
        "state_file": str(contract.state_file),
        "report": str(contract.state_file.parent / "final-report.json"),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    if state.get("state") == "completed":
        if args.evidence_dir is not None:
            if bool(state.get("rehearsal_only")):
                print("LANGZEITRENDER EVIDENCE BLOCKIERT: Probelauf darf kein Stable-Evidence erzeugen.", file=sys.stderr)
                return 2
            from export_stable_evidence import export_long_render
            export_long_render(contract.state_file.parent / "final-report.json", args.evidence_dir / "long_render.json")
        return 0
    if state.get("state") in {"paused", "paused_timeout", "paused_failure"}:
        return 75
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
