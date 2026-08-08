#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile
from typing import Any

try:
    import quality_evidence
    from release_identity import ROOT, release_identity, sha256_file
    from stable_operator_common import (
        OperatorBlocked,
        completed_phases,
        init_session,
        load_contract,
        load_session,
        record_phase,
        require_previous,
        sha256_canonical,
    )
    from toolchain_common import load_contract as load_toolchain_contract, verify_wheelhouse
    from validate_stable_acceptance import validate_evidence
except ModuleNotFoundError:
    from scripts import quality_evidence
    from scripts.release_identity import ROOT, release_identity, sha256_file
    from scripts.stable_operator_common import (
        OperatorBlocked,
        completed_phases,
        init_session,
        load_contract,
        load_session,
        record_phase,
        require_previous,
        sha256_canonical,
    )
    from scripts.toolchain_common import load_contract as load_toolchain_contract, verify_wheelhouse
    from scripts.validate_stable_acceptance import validate_evidence


def _run(command: list[str], *, env: dict[str, str] | None = None, cwd: Path = ROOT, timeout: int = 24 * 3600) -> None:
    print("▶", " ".join(command), flush=True)
    completed = subprocess.run(command, cwd=cwd, env=env, check=False, timeout=timeout)
    if completed.returncode:
        raise OperatorBlocked(f"Kommando fehlgeschlagen ({completed.returncode}): {' '.join(command)}")


def _session_dir(value: Path) -> Path:
    result = value.expanduser().resolve(strict=False)
    result.mkdir(parents=True, exist_ok=True)
    return result


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    path.write_text(text, encoding="utf-8")


def _quality_versions(python: Path) -> dict[str, str]:
    code = (
        "import importlib.metadata as m,json; "
        "names=['ruff','mypy','bandit','pip-audit']; "
        "print(json.dumps({n:m.version(n) for n in names},sort_keys=True))"
    )
    completed = subprocess.run([str(python), "-c", code], text=True, capture_output=True, check=False)
    if completed.returncode:
        raise OperatorBlocked(f"Installierte Toolversionen konnten nicht gelesen werden: {completed.stderr.strip()}")
    value = json.loads(completed.stdout)
    if not isinstance(value, dict):
        raise OperatorBlocked("Installierte Toolversionen sind kein JSON-Objekt.")
    return {str(key): str(item) for key, item in value.items()}


def _directory_digest(directory: Path) -> tuple[str, int]:
    entries: list[dict[str, object]] = []
    for path in sorted(directory.rglob("*")):
        if path.is_file() and not path.is_symlink():
            entries.append({
                "path": path.relative_to(directory).as_posix(),
                "size": path.stat().st_size,
                "sha256": sha256_file(path),
            })
    if not entries:
        raise OperatorBlocked(f"Verzeichnis enthält keine einfrierbaren Dateien: {directory}")
    return sha256_canonical(entries), len(entries)


