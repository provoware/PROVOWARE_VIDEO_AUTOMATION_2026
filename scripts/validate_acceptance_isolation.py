#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

REPORT_NAME = "installation-hygiene-latest.json"
PERSISTENT_ENV_KEYS = (
    "HOME",
    "XDG_DATA_HOME",
    "XDG_CONFIG_HOME",
    "XDG_STATE_HOME",
    "XDG_CACHE_HOME",
)
FORBIDDEN_ACCEPTANCE_OVERRIDES = (
    "VIDEOBATCH_INSTALL_ROOT",
    "VIDEOBATCH_PORTABLE_LAUNCHER",
    "VIDEOBATCH_PORTABLE",
    "VIDEOBATCH_RUNTIME_PYTHON",
    "VIDEOBATCH_QUALITY_PYTHON",
    "VIDEOBATCH_TOOLCHAIN_PYTHON",
)
CANONICAL_PATH_FIELDS = (
    "canonical_install_root",
    "canonical_desktop_entry",
    "canonical_launcher",
)
PATH_LIST_FIELDS = (
    "desktop_entries_removed",
    "legacy_installations_retired",
    "protected_user_data",
)
PATH_RECORD_FIELDS = (
    "legacy_installations_detected",
    "legacy_installations_blocked",
)


def _resolved(path: str | Path) -> Path:
    return Path(path).expanduser().resolve(strict=False)


def _inside(path: str | Path, root: Path) -> bool:
    try:
        _resolved(path).relative_to(_resolved(root))
    except (ValueError, OSError, RuntimeError):
        return False
    return True


def validate_environment(test_home: Path, environ: Mapping[str, str] | None = None) -> list[str]:
    env = os.environ if environ is None else environ
    root = _resolved(test_home)
    errors: list[str] = []

    home = str(env.get("HOME", "")).strip()
    if not home or _resolved(home) != root:
        errors.append(f"HOME zeigt nicht exakt auf die Test-Heimat: {home or '<leer>'}")

    for key in PERSISTENT_ENV_KEYS[1:]:
        value = str(env.get(key, "")).strip()
        if not value:
            errors.append(f"{key} ist für die Abnahme nicht gesetzt")
        elif not _inside(value, root):
            errors.append(f"{key} verlässt die Test-Heimat: {value}")

    for key in FORBIDDEN_ACCEPTANCE_OVERRIDES:
        value = str(env.get(key, "")).strip()
        if value:
            errors.append(f"{key} darf die Abnahme nicht von außen beeinflussen: {value}")

    return errors


def _iter_paths(items: Any) -> Iterable[str]:
    if not isinstance(items, list):
        return ()
    return (str(item) for item in items if isinstance(item, (str, Path)))


def _iter_record_paths(items: Any) -> Iterable[str]:
    if not isinstance(items, list):
        return ()
    return (
        str(item.get("path", ""))
        for item in items
        if isinstance(item, dict) and str(item.get("path", "")).strip()
    )


def validate_hygiene_report(report: Mapping[str, Any], test_home: Path) -> list[str]:
    root = _resolved(test_home)
    errors: list[str] = []

    if report.get("schema_version") != 1:
        errors.append(f"Unbekannte Hygienebericht-Version: {report.get('schema_version')!r}")

    for field in CANONICAL_PATH_FIELDS:
        value = str(report.get(field, "")).strip()
        if not value:
            errors.append(f"Hygienebericht ohne {field}")
        elif not _inside(value, root):
            errors.append(f"{field} verlässt die Test-Heimat: {value}")

    current = report.get("current_install_root")
    if current not in (None, ""):
        errors.append(f"Echte/äußere Installation in der Abnahme geerbt: {current}")

    if report.get("destructive_cleanup_allowed") is not False:
        errors.append("Destruktive Installationsbereinigung muss in der Test-Heimat gesperrt bleiben")

    for field in PATH_LIST_FIELDS:
        values = report.get(field, [])
        if not isinstance(values, list):
            errors.append(f"{field} ist keine Liste")
            continue
        for value in _iter_paths(values):
            if not _inside(value, root):
                errors.append(f"{field} enthält Pfad außerhalb der Test-Heimat: {value}")

    for field in PATH_RECORD_FIELDS:
        values = report.get(field, [])
        if not isinstance(values, list):
            errors.append(f"{field} ist keine Liste")
            continue
        for value in _iter_record_paths(values):
            if not _inside(value, root):
                errors.append(f"{field} enthält Pfad außerhalb der Test-Heimat: {value}")

    return errors


def find_reports(report_root: Path) -> list[Path]:
    root = _resolved(report_root)
    if not root.is_dir():
        return []
    return sorted(path for path in root.rglob(REPORT_NAME) if path.is_file() and not path.is_symlink())


def validate(test_home: Path, report_root: Path, environ: Mapping[str, str] | None = None) -> dict[str, Any]:
    root = _resolved(test_home)
    report_base = _resolved(report_root)
    errors = validate_environment(root, environ)

    if not _inside(report_base, root):
        errors.append(f"Berichtswurzel liegt außerhalb der Test-Heimat: {report_base}")
        reports: list[Path] = []
    else:
        reports = find_reports(report_base)

    if len(reports) != 1:
        errors.append(f"Genau ein Hygienebericht erwartet, gefunden: {len(reports)}")

    checked: list[str] = []
    for path in reports:
        checked.append(str(path))
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            errors.append(f"Hygienebericht unlesbar: {path}: {exc}")
            continue
        if not isinstance(payload, dict):
            errors.append(f"Hygienebericht ist kein JSON-Objekt: {path}")
            continue
        errors.extend(validate_hygiene_report(payload, root))

    return {
        "schema_version": 1,
        "status": "passed" if not errors else "failed",
        "test_home": str(root),
        "report_root": str(report_base),
        "reports": checked,
        "errors": errors,
        "xdg_runtime_dir": str((os.environ if environ is None else environ).get("XDG_RUNTIME_DIR", "")),
        "note": "XDG_RUNTIME_DIR bleibt absichtlich außerhalb der Test-Heimat, damit Wayland/DBus erreichbar bleiben.",
    }


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        description="Prüft fail-closed, dass die echte STARTEN.sh-Abnahme nur die isolierte Test-Heimat verändert."
    )
    result.add_argument("--test-home", type=Path, required=True)
    result.add_argument("--report-root", type=Path, required=True)
    return result


def main(argv: Sequence[str] | None = None) -> int:
    args = parser().parse_args(argv)
    result = validate(args.test_home, args.report_root)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
