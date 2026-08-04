#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from validate_stable_acceptance import manifest_sha256, validate_evidence

ROOT = Path(__file__).resolve().parents[1]


def run(command: list[str], *, cwd: Path, env: dict[str, str], label: str, timeout: int = 7200) -> None:
    print(f"\n▶ {label}", flush=True)
    completed = subprocess.run(command, cwd=cwd, env=env, text=True, check=False, timeout=timeout)
    if completed.returncode:
        raise RuntimeError(f"{label} fehlgeschlagen (Code {completed.returncode}).")
    print(f"✓ {label}", flush=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Finalisiert VideoBatch autonom bis zum Stable-ZIP.")
    parser.add_argument("--output", type=Path, default=ROOT / "dist")
    parser.add_argument("--acceptance-evidence", type=Path, required=True)
    args = parser.parse_args()
    version = json.loads((ROOT / "VERSION.json").read_text(encoding="utf-8"))
    candidate = str(version["build"])
    candidate_hash = manifest_sha256(ROOT / "RELEASE_MANIFEST.json")
    validate_evidence(args.acceptance_evidence, candidate, candidate_hash)
    env_python = Path(sys.executable).resolve()
    if not env_python.is_file():
        raise RuntimeError("Die verifizierte Qualitätsumgebung ist nicht verfügbar.")
    if not (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")):
        raise RuntimeError("Eine aktive grafische Desktop-Sitzung ist für die reale Abschlussprüfung erforderlich.")
    base_env = {
        **os.environ,
        "VIDEOBATCH_QUALITY_PYTHON": str(env_python),
        "VIDEOBATCH_TOOLCHAIN_PYTHON": str(env_python),
        "PYTHONPATH": str(ROOT / "src"),
        "PYTHONDONTWRITEBYTECODE": "1",
    }

    run([str(ROOT / "quality.sh")], cwd=ROOT, env=base_env, label="Externe Qualität und Kernprüfung")
    verified_env = {**base_env, "VIDEOBATCH_QUALITY_ALREADY_VERIFIED": "1"}
    run([str(ROOT / "verify_release.sh")], cwd=ROOT, env=verified_env, label="Releasekandidat vollständig verifizieren")
    run([str(env_python), str(ROOT / "scripts/live_desktop_gate.py")], cwd=ROOT, env=base_env, label="Reale Desktopprüfung des Releasekandidaten")

    args.output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="videobatch-stable-finalize-") as tmp:
        stable = Path(tmp) / "VideoBatch_Fast_2.8.3"
        run([
            str(env_python), str(ROOT / "scripts/promote_stable_workspace.py"),
            "--source", str(ROOT), "--destination", str(stable), "--stable-version", "2.8.3",
        ], cwd=ROOT, env=base_env, label="Getrennte Stable-Arbeitskopie erzeugen")
        stable_env = {
            **base_env, "PYTHONPATH": str(stable / "src"), "VIDEOBATCH_QUALITY_ALREADY_VERIFIED": "1",
            "VIDEOBATCH_ACCEPTANCE_EVIDENCE": str(args.acceptance_evidence.resolve()),
            "VIDEOBATCH_ACCEPTANCE_CANDIDATE": candidate,
            "VIDEOBATCH_ACCEPTANCE_MANIFEST_SHA256": candidate_hash,
        }

        rebuild = (
            "import sys; from pathlib import Path; "
            f"sys.path.insert(0, {str(stable / 'scripts')!r}); "
            "from toolchain_common import load_contract,rebuild_wheelhouse_metadata; "
            f"root=Path({str(stable)!r}); c=load_contract(root); "
            "rebuild_wheelhouse_metadata(root/c['paths']['wheelhouse'], c, root=root)"
        )
        run([str(env_python), "-c", rebuild], cwd=stable, env=stable_env, label="Stable-Wheelhouse neu an Stable binden")
        run([str(env_python), str(stable / "scripts/validate_version_contract.py")], cwd=stable, env=stable_env, label="Stable-Versionsvertrag prüfen")
        run([
            str(env_python), str(stable / "scripts/capture_visual_scenarios.py"), "--accept-baselines"
        ], cwd=stable, env=stable_env, label="Stable-Visualreferenzen auf realem Desktop erzeugen")
        run([str(env_python), str(stable / "scripts/build_visual_inspection.py")], cwd=stable, env=stable_env, label="Stable-Visualmanifest erzeugen")
        run([str(env_python), str(stable / "scripts/live_desktop_gate.py")], cwd=stable, env=stable_env, label="Stable-Desktopfreigabe erzeugen")
        run([str(env_python), str(stable / "scripts/build_release_manifest.py")], cwd=stable, env=stable_env, label="Stable-Manifest erzeugen")
        run([str(stable / "test.sh")], cwd=stable, env=stable_env, label="Stable vollständig aus Arbeitskopie prüfen")
        run([str(stable / "stable_release.sh"), str(args.output.resolve())], cwd=stable, env=stable_env, label="Deterministisches Stable-ZIP erzeugen")

    final = args.output / "VideoBatch_Fast_2.8.3.zip"
    if not final.is_file():
        raise RuntimeError("Stable-ZIP wurde trotz grüner Schritte nicht erzeugt.")
    digest = hashlib.sha256(final.read_bytes()).hexdigest()
    report = {
        "schema_version": 1, "status": "passed", "stable_version": "2.8.3",
        "artifact": str(final), "sha256": digest,
        "gates": ["toolchain", "ruff", "mypy", "bandit", "pip-audit", "tests", "coverage", "visual", "live-desktop", "deterministic-package"],
    }
    report_path = args.output / "VideoBatch_Fast_2.8.3_FINAL_REPORT.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"\nFINALISIERUNG ABGESCHLOSSEN\nStable: {final}\nSHA-256: {digest}\nBericht: {report_path}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, subprocess.TimeoutExpired) as exc:
        print(f"FINALISIERUNG BLOCKIERT: {exc}", file=sys.stderr)
        raise SystemExit(1)
