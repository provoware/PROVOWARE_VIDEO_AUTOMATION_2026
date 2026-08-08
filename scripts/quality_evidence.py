#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
import zipfile
from pathlib import Path
from typing import Any

try:
    from release_identity import ROOT, release_identity, sha256_file
except ModuleNotFoundError:  # Import als scripts.quality_evidence
    from scripts.release_identity import ROOT, release_identity, sha256_file

REQUIRED_TOOLS = {"ruff": "0.16.1", "mypy": "2.3.0", "bandit": "1.9.4", "pip-audit": "2.10.1"}
INDEX_NAME = "QUALITY_EVIDENCE_INDEX.json"


class QualityEvidenceError(RuntimeError):
    pass


def _load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise QualityEvidenceError(f"{path.name} ist unlesbar: {exc}") from exc
    if not isinstance(value, dict):
        raise QualityEvidenceError(f"{path.name} ist kein JSON-Objekt.")
    return value


def validate_external_report(path: Path, *, root: Path = ROOT) -> dict[str, Any]:
    report = _load(path)
    identity = release_identity(root)
    if report.get("schema_version") != 4:
        raise QualityEvidenceError("Externer Qualitätsnachweis verwendet nicht das sourcegebundene Schema 4.")
    if report.get("candidate_identity") != identity:
        raise QualityEvidenceError("Externer Qualitätsnachweis ist stale oder gehört zu einem anderen Kandidaten.")
    if report.get("offline") is not True:
        raise QualityEvidenceError("Externer Qualitätsnachweis wurde nicht mit Offline-Netzwerksperre erzeugt.")
    results = report.get("results")
    if not isinstance(results, list):
        raise QualityEvidenceError("Externer Qualitätsnachweis enthält keine Werkzeugergebnisse.")
    actual = {str(item.get("tool")): item for item in results if isinstance(item, dict)}
    if set(actual) != set(REQUIRED_TOOLS):
        raise QualityEvidenceError(f"Werkzeugmenge unvollständig: {sorted(actual)}")
    for name, version in REQUIRED_TOOLS.items():
        item = actual[name]
        if item.get("status") != "pass" or item.get("returncode") != 0 or item.get("version") != version:
            raise QualityEvidenceError(f"{name} ist nicht exakt bestanden ({item.get('version')}, {item.get('status')}).")
        if item.get("offline_guard") is not True:
            raise QualityEvidenceError(f"{name} lief ohne Offline-Netzwerksperre.")
    return report


def _evidence_files(directory: Path) -> list[Path]:
    result: list[Path] = []
    for path in sorted(directory.rglob("*")):
        if not path.is_file() or path.is_symlink():
            continue
        if path.name == INDEX_NAME or path.suffix == ".zip":
            continue
        result.append(path)
    return result


def build_index(directory: Path, *, root: Path = ROOT, require_pass: bool = True) -> dict[str, Any]:
    report_path = directory / "diagnostics" / "external_quality_latest.json"
    if not report_path.is_file():
        report_path = directory / "external_quality_latest.json"
    if require_pass:
        validate_external_report(report_path, root=root)
    files = []
    for path in _evidence_files(directory):
        rel = path.relative_to(directory).as_posix()
        files.append({"path": rel, "size": path.stat().st_size, "sha256": sha256_file(path)})
    if not files:
        raise QualityEvidenceError("Evidence-Ordner enthält keine Nachweisdateien.")
    return {
        "schema_version": 1,
        "evidence_type": "external_quality",
        "candidate_identity": release_identity(root),
        "required_tools": REQUIRED_TOOLS,
        "status": "passed" if require_pass else "collected",
        "files": files,
    }


def write_index(directory: Path, payload: dict[str, Any]) -> Path:
    target = directory / INDEX_NAME
    text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    fd, raw = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".tmp", dir=directory)
    tmp = Path(raw)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, target)
    finally:
        tmp.unlink(missing_ok=True)
    return target


def verify_index(directory: Path, *, root: Path = ROOT, require_pass: bool = True) -> dict[str, Any]:
    index = _load(directory / INDEX_NAME)
    if index.get("schema_version") != 1 or index.get("evidence_type") != "external_quality":
        raise QualityEvidenceError("Evidence-Indexformat ist ungültig.")
    if index.get("candidate_identity") != release_identity(root):
        raise QualityEvidenceError("Evidence-Index ist stale oder für einen anderen Source-/Manifest-Stand erzeugt.")
    if require_pass and index.get("status") != "passed":
        raise QualityEvidenceError("Evidence-Bundle enthält keinen bestandenen Qualitätslauf.")
    entries = index.get("files")
    if not isinstance(entries, list) or not entries:
        raise QualityEvidenceError("Evidence-Index enthält keine Dateien.")
    declared: set[str] = set()
    for raw in entries:
        if not isinstance(raw, dict):
            raise QualityEvidenceError("Ungültiger Evidence-Dateieintrag.")
        rel = str(raw.get("path", ""))
        if not rel or rel in declared or Path(rel).is_absolute() or ".." in Path(rel).parts:
            raise QualityEvidenceError(f"Unsicherer Evidence-Pfad: {rel!r}")
        declared.add(rel)
        path = directory / rel
        if not path.is_file() or path.is_symlink():
            raise QualityEvidenceError(f"Evidence-Datei fehlt: {rel}")
        if path.stat().st_size != int(raw.get("size", -1)) or sha256_file(path) != str(raw.get("sha256", "")):
            raise QualityEvidenceError(f"Evidence-Datei verändert: {rel}")
    actual = {path.relative_to(directory).as_posix() for path in _evidence_files(directory)}
    if actual != declared:
        raise QualityEvidenceError("Evidence-Dateimenge weicht vom Index ab.")
    if require_pass:
        report = directory / "diagnostics" / "external_quality_latest.json"
        if not report.is_file():
            report = directory / "external_quality_latest.json"
        validate_external_report(report, root=root)
    return index


def build_zip(directory: Path, output: Path, *, root: Path = ROOT) -> Path:
    verify_index(directory, root=root, require_pass=True)
    output.parent.mkdir(parents=True, exist_ok=True)
    fd, raw = tempfile.mkstemp(prefix=f".{output.name}.", suffix=".tmp", dir=output.parent)
    os.close(fd)
    tmp = Path(raw)
    try:
        with zipfile.ZipFile(tmp, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            members = [directory / INDEX_NAME, *_evidence_files(directory)]
            for path in sorted(members, key=lambda p: p.relative_to(directory).as_posix()):
                rel = path.relative_to(directory).as_posix()
                info = zipfile.ZipInfo(rel, date_time=(1980, 1, 1, 0, 0, 0))
                info.create_system = 3
                info.external_attr = (0o100600 << 16)
                archive.writestr(info, path.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
        os.replace(tmp, output)
    finally:
        tmp.unlink(missing_ok=True)
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description="Erzeugt/verifiziert sourcegebundene externe Quality-Evidence.")
    parser.add_argument("action", choices=("build", "verify", "bundle"))
    parser.add_argument("--evidence-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    directory = args.evidence_dir.resolve()
    directory.mkdir(parents=True, exist_ok=True)
    if args.action == "build":
        payload = build_index(directory)
        path = write_index(directory, payload)
        print(path)
    elif args.action == "verify":
        verify_index(directory)
        print("QUALITY-EVIDENCE BESTANDEN · Source/Manifest/Tools/Dateien unverändert")
    else:
        if not (directory / INDEX_NAME).is_file():
            write_index(directory, build_index(directory))
        output = args.output or directory.with_name(directory.name + ".zip")
        build_zip(directory, output)
        print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
