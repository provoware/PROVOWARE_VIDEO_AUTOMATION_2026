#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
from typing import Any

MAX_AGE = timedelta(days=30)
KUBUNTU_EVIDENCE = Path("diagnostics/release_readiness/KUBUNTU_OPERATOR_ACCEPTANCE_2026-09-29.json")
LONG_RENDER_EVIDENCE = Path("diagnostics/release_readiness/LONG_RENDER_OPERATOR_ACCEPTANCE_2026-09-29.json")
CANONICAL_EVIDENCE = Path("diagnostics/release_readiness/RELEASE_EVIDENCE.json")


class OperatorAcceptanceBlocked(RuntimeError):
    pass


def _blocked(message: str) -> OperatorAcceptanceBlocked:
    return OperatorAcceptanceBlocked(
        f"Operator-Stable-Freigabe blockiert: {message} "
        "Es werden weder Messwerte rekonstruiert noch fehlende technische Nachweise erfunden."
    )


def _load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise _blocked(f"{path} ist nicht lesbares JSON ({exc}).") from exc
    if not isinstance(value, dict):
        raise _blocked(f"{path} muss ein JSON-Objekt sein.")
    return value


def manifest_sha256(path: Path) -> str:
    if not path.is_file():
        raise _blocked(f"Release-Manifest fehlt: {path}.")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _accepted_at(value: object, label: str, now: datetime) -> str:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            raise ValueError("Zeitzone fehlt")
        stamp = parsed.astimezone(timezone.utc)
    except ValueError as exc:
        raise _blocked(f"{label} hat keinen gültigen ISO-8601-Zeitpunkt mit Zeitzone.") from exc
    if stamp > now + timedelta(minutes=5) or now - stamp > MAX_AGE:
        raise _blocked(f"{label} ist älter als 30 Tage oder liegt in der Zukunft.")
    return stamp.isoformat()


def _operator_file(
    root: Path,
    relative: Path,
    *,
    evidence_type: str,
    gate_id: str,
    candidate: str,
    now: datetime,
) -> dict[str, Any]:
    path = root / relative
    data = _load(path)
    if data.get("schema_version") != 1:
        raise _blocked(f"{relative} verwendet nicht Schema 1.")
    if data.get("evidence_type") != evidence_type or data.get("gate_id") != gate_id:
        raise _blocked(f"{relative} gehört nicht zum erwarteten Stable-Gate {gate_id}.")
    if data.get("candidate_id") != candidate or data.get("result") != "passed":
        raise _blocked(f"{relative} ist nicht als bestanden an Kandidat {candidate} gebunden.")
    if not str(data.get("statement") or "").strip() or not str(data.get("provenance") or "").strip():
        raise _blocked(f"{relative} enthält keine nachvollziehbare Freigabe-Provenienz.")
    accepted = _accepted_at(data.get("accepted_at"), relative.name, now)
    return {
        "path": relative.as_posix(),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "accepted_at": accepted,
        "gate_id": gate_id,
    }


def validate_operator_acceptance(
    source_root: Path,
    candidate: str,
    digest: str,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    root = Path(source_root).resolve(strict=True)
    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)

    version = _load(root / "VERSION.json")
    if version.get("channel") != "rc" or version.get("build") != candidate:
        raise _blocked("VERSION.json bezeichnet nicht den freigegebenen RC-Kandidaten.")

    actual_digest = manifest_sha256(root / "RELEASE_MANIFEST.json")
    if actual_digest != digest:
        raise _blocked("RELEASE_MANIFEST.json hat sich seit der Freigabebindung geändert.")

    canonical = _load(root / CANONICAL_EVIDENCE)
    product = canonical.get("product")
    gates = canonical.get("stable_gates")
    if not isinstance(product, dict) or product.get("version") != candidate:
        raise _blocked("Kanonische RELEASE_EVIDENCE gehört nicht zum RC-Kandidaten.")
    if canonical.get("stable_ready") is not True or not isinstance(gates, list):
        raise _blocked("Kanonische RELEASE_EVIDENCE ist nicht stable_ready.")
    gate_status = {
        str(item.get("id")): str(item.get("status"))
        for item in gates
        if isinstance(item, dict)
    }
    open_gates = sorted(gate for gate, status in gate_status.items() if status != "passed")
    for required in ("physical_kubuntu_26_04_wayland", "large_media_soak"):
        if gate_status.get(required) != "passed":
            open_gates.append(required)
    if open_gates:
        raise _blocked("Nicht alle kanonischen Stable-Gates sind bestanden: " + ", ".join(sorted(set(open_gates))))

    development = _load(root / "DEVELOPMENT_STATUS.json")
    if development.get("version") != candidate or development.get("stable_ready") is not True:
        raise _blocked("DEVELOPMENT_STATUS ist nicht vollständig stable_ready.")
    if list(development.get("stable_blockers") or []):
        raise _blocked("DEVELOPMENT_STATUS enthält noch Stable-Blocker.")

    report_name = development.get("approved_quality_report")
    if not isinstance(report_name, str) or Path(report_name).name != report_name:
        raise _blocked("Freigegebener Qualitätsbericht ist nicht eindeutig benannt.")
    report = _load(root / report_name)
    if (
        report.get("version") != candidate
        or report.get("status") != "passed"
        or report.get("stable_ready") is not True
        or list(report.get("stable_blockers") or [])
    ):
        raise _blocked("Freigegebener Qualitätsbericht ist nicht vollständig bestanden.")

    kubuntu = _operator_file(
        root,
        KUBUNTU_EVIDENCE,
        evidence_type="operator_baseline_acceptance",
        gate_id="physical_kubuntu_26_04_wayland",
        candidate=candidate,
        now=current,
    )
    long_render = _operator_file(
        root,
        LONG_RENDER_EVIDENCE,
        evidence_type="operator_long_render_acceptance",
        gate_id="large_media_soak",
        candidate=candidate,
        now=current,
    )

    kubuntu_data = _load(root / KUBUNTU_EVIDENCE)
    long_data = _load(root / LONG_RENDER_EVIDENCE)
    if kubuntu_data.get("physical_test_reexecuted") is not False or kubuntu_data.get("formal_kubuntu_26_04_json_claimed") is not False:
        raise _blocked("Kubuntu-Operatornachweis muss transparent festhalten, dass kein neuer Messlauf erfunden wurde.")
    if long_data.get("measurements_reconstructed") is not False or long_data.get("formal_long_render_json_claimed") is not False:
        raise _blocked("Langzeitrender-Operatornachweis muss transparent festhalten, dass keine Messwerte rekonstruiert wurden.")

    return {
        "schema_version": 1,
        "status": "passed",
        "acceptance_mode": "explicit_operator_signoff",
        "candidate": candidate,
        "manifest_sha256": digest,
        "operator_evidence": [kubuntu, long_render],
        "canonical_stable_ready": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Prüft die ausdrücklich dokumentierte Operator-Stable-Freigabe.")
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--manifest-sha256", required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        result = validate_operator_acceptance(args.source_root, args.candidate, args.manifest_sha256)
    except OperatorAcceptanceBlocked as exc:
        if args.json:
            print(json.dumps({"schema_version": 1, "status": "failed", "error": str(exc)}, ensure_ascii=False, indent=2))
        else:
            print(str(exc))
        return 14
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"OPERATOR-STABLE-FREIGABE BESTANDEN · {args.candidate}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