def phase_toolchain(session_dir: Path) -> None:
    init_session(session_dir)
    session = load_session(session_dir)
    contract = load_contract()
    require_previous(session, "toolchain", contract)
    env = {**os.environ, "VIDEOBATCH_ALLOW_PUBLIC_PYPI": "1", "PYTHONDONTWRITEBYTECODE": "1"}
    _run([sys.executable, str(ROOT / "scripts/build_toolchain_wheelhouse.py"), "--scope", "all"], env=env)
    toolchain = load_toolchain_contract()
    wheelhouse = ROOT / str(toolchain["paths"]["wheelhouse"])
    errors = verify_wheelhouse(wheelhouse, toolchain, scope="all")
    if errors:
        raise OperatorBlocked("Wheelhouse-Verifikation fehlgeschlagen: " + " | ".join(errors))
    manifest = wheelhouse / "TOOLCHAIN_WHEELHOUSE_MANIFEST.json"
    # pip-audit benötigt aktuelle Advisory-Daten. Diese werden nach dem eingefrorenen
    # Wheelhouse einmal online in einen dedizierten HTTP-Cache geladen; der eigentliche
    # Quality-Gate-Lauf erfolgt anschließend mit Netzwerksperre ausschließlich gegen
    # diesen Cache.
    cache_dir = session_dir / "toolchain" / "pip-audit-cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    prep_env = {**env, "VIDEOBATCH_PIP_AUDIT_CACHE": str(cache_dir)}
    _run([sys.executable, str(ROOT / "scripts/toolchain.py"), "prepare", "--scope", "quality", "--offline-only", "--replace", "--quiet"], env=prep_env)
    completed = subprocess.run(
        [sys.executable, str(ROOT / "scripts/toolchain.py"), "path", "--scope", "quality", "--quiet"],
        cwd=ROOT, env=prep_env, text=True, capture_output=True, check=False,
    )
    if completed.returncode:
        raise OperatorBlocked("Qualitäts-Python für Advisory-Cache konnte nicht bestimmt werden.")
    quality_python = Path(completed.stdout.strip()).resolve(strict=True)
    warm = subprocess.run(
        [str(quality_python), "-m", "pip_audit", "--cache-dir", str(cache_dir), "--no-deps", "--disable-pip",
         "--progress-spinner", "off", "-r", str(ROOT / "requirements.lock")],
        cwd=ROOT, env=prep_env, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False,
    )
    cache_log = session_dir / "toolchain" / "pip-audit-cache-warm.log"
    cache_log.write_text(warm.stdout or "(keine Ausgabe)\n", encoding="utf-8", errors="replace")
    cache_sha256, cache_files = _directory_digest(cache_dir)
    evidence = session_dir / "toolchain" / "toolchain-freeze.json"
    payload = {
        "schema_version": 1,
        "candidate_identity": release_identity(),
        "wheelhouse_manifest_sha256": sha256_file(manifest),
        "toolchain_contract_sha256": sha256_file(ROOT / "TOOLCHAIN_CONTRACT.json"),
        "requirements_toolchain_sha256": sha256_file(ROOT / "requirements-toolchain.lock"),
        "pip_audit_advisory_cache": {
            "sha256": cache_sha256,
            "file_count": cache_files,
            "warm_returncode": warm.returncode,
            "log_sha256": sha256_file(cache_log),
        },
        "platform": platform.platform(),
        "python": sys.version,
        "status": "passed",
    }
    _write_json(evidence, payload)
    record_phase(
        session_dir, "toolchain", [manifest, evidence, cache_log],
        details={"wheelhouse": str(wheelhouse), "pip_audit_cache": str(cache_dir)},
    )
    print(f"✓ TOOLCHAIN EINGEFROREN · {manifest}")


def phase_quality(session_dir: Path) -> None:
    session = load_session(session_dir)
    contract = load_contract()
    require_previous(session, "quality", contract)
    quality_dir = session_dir / "quality"
    diagnostics = quality_dir / "diagnostics"
    diagnostics.mkdir(parents=True, exist_ok=True)
    env = {
        **os.environ,
        "VIDEOBATCH_DIAGNOSTICS_DIR": str(diagnostics),
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONPATH": str(ROOT / "src"),
        "VIDEOBATCH_PIP_AUDIT_CACHE": str(session_dir / "toolchain" / "pip-audit-cache"),
    }
    _run([sys.executable, str(ROOT / "scripts/toolchain.py"), "prepare", "--scope", "quality", "--offline-only", "--replace", "--quiet"], env=env)
    _run([sys.executable, str(ROOT / "scripts/toolchain.py"), "gate", "--scope", "quality", "--run-external", "--quiet"], env=env)
    completed = subprocess.run(
        [sys.executable, str(ROOT / "scripts/toolchain.py"), "path", "--scope", "quality", "--quiet"],
        cwd=ROOT, env=env, text=True, capture_output=True, check=False,
    )
    if completed.returncode:
        raise OperatorBlocked("Qualitäts-Python konnte nicht bestimmt werden.")
    env_python = Path(completed.stdout.strip()).resolve(strict=True)
    versions = _quality_versions(env_python)
    expected = {str(k): str(v) for k, v in contract["quality_tools"].items()}
    if versions != expected:
        raise OperatorBlocked(f"Toolversionen weichen vom Operator-Vertrag ab: {versions}")
    _write_json(quality_dir / "installed-versions.json", {"python": sys.version, "packages": versions})
    shutil.copy2(ROOT / "toolchain_wheelhouse/TOOLCHAIN_WHEELHOUSE_MANIFEST.json", quality_dir / "wheelhouse-manifest.json")
    shutil.copy2(ROOT / "toolchain_wheelhouse/requirements-toolchain-resolved.lock", quality_dir / "requirements-toolchain-resolved.lock")
    quality_evidence.write_index(quality_dir, quality_evidence.build_index(quality_dir))
    quality_evidence.verify_index(quality_dir)
    base_env = {**env, "VIDEOBATCH_QUALITY_ALREADY_VERIFIED": "1", "VIDEOBATCH_QUALITY_PYTHON": str(env_python)}
    _run([str(ROOT / "test.sh")], env=base_env, timeout=4 * 3600)
    bundle = session_dir / "quality-evidence.zip"
    quality_evidence.build_zip(quality_dir, bundle)
    record_phase(session_dir, "quality", [quality_dir / quality_evidence.INDEX_NAME, bundle])
    print(f"✓ EXTERNE QUALITÄT + REGRESSION BESTANDEN · {bundle}")


