#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import shutil
from pathlib import Path

EXCLUDED = {
    ".git", ".pytest_cache", ".ruff_cache", ".mypy_cache", ".videobatch-venv",
    "dist", "diagnostics", "visual_actual", "actual", "diff", "__pycache__",
}
BINARY_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".zip", ".whl", ".pyc", ".pem"}


def _blocked(message: str) -> RuntimeError:
    return RuntimeError(
        f"Ursache: {message} Auswirkung: Die Stable-Promotion beginnt nicht. "
        "Schutzmaßnahme: RC-Arbeitskopie und Ausgabeziel bleiben unverändert. "
        "Lösung: Alle Stable-Gates für diesen Kandidaten belegen und den Status aktualisieren. "
        "Alternative: Den RC-Kandidaten unverändert weiter prüfen."
    )


def validate_promotion_source(source: Path) -> tuple[dict[str, object], str]:
    version = json.loads((source / "VERSION.json").read_text(encoding="utf-8"))
    status = json.loads((source / "DEVELOPMENT_STATUS.json").read_text(encoding="utf-8"))
    build = str(version["build"])
    if version.get("channel") != "rc" or status.get("version") != build:
        raise _blocked("Versionsvertrag und Freigabestatus bezeichnen nicht denselben RC-Kandidaten.")
    report_name = status.get("approved_quality_report")
    if not isinstance(report_name, str) or Path(report_name).name != report_name:
        raise _blocked("Der freigegebene Qualitätsbericht ist nicht eindeutig benannt.")
    report = json.loads((source / report_name).read_text(encoding="utf-8"))
    blockers = [*status.get("stable_blockers", []), *report.get("stable_blockers", [])]
    if not status.get("stable_ready") or not report.get("stable_ready") or blockers:
        raise _blocked(f"Stable-Nachweise für {build} sind offen: {', '.join(blockers) or 'Freigabe fehlt'}.")
    if report.get("version") != build or report.get("status") != "passed":
        raise _blocked("Der freigegebene Qualitätsbericht gehört nicht bestanden zu diesem Kandidaten.")
    match = re.fullmatch(r"(.+)-rc\d+", build)
    if not match:
        raise _blocked("Die RC-Version in VERSION.json hat kein unterstütztes Format.")
    return version, match.group(1)


def ignore(_directory: str, names: list[str]) -> set[str]:
    return {name for name in names if name in EXCLUDED or name.endswith((".pyc", ".pyo"))}


def replace_text(root: Path, old_build: str, stable: str) -> None:
    old_pep = old_build.replace("-rc", "rc")
    for path in root.rglob("*"):
        if not path.is_file() or path.is_symlink() or path.suffix.lower() in BINARY_SUFFIXES:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            continue
        updated = text.replace(old_build, stable).replace(old_pep, stable)
        if updated != text:
            path.write_text(updated, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Erzeugt eine getrennte Stable-Arbeitskopie.")
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    args = parser.parse_args()
    source = args.source.resolve(strict=True)
    destination = args.destination.resolve(strict=False)
    version, stable_version = validate_promotion_source(source)
    if destination.exists():
        raise _blocked(f"Das Ausgabeziel {destination} existiert bereits.")
    shutil.copytree(source, destination, symlinks=False, ignore=ignore)
    version_path = destination / "VERSION.json"
    old_build = str(version["build"])
    replace_text(destination, old_build, stable_version)
    version = json.loads(version_path.read_text(encoding="utf-8"))
    version.update({
        "version": stable_version,
        "build": stable_version,
        "channel": "stable",
        "purpose": "Stabile VideoBatch-Freigabe nach vollständig grüner autonomer Releaseprüfung.",
    })
    version_path.write_text(json.dumps(version, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for relative in ("AUTOMATED_DESKTOP_APPROVAL.json", "visual_inspection/live_desktop_approval.png", "RELEASE_MANIFEST.json"):
        (destination / relative).unlink(missing_ok=True)
    for old_name, new_name in (
        (f"IMPLEMENTATION_REPORT_{old_build}.md", f"IMPLEMENTATION_REPORT_{stable_version}.md"),
        (f"CODE_QUALITY_REPORT_{old_build}.md", f"CODE_QUALITY_REPORT_{stable_version}.md"),
    ):
        old = destination / old_name
        if old.exists():
            old.rename(destination / new_name)
    print(f"STABLE-ARBEITSKOPIE ERZEUGT · {destination}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, KeyError, ValueError, RuntimeError) as exc:
        print(f"STABLE-PROMOTION BLOCKIERT: {exc}")
        raise SystemExit(1)
