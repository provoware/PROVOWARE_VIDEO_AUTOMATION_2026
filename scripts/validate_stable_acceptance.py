#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import sys

try:
    from release_identity import release_identity
except ModuleNotFoundError:  # Import als scripts.validate_stable_acceptance
    from scripts.release_identity import release_identity

SCHEMA_VERSION = 2
MAX_AGE = timedelta(days=30)
REQUIRED_CHECKS = {
    "kde_x11": {"physical_session", "application_started", "preview_rendered", "window_scaling_checked"},
    "long_render": {"large_media_selection", "slow_external_target", "render_completed", "output_hash_verified"},
}


class AcceptanceBlocked(RuntimeError):
    pass


def _blocked(cause: str, solution: str, alternative: str) -> AcceptanceBlocked:
    return AcceptanceBlocked(
        f"Ursache: {cause} Auswirkung: Das Stable-Paket wird nicht erzeugt. "
        "Automatische Schutzmaßnahme: Die Freigabe stoppt, ohne Nachweise zu ändern oder zu erzeugen. "
        f"Lösung: {solution} Alternative: {alternative}"
    )


def manifest_sha256(path: Path) -> str:
    if not path.is_file():
        raise _blocked("Das Release-Manifest fehlt.", "Release-Manifest für den unveränderten Kandidaten erzeugen.", "Den Kandidaten erneut bauen und danach abnehmen.")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load(path: Path) -> dict[str, object]:
    if not path.is_file():
        raise _blocked(f"Der Nachweis {path.name} fehlt.", f"Die reale Prüfung durchführen und {path.name} im Nachweisformat ablegen.", "Den Kandidaten als Release Candidate belassen.")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise _blocked(f"Der Nachweis {path.name} ist nicht lesbares JSON ({exc}).", "Den Nachweis als gültiges UTF-8-JSON neu exportieren.", "Den Kandidaten als Release Candidate belassen.") from exc
    if not isinstance(value, dict):
        raise _blocked(f"Der Nachweis {path.name} ist kein JSON-Objekt.", "Ein Objekt gemäß Nachweisformat ablegen.", "Den Kandidaten als Release Candidate belassen.")
    return value


def _timestamp(value: object, name: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            raise ValueError("Zeitzone fehlt")
        return parsed.astimezone(timezone.utc)
    except ValueError as exc:
        raise _blocked(f"Der Zeitpunkt in {name} ist ungültig.", "Einen ISO-8601-Zeitpunkt mit Zeitzone eintragen.", "Die Abnahme wiederholen.") from exc


def _validate_one(data: dict[str, object], kind: str, candidate: str, digest: str, source_digest: str, now: datetime) -> None:
    name = f"{kind}.json"
    if data.get("schema_version") != SCHEMA_VERSION or data.get("evidence_type") != kind:
        raise _blocked(f"{name} verwendet ein falsches Format oder eine falsche Nachweisart.", f"{name} im Nachweisformat Version {SCHEMA_VERSION} exportieren.", "Die Abnahme wiederholen.")
    if data.get("candidate_id") != candidate or data.get("manifest_sha256") != digest or data.get("source_sha256") != source_digest:
        raise _blocked(f"{name} gehört nicht zum unveränderten Kandidaten, Manifest- oder Source-Hash.", "Die Abnahme für genau diesen Kandidaten sowie dessen Manifest- und Source-Hash durchführen.", "Den belegten Kandidaten separat veröffentlichen.")
    if data.get("result") != "passed":
        raise _blocked(f"{name} enthält kein bestandenes Ergebnis.", "Die fehlgeschlagene Prüfung beheben und real wiederholen.", "Den Kandidaten als Release Candidate belassen.")
    environment = data.get("environment")
    if not isinstance(environment, dict) or not environment:
        raise _blocked(f"{name} beschreibt die Prüfumgebung nicht.", "Die reale Umgebung als nicht leeres Objekt dokumentieren.", "Die Abnahme wiederholen.")
    stamp = _timestamp(data.get("timestamp"), name)
    if stamp > now + timedelta(minutes=5) or now - stamp > MAX_AGE:
        raise _blocked(f"{name} ist veraltet oder liegt unzulässig in der Zukunft.", "Die Abnahme jetzt am unveränderten Kandidaten wiederholen.", "Den Kandidaten als Release Candidate belassen.")
    checks = data.get("checks")
    passed = {key for key, value in checks.items() if value is True} if isinstance(checks, dict) else set()
    missing = sorted(REQUIRED_CHECKS[kind] - passed)
    if missing:
        raise _blocked(f"{name} hat fehlende oder fehlgeschlagene Prüfpunkte: {', '.join(missing)}.", "Alle Pflichtprüfpunkte real bestehen und dokumentieren.", "Den Kandidaten als Release Candidate belassen.")


def validate_evidence(directory: Path, candidate: str, digest: str, source_digest: str, *, now: datetime | None = None) -> None:
    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    for kind in REQUIRED_CHECKS:
        _validate_one(_load(directory / f"{kind}.json"), kind, candidate, digest, source_digest, current)


def main() -> int:
    parser = argparse.ArgumentParser(description="Prüft externe Stable-Abnahmen strikt lesend und sourcegebunden.")
    parser.add_argument("--evidence-dir", type=Path, required=True)
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--manifest-sha256", required=True)
    parser.add_argument("--source-sha256", default="")
    args = parser.parse_args()
    source_digest = args.source_sha256 or str(release_identity()["source_sha256"])
    validate_evidence(args.evidence_dir, args.candidate, args.manifest_sha256, source_digest)
    print("STABLE-ABNAHMEN GÜLTIG: KDE X11 und Langzeitrender · Source/Manifest gebunden.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AcceptanceBlocked as exc:
        print(f"STABLE BLOCKIERT: {exc}", file=sys.stderr)
        raise SystemExit(14)
