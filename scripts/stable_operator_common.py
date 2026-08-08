#!/usr/bin/env python3
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import tempfile
from typing import Any

try:
    from release_identity import ROOT, release_identity, sha256_file
except ModuleNotFoundError:
    from scripts.release_identity import ROOT, release_identity, sha256_file

CONTRACT = ROOT / "STABLE_OPERATOR_CONTRACT.json"
SESSION_NAME = "OPERATOR_SESSION.json"


class OperatorBlocked(RuntimeError):
    pass


def load_contract(root: Path = ROOT) -> dict[str, Any]:
    try:
        data = json.loads((root / CONTRACT.name).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise OperatorBlocked(f"Operator-Vertrag ist unlesbar: {exc}") from exc
    if not isinstance(data, dict) or data.get("schema_version") != 1:
        raise OperatorBlocked("Operator-Vertrag besitzt kein unterstütztes Schema.")
    phases = data.get("phases")
    if not isinstance(phases, list) or len(phases) != len(set(map(str, phases))):
        raise OperatorBlocked("Operator-Phasen fehlen oder sind doppelt.")
    return data


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, raw = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    tmp = Path(raw)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


def init_session(directory: Path, *, root: Path = ROOT) -> dict[str, Any]:
    directory = directory.resolve(strict=False)
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / SESSION_NAME
    identity = release_identity(root)
    if target.exists():
        return load_session(directory, root=root)
    payload = {
        "schema_version": 1,
        "candidate_identity": identity,
        "created_at": utc_now(),
        "updated_at": utc_now(),
        "phases": [],
    }
    _atomic_json(target, payload)
    return payload


def load_session(directory: Path, *, root: Path = ROOT) -> dict[str, Any]:
    path = directory.resolve(strict=False) / SESSION_NAME
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise OperatorBlocked(f"Operator-Sitzung ist unlesbar: {exc}") from exc
    if not isinstance(data, dict) or data.get("schema_version") != 1:
        raise OperatorBlocked("Operator-Sitzung besitzt kein unterstütztes Schema.")
    if data.get("candidate_identity") != release_identity(root):
        raise OperatorBlocked("Operator-Sitzung ist stale oder gehört zu einem anderen Source-/Manifest-Stand.")
    records = data.get("phases")
    if not isinstance(records, list):
        raise OperatorBlocked("Operator-Sitzung enthält keine gültige Phasenliste.")
    contract = load_contract(root)
    phase_order = [str(item) for item in contract["phases"]]
    seen: list[str] = []
    for record in records:
        if not isinstance(record, dict) or record.get("status") != "passed":
            raise OperatorBlocked("Operator-Sitzung enthält einen ungültigen Phaseneintrag.")
        phase = str(record.get("phase", ""))
        if phase not in phase_order or phase in seen:
            raise OperatorBlocked(f"Operator-Sitzung enthält eine unbekannte oder doppelte Phase: {phase!r}")
        seen.append(phase)
        artifacts = record.get("artifacts")
        if not isinstance(artifacts, list) or not artifacts:
            raise OperatorBlocked(f"Operator-Phase {phase} besitzt keine gebundenen Artefakte.")
        for raw in artifacts:
            if not isinstance(raw, dict):
                raise OperatorBlocked(f"Operator-Phase {phase} besitzt einen ungültigen Artefakteintrag.")
            path = Path(str(raw.get("path", "")))
            if not path.is_file() or path.is_symlink():
                raise OperatorBlocked(f"Operator-Evidence fehlt oder ist Link: {path}")
            if path.stat().st_size != int(raw.get("size", -1)) or sha256_file(path) != str(raw.get("sha256", "")):
                raise OperatorBlocked(f"Operator-Evidence wurde nachträglich verändert: {path}")
    indices = [phase_order.index(item) for item in seen]
    if indices != sorted(indices):
        raise OperatorBlocked("Operator-Phasen wurden außerhalb der vorgeschriebenen Reihenfolge aufgezeichnet.")
    return data


def completed_phases(session: dict[str, Any]) -> list[str]:
    return [
        str(item.get("phase"))
        for item in session.get("phases", [])
        if isinstance(item, dict) and item.get("status") == "passed"
    ]


def require_previous(session: dict[str, Any], phase: str, contract: dict[str, Any]) -> None:
    phases = [str(item) for item in contract["phases"]]
    if phase not in phases:
        raise OperatorBlocked(f"Unbekannte Operator-Phase: {phase}")
    index = phases.index(phase)
    required = phases[:index]
    done = completed_phases(session)
    missing = [item for item in required if item not in done]
    if missing:
        raise OperatorBlocked(f"Phase {phase} blockiert; vorher fehlen: {', '.join(missing)}")


def record_phase(
    directory: Path,
    phase: str,
    artifacts: list[Path] | None = None,
    *,
    root: Path = ROOT,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    session = load_session(directory, root=root)
    contract = load_contract(root)
    require_previous(session, phase, contract)
    artifact_records = []
    for path in artifacts or []:
        resolved = path.resolve(strict=True)
        if not resolved.is_file() or resolved.is_symlink():
            raise OperatorBlocked(f"Evidence-Artefakt ist keine reguläre Datei: {resolved}")
        artifact_records.append({
            "path": str(resolved),
            "size": resolved.stat().st_size,
            "sha256": sha256_file(resolved),
        })
    records = [item for item in session["phases"] if not (isinstance(item, dict) and item.get("phase") == phase)]
    records.append({
        "phase": phase,
        "status": "passed",
        "completed_at": utc_now(),
        "artifacts": artifact_records,
        "details": details or {},
    })
    session["phases"] = records
    session["updated_at"] = utc_now()
    _atomic_json(directory.resolve(strict=False) / SESSION_NAME, session)
    return session


def sha256_canonical(value: Any) -> str:
    data = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(data).hexdigest()