def phase_desktop(session_dir: Path, expected_session: str) -> None:
    phase = f"desktop_{expected_session}"
    session = load_session(session_dir)
    contract = load_contract()
    require_previous(session, phase, contract)
    actual = os.environ.get("XDG_SESSION_TYPE", "").strip().lower()
    if actual != expected_session:
        raise OperatorBlocked(f"Für {phase} ist eine echte {expected_session.upper()}-Sitzung erforderlich; erkannt: {actual or 'keine'}")
    desktop = os.environ.get("XDG_CURRENT_DESKTOP", "")
    if "kde" not in desktop.lower() and "plasma" not in desktop.lower():
        raise OperatorBlocked(f"Für {phase} ist KDE/Plasma erforderlich; erkannt: {desktop or 'unbekannt'}")
    evidence_dir = session_dir / "acceptance"
    env = {**os.environ, "VIDEOBATCH_PHYSICAL_ACCEPTANCE": "1", "PYTHONPATH": f"{ROOT / 'src'}:{ROOT / 'scripts'}"}
    _run([sys.executable, str(ROOT / "scripts/live_desktop_gate.py"), "--evidence-dir", str(evidence_dir)], env=env)
    evidence = evidence_dir / f"kde_{expected_session}.json"
    raw_dir = session_dir / phase
    raw_dir.mkdir(parents=True, exist_ok=True)
    raw_report = raw_dir / "AUTOMATED_DESKTOP_APPROVAL.json"
    raw_screenshot = raw_dir / "live_desktop_approval.png"
    shutil.copy2(ROOT / "AUTOMATED_DESKTOP_APPROVAL.json", raw_report)
    shutil.copy2(ROOT / "visual_inspection/live_desktop_approval.png", raw_screenshot)
    record_phase(session_dir, phase, [evidence, raw_report, raw_screenshot])
    print(f"✓ PHYSISCHE KDE-{expected_session.upper()}-EVIDENCE · {evidence}")


def phase_long_render(session_dir: Path, contract_path: Path, resume: bool) -> None:
    session = load_session(session_dir)
    contract = load_contract()
    require_previous(session, "long_render", contract)
    evidence_dir = session_dir / "acceptance"
    command = [
        sys.executable,
        str(ROOT / "scripts/run_long_render_acceptance.py"),
        "--contract", str(contract_path.resolve(strict=True)),
        "--evidence-dir", str(evidence_dir),
    ]
    if resume:
        command.append("--resume")
    env = {**os.environ, "PYTHONPATH": f"{ROOT / 'src'}:{ROOT / 'scripts'}"}
    _run(command, env=env, timeout=24 * 3600)
    evidence = evidence_dir / "long_render.json"
    from videobatch_fast.long_render_contract import load_contract as load_long_render_contract
    loaded = load_long_render_contract(contract_path.resolve(strict=True))
    final_report = loaded.state_file.parent / "final-report.json"
    if not final_report.is_file():
        raise OperatorBlocked("Langzeitrender meldet Erfolg, aber final-report.json fehlt.")
    record_phase(
        session_dir, "long_render", [evidence, contract_path.resolve(strict=True), final_report],
        details={"contract": str(contract_path.resolve()), "final_report": str(final_report)},
    )
    print(f"✓ 96-JOB-SLOW-TARGET-EVIDENCE · {evidence}")


def _patch_rehearsal_status(staging: Path) -> None:
    status_path = staging / "DEVELOPMENT_STATUS.json"
    status = json.loads(status_path.read_text(encoding="utf-8"))
    report_name = str(status.get("approved_quality_report", ""))
    if not report_name or Path(report_name).name != report_name:
        raise OperatorBlocked("Approved-Quality-Report ist nicht eindeutig benannt.")
    report_path = staging / report_name
    report = json.loads(report_path.read_text(encoding="utf-8"))
    status.update({"stable_ready": True, "stable_blockers": [], "status": "green", "open": 0})
    report.update({"stable_ready": True, "stable_blockers": [], "status": "passed"})
    _write_json(status_path, status)
    _write_json(report_path, report)


