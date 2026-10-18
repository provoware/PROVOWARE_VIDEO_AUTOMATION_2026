#!/usr/bin/env python3
"""Local project inventory and evidence-aware test selection.

The index is stored OUTSIDE the release source tree. A stale index is never
used to authorize skipping a mandatory test or a release approval.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "registries" / "PROJECT_FILE_POLICY.json"
CATEGORIES = {
    "src": "Programmcode", "tests": "Automatische Prüfungen",
    "scripts": "Entwicklungswerkzeuge", "docs": "Dokumentation",
    "diagnostics": "Prüfberichte", "resources": "Programmressourcen",
    "registries": "Verbindliche Verträge", ".github": "CI-Automation",
    "visual_inspection": "Sichtprüfungen", "debugging": "Fehlerdiagnose",
    "toolchain_wheelhouse": "Abhängigkeiten",
}
RELEASE_SENSITIVE = {
    "RELEASE_MANIFEST.json", "VERSION.json", "requirements.lock",
    "requirements-quality.lock", "requirements-toolchain.lock",
    "pyproject.toml", "test.sh", "verify_release.sh",
}
IGNORED_DIRS = {".git", ".venv", "__pycache__", ".pytest_cache", ".mypy_cache",
                ".ruff_cache", "node_modules"}


def inventory_path() -> Path:
    base = os.environ.get("XDG_STATE_HOME")
    state = Path(base).expanduser() if base and Path(base).is_absolute() else Path.home() / ".local/state"
    digest = hashlib.sha256(str(ROOT.resolve()).encode()).hexdigest()[:12]
    return state / "videobatch" / "project_index" / f"{digest}.json"


def category(name: str) -> str:
    return CATEGORIES.get(name.split("/", 1)[0], "Start / zentrale Verträge")


def snapshot() -> dict[str, dict[str, object]]:
    """Always inspect current files, including additions/deletions/renames."""
    entries: dict[str, dict[str, object]] = {}
    for base, folders, names in os.walk(ROOT):
        folders[:] = sorted(n for n in folders if n not in IGNORED_DIRS)
        for name in sorted(names):
            path = Path(base) / name
            if path.is_symlink() or not path.is_file():
                continue
            relative = path.relative_to(ROOT).as_posix()
            stat = path.stat()
            entries[relative] = {
                "category": category(relative),
                "size": stat.st_size,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
    return entries


def changes(before: dict, after: dict) -> dict:
    prev, curr = set(before), set(after)
    old = sorted(prev - curr)
    new = sorted(curr - prev)
    modified = sorted(p for p in (prev & curr)
                      if before[p]["sha256"] != after[p]["sha256"])
    # Rename pairing is informative only; equal content is not evidence of intent.
    moved: list[dict[str, str]] = []
    for source in old[:]:
        match = next((dest for dest in new
                      if before[source]["sha256"] == after[dest]["sha256"]), None)
        if match:
            moved.append({"from": source, "to": match})
            old.remove(source)
            new.remove(match)
    return {"added": new, "deleted": old, "modified": modified, "renamed": moved}


def choose_tests(delta: dict) -> dict:
    touched = set(delta["added"] + delta["deleted"] + delta["modified"])
    for moved in delta["renamed"]:
        touched.update((moved["from"], moved["to"]))
    modes: list[str] = []
    reasons: list[str] = []
    if not touched:
        return {"suggested": [], "reason": ["Kein Dateiunterschied"],
                "mandatory_release_checks_skippable": False}
    if any(p in RELEASE_SENSITIVE or p.startswith(".github/") for p in touched):
        modes = ["--core", "--local"]
        reasons.append("Release-/CI-/Toolchain-Vertrag verändert")
    elif all(p.startswith("docs/") or p.endswith(".md") for p in touched):
        modes = ["--docs"]
        reasons.append("Nur Dokumentation verändert")
    else:
        modes = ["--core"]
        reasons.append("Programmcode, Ressourcen oder Tests verändert")
        if any(p.startswith(("src/videobatch_fast/qt_", "src/videobatch_fast/ui")) for p in touched):
            modes.append("--local")
            reasons.append("GUI-Code verändert: Oberfläche praktisch prüfen")
    return {"suggested": modes, "reason": reasons,
            "mandatory_release_checks_skippable": False}


def load_previous(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, ValueError, OSError):
        return {}
    return data.get("files", {}) if data.get("schema_version") == 1 else {}


def refresh() -> dict:
    path = inventory_path()
    previous = load_previous(path)
    files = snapshot()
    delta = changes(previous, files)
    result = {"schema_version": 1, "root": str(ROOT.resolve()),
              "updated_unix": int(time.time()), "files": files,
              "changes": delta, "test_advice": choose_tests(delta)}
    path.parent.mkdir(parents=True, exist_ok=True)
    import tempfile
    import os as _os
    fd, temp = tempfile.mkstemp(prefix=".index-", dir=path.parent)
    try:
        with _os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(result, stream, ensure_ascii=False, sort_keys=True, indent=2)
            stream.write("\n")
            stream.flush()
            _os.fsync(stream.fileno())
        _os.replace(temp, path)
    finally:
        Path(temp).unlink(missing_ok=True)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Datei- und Prüfindex ohne Releasefreigabe")
    parser.add_argument("--watch", action="store_true",
                        help="Änderungen während der Entwicklung automatisch registrieren")
    parser.add_argument("--interval", type=float, default=5.0)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    if args.watch and args.interval < 1:
        parser.error("Das Überwachungsintervall muss mindestens 1 Sekunde betragen.")
    last = None
    while True:
        result = refresh()
        digest = hashlib.sha256(json.dumps(result["files"], sort_keys=True).encode()).hexdigest()
        if digest != last:
            if args.json:
                print(json.dumps({"count": len(result["files"]),
                    "changes": result["changes"], "test_advice": result["test_advice"],
                    "index": str(inventory_path())}, ensure_ascii=False), flush=True)
            else:
                print(f"Dateiindex: {len(result['files'])} Dateien · {inventory_path()}", flush=True)
                print("Prüfempfehlung:", ", ".join(result["test_advice"]["suggested"])
                      or "keine Änderung", flush=True)
            last = digest
        if not args.watch:
            return 0
        try:
            time.sleep(args.interval)
        except KeyboardInterrupt:
            return 0


if __name__ == "__main__":
    raise SystemExit(main())
