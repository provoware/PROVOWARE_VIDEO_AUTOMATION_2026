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

from promote_stable_workspace import validate_promotion_source
from validate_operator_stable_acceptance import validate_operator_acceptance
from validate_stable_acceptance import manifest_sha256, validate_evidence

ROOT = Path(__file__).resolve().parents[1]


def tk_x11_env(env: dict[str, str]) -> dict[str, str]:
    """Return an isolated X11 environment for the legacy Tk GUI regression only."""
    isolated = {**env}
    isolated["XDG_SESSION_TYPE"] = "x11"
    isolated["WAYLAND_DISPLAY"] = ""
    return isolated


def run(command: list[str], *, cwd: Path, env: dict[str, str], label: str, timeout: int = 7200) -> None:
    print(f"\n▶ {label}", flush=True)
    completed = subprocess.run(command, cwd=cwd, env=env, text=True, check=False, timeout=timeout)
    if completed.returncode:
        raise RuntimeError(f"{label} fehlgeschlagen (Code {completed.returncode}).")
    print(f"✓ {label}", flush=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Finalisiert VideoBatch autonom bis zum Stable-ZIP.")
    parser.add_argument("--output", type=Path, default=ROOT / "dist")
    acceptance = parser.add_mutually_exclusive_group(required=True)
    acceptance.add_argument("--acceptance-evidence", type=Path)
    acceptance.add_argument("--operator-acceptance", action="store_true")
    parser.add_argument("--stable-workspace", type=Path)
    args = parser.parse_args()
    rc_version, stable_build = validate_promotion_source(ROOT)
    candidate = str(rc_version["build"])
    candidate_hash = manifest_sha256(ROOT / "RELEASE_MANIFEST.json")
    if args.operator_acceptance:
        validate_operator_acceptance(ROOT, candidate, candidate_hash)
    else:
        assert args.acceptance_evidence is not None
        validate_evidence(args.acceptance_evidence, candidate, candidate_hash)
    env_python = Path(sys.executable).resolve()
    if not env_python.is_file():
        raise RuntimeError("Die verifizierte Qualitätsumgebung ist nicht verfügbar.")
    if not os.environ.get("WAYLAND_DISPLAY"):
        raise RuntimeError(
            "Eine native Wayland-Sitzung auf Kubuntu 26.04 Plasma ist für die reale Abschlussprüfung erforderlich."
        )
    base_env = {
        **os.environ,
        "VIDEOBATCH_QUALITY_PYTHON": str(env_python),
        "VIDEOBATCH_TOOLCHAIN_PYTHON": str(env_python),
        "PYTHONPATH": str(ROOT / "src"),
        "PYTHONDONTWRITEBYTECODE": "1",
    }

    run([str(ROOT / "quality.sh")], cwd=ROOT, env=base_env, label="Externe Qualität und Kernprüfung")
    verified_env = {**base_env, "VIDEOBATCH_QUALITY_ALREADY_VERIFIED": "1"}
    run(
        ["bash", str(ROOT / "verify_release.sh")],
        cwd=ROOT,
        env=tk_x11_env(verified_env),
        label="Releasekandidat vollständig verifizieren",
    )
    run([str(env_python), str(ROOT / "scripts/live_desktop_gate.py")], cwd=ROOT, env=base_env, label="Reale Desktopprüfung des Releasekandidaten")

    args.output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="videobatch-stable-finalize-") as tmp:
        stable = (
            args.stable_workspace.resolve()
            if args.stable_workspace is not None
            else Path(tmp) / f"VideoBatch_Fast_{stable_build}"
        )
        if stable.exists():
            raise RuntimeError(f"Stable-Arbeitskopie existiert bereits: {stable}")
        run([
            str(env_python), str(ROOT / "scripts/promote_stable_workspace.py"),
            "--source", str(ROOT), "--destination", str(stable),
        ], cwd=ROOT, env=base_env, label="Getrennte Stable-Arbeitskopie erzeugen")
        run([
            str(env_python), str(stable / "diagnostics/release_readiness/generate_from_evidence.py"), "--write"
        ], cwd=stable, env={**base_env, "PYTHONPATH": str(stable / "src")}, label="Stable-Evidenz ableiten")
        run([
            str(env_python), str(stable / "scripts/render_release_docs.py"), "--write"
        ], cwd=stable, env={**base_env, "PYTHONPATH": str(stable / "src")}, label="Stable-Dokumentstatus ableiten")
        stable_env = {
            **base_env,
            "PYTHONPATH": str(stable / "src"),
            "VIDEOBATCH_QUALITY_ALREADY_VERIFIED": "1",
        }
        if args.operator_acceptance:
            stable_env.update({
                "VIDEOBATCH_OPERATOR_ACCEPTANCE": "1",
                "VIDEOBATCH_OPERATOR_ACCEPTANCE_ROOT": str(ROOT),
                "VIDEOBATCH_OPERATOR_ACCEPTANCE_CANDIDATE": candidate,
                "VIDEOBATCH_OPERATOR_ACCEPTANCE_MANIFEST_SHA256": candidate_hash,
            })
        else:
            assert args.acceptance_evidence is not None
            stable_env.update({
                "VIDEOBATCH_ACCEPTANCE_EVIDENCE": str(args.acceptance_evidence.resolve()),
                "VIDEOBATCH_ACCEPTANCE_CANDIDATE": candidate,
                "VIDEOBATCH_ACCEPTANCE_MANIFEST_SHA256": candidate_hash,
            })

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
        run(
            [str(stable / "test.sh")],
            cwd=stable,
            env=tk_x11_env(stable_env),
            label="Stable vollständig aus Arbeitskopie prüfen",
        )
        run([str(stable / "stable_release.sh"), str(args.output.resolve())], cwd=stable, env=stable_env, label="Deterministisches Stable-ZIP erzeugen")

    final = args.output / f"VideoBatch_Fast_{stable_build}.zip"
    if not final.is_file():
        raise RuntimeError("Stable-ZIP wurde trotz grüner Schritte nicht erzeugt.")
    digest = hashlib.sha256(final.read_bytes()).hexdigest()
    report = {
        "schema_version": 1, "status": "passed", "product_name": rc_version["name"],
        "stable_version": stable_build, "stable_build": stable_build, "stable_channel": "stable",
        "promoted_rc_candidate": rc_version["build"],
        "acceptance_mode": "explicit_operator_signoff" if args.operator_acceptance else "strict_physical_evidence",
        "artifact": str(final), "sha256": digest,
        "stable_workspace": str(args.stable_workspace.resolve()) if args.stable_workspace is not None else "",
        "gates": ["toolchain", "ruff", "mypy", "bandit", "pip-audit", "tests", "coverage", "visual", "live-desktop", "deterministic-package"],
    }
    report_path = args.output / f"VideoBatch_Fast_{stable_build}_FINAL_REPORT.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"\nFINALISIERUNG ABGESCHLOSSEN\nStable: {final}\nSHA-256: {digest}\nBericht: {report_path}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, subprocess.TimeoutExpired) as exc:
        print(f"FINALISIERUNG BLOCKIERT: {exc}", file=sys.stderr)
        raise SystemExit(1)