def _promotion_rehearsal(session_dir: Path, output: Path) -> Path:
    session = load_session(session_dir)
    contract = load_contract()
    require_previous(session, "promotion_rehearsal", contract)
    quality_dir = session_dir / "quality"
    acceptance = session_dir / "acceptance"
    quality_index = quality_evidence.verify_index(quality_dir)
    identity = release_identity()
    validate_evidence(
        acceptance,
        str(identity["candidate_id"]),
        str(identity["manifest_sha256"]),
        str(identity["source_sha256"]),
    )
    with tempfile.TemporaryDirectory(prefix="videobatch-w18-rehearsal-") as tmp_raw:
        tmp = Path(tmp_raw)
        source = tmp / "candidate"
        stable = tmp / "stable"
        shutil.copytree(ROOT, source, symlinks=False, ignore=shutil.ignore_patterns(".git", ".pytest_cache", ".ruff_cache", ".mypy_cache", "__pycache__", "dist"))
        _patch_rehearsal_status(source)
        _run([sys.executable, str(ROOT / "scripts/promote_stable_workspace.py"), "--source", str(source), "--destination", str(stable)])
        env = {**os.environ, "PYTHONPATH": f"{stable / 'src'}:{stable / 'scripts'}", "PYTHONDONTWRITEBYTECODE": "1"}
        _run([sys.executable, str(stable / "scripts/build_release_manifest.py")], cwd=stable, env=env)
        first, second = tmp / "stable-a.zip", tmp / "stable-b.zip"
        _run([sys.executable, str(stable / "scripts/package_release.py"), "--output", str(first)], cwd=stable, env=env)
        _run([sys.executable, str(stable / "scripts/package_release.py"), "--output", str(second)], cwd=stable, env=env)
        if first.read_bytes() != second.read_bytes():
            raise OperatorBlocked("Promotion-Rehearsal ist nicht byte-reproduzierbar.")
        report = {
            "schema_version": 1,
            "status": "passed",
            "candidate_identity": identity,
            "operator_session_sha256": sha256_file(session_dir / "OPERATOR_SESSION.json"),
            "quality_evidence_index_sha256": sha256_canonical(quality_index),
            "acceptance_evidence": {
                name: sha256_file(acceptance / name)
                for name in ("kde_x11.json", "long_render.json")
            },
            "stable_package_sha256": hashlib.sha256(first.read_bytes()).hexdigest(),
            "stable_package_size": first.stat().st_size,
            "byte_reproducible": True,
            "note": "Rehearsal only: kein Stable-Artefakt wurde veröffentlicht.",
        }
    _write_json(output, report)
    return output


def phase_rehearsal(session_dir: Path, output: Path) -> None:
    report = _promotion_rehearsal(session_dir, output)
    record_phase(session_dir, "promotion_rehearsal", [report])
    print(f"✓ STABLE-PROMOTION-REHEARSAL BESTANDEN · {report}")


def show_status(session_dir: Path) -> None:
    session = init_session(session_dir)
    contract = load_contract()
    done = completed_phases(session)
    print(json.dumps({
        "candidate_identity": session["candidate_identity"],
        "completed": done,
        "remaining": [phase for phase in contract["phases"] if phase not in done],
        "session": str(session_dir / "OPERATOR_SESSION.json"),
    }, ensure_ascii=False, indent=2, sort_keys=True))


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="Welle-18 Operator für reale Stable-Gates und Promotion-Rehearsal.")
    result.add_argument("--session-dir", type=Path, required=True)
    sub = result.add_subparsers(dest="action", required=True)
    sub.add_parser("status")
    sub.add_parser("toolchain")
    sub.add_parser("quality")
    desktop = sub.add_parser("desktop")
    desktop.add_argument("--session", choices=("x11",), required=True)
    soak = sub.add_parser("long-render")
    soak.add_argument("--contract", type=Path, required=True)
    soak.add_argument("--resume", action="store_true")
    rehearsal = sub.add_parser("promotion-rehearsal")
    rehearsal.add_argument("--output", type=Path)
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    session_dir = _session_dir(args.session_dir)
    init_session(session_dir)
    if args.action == "status":
        show_status(session_dir)
    elif args.action == "toolchain":
        phase_toolchain(session_dir)
    elif args.action == "quality":
        phase_quality(session_dir)
    elif args.action == "desktop":
        phase_desktop(session_dir, args.session)
    elif args.action == "long-render":
        phase_long_render(session_dir, args.contract, bool(args.resume))
    else:
        output = args.output or session_dir / "PROMOTION_REHEARSAL.json"
        phase_rehearsal(session_dir, output.resolve(strict=False))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OperatorBlocked, OSError, ValueError, json.JSONDecodeError, subprocess.TimeoutExpired) as exc:
        print(f"OPERATOR BLOCKIERT: {exc}", file=sys.stderr)
        raise SystemExit(18)
