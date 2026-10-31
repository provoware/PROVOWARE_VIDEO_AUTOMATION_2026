"""Validate persisted archive journals without trusting them to authorize deletion."""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Callable

from .safe_io import atomic_write_json

_TERMINAL = {"committed", "rolled_back", "source_retained", "failed_safe"}
_STATES = _TERMINAL | {"prepared", "copying", "copied", "verified_temp", "published", "verified_target", "source_removed", "failed"}
_FOLDERS = {"audio": "Audio", "image": "Bilder", "video": "Videos"}


def _managed_path(value: Any, parent: Path) -> Path:
    if not isinstance(value, str) or not value:
        raise ValueError("Pfad fehlt")
    path = Path(value)
    if not path.is_absolute() or path.parent != parent or path.is_symlink():
        raise ValueError("Pfad liegt nicht im erwarteten Archivbereich")
    if path.resolve().parent != parent.resolve():
        raise ValueError("Archivpfad enthält eine Umleitung")
    return path


def _validate(payload: Any, journal: Path, project: Path) -> dict[str, Any]:
    if not isinstance(payload, dict) or payload.get("schema_version") != 2:
        raise ValueError("Unbekanntes Journalschema")
    if payload.get("transaction_id") != journal.stem or payload.get("state") not in _STATES:
        raise ValueError("Transaktionskennung oder Zustand ungültig")
    source = payload.get("source")
    if not isinstance(source, str) or not Path(source).is_absolute():
        raise ValueError("Quellpfad ungültig")
    size, digest = payload.get("expected_size"), payload.get("expected_hash")
    if type(size) is not int or size < 0:
        raise ValueError("Dateigröße ungültig")
    if not isinstance(digest, str) or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
        raise ValueError("Prüfsumme ungültig")
    folder = _FOLDERS.get(str(payload.get("kind")), "Sonstiges")
    parent = project / "Verwendet" / folder
    target = _managed_path(payload.get("target"), parent)
    if payload.get("temp"):
        temp = _managed_path(payload["temp"], parent)
        if not (temp.name.startswith("archive_") and temp.suffix == ".part"):
            raise ValueError("Temporärpfad ungültig")
    if payload.get("reservation"):
        marker = _managed_path(payload["reservation"], parent)
        if marker.name != f".{target.name}.archive-reserve":
            raise ValueError("Reservierung passt nicht zum Ziel")
    return payload


def _classify(payload: dict[str, Any], verify: Callable[[Path, int, str], None]) -> None:
    source, target = Path(payload["source"]), Path(payload["target"])
    try:
        verify(target, payload["expected_size"], payload["expected_hash"])
        valid = True
    except OSError:
        valid = False
    if valid and source.exists():
        payload["state"] = "source_retained"
        payload["message"] = "Wiederaufnahme: gültiges Ziel und Original vorhanden; Original bewusst erhalten."
    elif valid:
        payload["state"] = "committed"
        payload["message"] = "Wiederaufnahme: gültiges Ziel bestätigt und Original bereits entfernt."
    else:
        payload["state"] = "failed_safe" if source.exists() else "failed"
        payload["message"] = "Wiederaufnahme: Ziel nicht bestätigt; Dateien und Reservierung zur Diagnose erhalten."
    payload["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")


def recover_transactions(project: Path, verify: Callable[[Path, int, str], None]) -> list[dict[str, str]]:
    results: list[dict[str, str]] = []
    project = project.absolute()
    directory = project / "Verwendet" / ".transactions"
    # Recovery never creates or follows a redirected journal directory.
    if directory.resolve() != directory or not directory.is_dir():
        return results
    for journal in sorted(directory.glob("*.json")):
        try:
            if journal.is_symlink():
                raise ValueError("Journal ist eine symbolische Verknüpfung")
            payload = json.loads(journal.read_text(encoding="utf-8"))
            payload = _validate(payload, journal, project)
        except (OSError, UnicodeError, ValueError, TypeError):
            results.append({"journal": str(journal), "status": "invalid", "message": "Journal nicht lesbar."})
            continue
        if payload["state"] in _TERMINAL:
            continue
        _classify(payload, verify)
        # Persist classification only. Journal paths never authorize unlink().
        atomic_write_json(journal, payload)
        results.append({"journal": str(journal), "status": payload["state"], "message": payload["message"]})
    return results

