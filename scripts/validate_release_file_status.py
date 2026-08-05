#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "docs/archive/release-history"
READY_MARKER = "_save_"
LEGACY_PREFIXES = ("CODE_QUALITY_REPORT_", "IMPLEMENTATION_REPORT_", "FINAL_AUDIT_", "VideoBatch_Fast_")


def _object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: JSON-Wurzel ist kein Objekt")
    return value


def validate(root: Path = ROOT) -> dict[str, Any]:
    contract = _object(root / "RELEASE_FILE_STATUS.json")
    if contract.get("scope") != "standalone_release_deliverables" or contract.get("ready_suffix") != READY_MARKER:
        raise ValueError("Release-Dateivertrag besitzt einen unbekannten Geltungsbereich")
    seen: set[str] = set()
    for group in ("ready", "unfinished"):
        entries = contract.get(group)
        if not isinstance(entries, list) or not entries:
            raise ValueError(f"Release-Dateivertrag enthält keine Gruppe {group}")
        for entry in entries:
            relative = str(entry.get("path", ""))
            candidate = Path(relative)
            if not relative or candidate.is_absolute() or ".." in candidate.parts:
                raise ValueError(f"Ungültiger Releasepfad: {relative}")
            if relative in seen:
                raise ValueError(f"Doppelter Releasepfad: {relative}")
            seen.add(relative)
            if not (root / candidate).is_file():
                raise ValueError(f"Deklarierte Datei fehlt: {relative}")
            has_marker = READY_MARKER in candidate.stem
            if group == "ready" and not has_marker:
                raise ValueError(f"Releasefertige Datei besitzt kein _save_: {relative}")
            if group == "unfinished" and has_marker:
                raise ValueError(f"Unfertige Datei trägt fälschlich _save_: {relative}")
            if group == "ready":
                old_name = candidate.name.replace(READY_MARKER, "")
                if (root / candidate.with_name(old_name)).exists():
                    raise ValueError(f"Ungesicherte Dublette existiert: {old_name}")
    old_root_reports = [
        path.name for path in root.iterdir()
        if path.is_file() and path.name.startswith(LEGACY_PREFIXES) and READY_MARKER not in path.stem
    ]
    if old_root_reports:
        raise ValueError("Historische Berichte liegen noch im Projektstamm: " + ", ".join(sorted(old_root_reports)))
    if (root / "tests/baselines/visual").exists():
        raise ValueError("Veraltete doppelte visuelle Baselines existieren noch")
    if not ARCHIVE.is_dir():
        raise ValueError("Historisches Releasearchiv fehlt")
    for document_name in ("README.md", "STATUS.md"):
        document = (root / document_name).read_text(encoding="utf-8")
        if "<!-- release-files:start -->" not in document or "<!-- release-files:end -->" not in document:
            raise ValueError(f"{document_name}: Release-Dateitabelle fehlt")
        for relative in seen:
            if f"`{relative}`" not in document:
                raise ValueError(f"{document_name}: deklarierter Releasepfad fehlt: {relative}")
    return contract


def main() -> int:
    try:
        contract = validate()
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print(f"RELEASE-DATEISTATUS BLOCKIERT: {exc}")
        return 1
    print(f"RELEASE-DATEISTATUS BESTANDEN · {len(contract['ready'])} fertig · {len(contract['unfinished'])} offen")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
