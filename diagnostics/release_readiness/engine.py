from __future__ import annotations

import hashlib
import json
import os
import re
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, Sequence

PASS_WORDS = ("pass", "passed", "success", "successful", "green", "completed")
FAIL_WORDS = ("failed", "failure", "error", "cancelled", "timed_out", "action_required")
OPEN_WORDS = ("required", "open", "pending", "not installed", "not executed", "blocked", "missing", "unknown")


class EvidenceError(RuntimeError):
    pass


@dataclass(frozen=True)
class Finding:
    severity: str
    code: str
    message: str
    sources: tuple[str, ...] = ()


@dataclass(frozen=True)
class Gate:
    id: str
    label: str
    status: str
    detail: str
    source: str
    required: bool = True


def safe_join(root: Path, relative: str) -> Path:
    pure = PurePosixPath(relative)
    if not relative or pure.is_absolute() or ".." in pure.parts:
        raise EvidenceError(f"Unsicherer relativer Pfad: {relative!r}")
    return root.joinpath(*pure.parts)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalize_status(value: Any) -> str:
    text = str(value or "").strip().lower().replace("-", "_")
    if not text:
        return "unknown"
    if text in {"fail", "red"} or any(word in text for word in FAIL_WORDS):
        return "fail"
    if text in {"queued", "in_progress", "waiting", "requested"}:
        return "running"
    if any(word in text for word in PASS_WORDS):
        return "pass"
    if any(word in text for word in OPEN_WORDS):
        return "open"
    return "unknown"


def nested(document: Mapping[str, Any], *path: str) -> Any:
    value: Any = document
    for part in path:
        if not isinstance(value, Mapping) or part not in value:
            return None
        value = value[part]
    return value


def integer(document: Mapping[str, Any], *path: str) -> int | None:
    value = nested(document, *path)
    if isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def floating(document: Mapping[str, Any], *path: str) -> float | None:
    value = nested(document, *path)
    if isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise EvidenceError(f"Ungültige JSON-Quelle {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise EvidenceError(f"JSON-Wurzel muss ein Objekt sein: {path}")
    return value


def load_evidence(root: Path) -> tuple[dict[str, dict[str, Any]], dict[str, Path], dict[str, str]]:
    required = {
        "manifest": "RELEASE_MANIFEST.json",
        "development": "DEVELOPMENT_STATUS.json",
        "quality": "QUALITY_ENVIRONMENT_STATUS.json",
        "release_files": "RELEASE_FILE_STATUS.json",
    }
    documents: dict[str, dict[str, Any]] = {}
    paths: dict[str, Path] = {}
    hashes: dict[str, str] = {}
    for key, relative in required.items():
        path = safe_join(root, relative)
        if not path.is_file():
            raise EvidenceError(f"Pflichtquelle fehlt: {relative}")
        documents[key] = read_json(path)
        paths[key] = path
        hashes[key] = sha256_file(path)
    report = str(documents["development"].get("approved_quality_report") or "").strip()
    if not report:
        candidates = sorted(root.glob("VideoBatch_*_BUILD_REPORT_save_.json"))
        if len(candidates) != 1:
            raise EvidenceError("Freigegebener Buildbericht ist nicht eindeutig bestimmbar.")
        report = candidates[0].name
    report_path = safe_join(root, report)
    if not report_path.is_file():
        raise EvidenceError(f"Freigegebener Buildbericht fehlt: {report}")
    documents["build"] = read_json(report_path)
    paths["build"] = report_path
    hashes["build"] = sha256_file(report_path)
    return documents, paths, hashes


def unchanged_findings(paths: Mapping[str, Path], hashes: Mapping[str, str]) -> list[Finding]:
    findings: list[Finding] = []
    for key, expected in hashes.items():
        try:
            current = sha256_file(paths[key])
        except OSError as exc:
            findings.append(Finding("error", "INPUT_UNREADABLE_AFTER_RUN", f"Quelle nach Lauf nicht lesbar: {paths[key]}: {exc}", (key,)))
            continue
        if current != expected:
            findings.append(Finding("error", "INPUT_MUTATED", f"Eingabequelle wurde verändert: {paths[key]}", (key,)))
    return findings


def compare(findings: list[Finding], code: str, label: str, values: Mapping[str, Any]) -> None:
    present = {key: value for key, value in values.items() if value not in (None, "")}
    if len(present) < 2:
        findings.append(Finding("warning", f"{code}_INSUFFICIENT", f"{label}: zu wenige Vergleichsquellen.", tuple(present)))
        return
    if len({json.dumps(value, sort_keys=True, ensure_ascii=False) for value in present.values()}) > 1:
        detail = ", ".join(f"{key}={value!r}" for key, value in sorted(present.items()))
        findings.append(Finding("error", code, f"Widerspruch bei {label}: {detail}", tuple(sorted(present))))


def validate_manifest(root: Path, manifest: Mapping[str, Any], findings: list[Finding]) -> bool:
    items = manifest.get("files")
    if not isinstance(items, list):
        findings.append(Finding("error", "MANIFEST_FILES_INVALID", "Manifestfeld `files` ist keine Liste.", ("manifest",)))
        return False
    valid = integer(manifest, "file_count") == len(items)
    if not valid:
        findings.append(Finding("error", "MANIFEST_SELF_COUNT_MISMATCH", f"Manifest nennt {integer(manifest, 'file_count')} Dateien, enthält aber {len(items)} Einträge.", ("manifest",)))
    seen: set[str] = set()
    for index, item in enumerate(items):
        if not isinstance(item, Mapping):
            findings.append(Finding("error", "MANIFEST_ITEM_INVALID", f"Eintrag {index} ist kein Objekt.", ("manifest",)))
            valid = False
            continue
        rel = str(item.get("path") or "")
        try:
            path = safe_join(root, rel)
        except EvidenceError as exc:
            findings.append(Finding("error", "MANIFEST_PATH_UNSAFE", str(exc), ("manifest",)))
            valid = False
            continue
        if rel in seen:
            findings.append(Finding("error", "MANIFEST_PATH_DUPLICATE", f"Doppelter Manifestpfad: {rel}", ("manifest",)))
            valid = False
            continue
        seen.add(rel)
        if not path.is_file() or path.is_symlink():
            findings.append(Finding("error", "MANIFEST_FILE_MISSING", f"Manifestdatei fehlt oder ist ein Link: {rel}", ("manifest",)))
            valid = False
            continue
        expected_size = item.get("size")
        if expected_size is not None and int(expected_size) != path.stat().st_size:
            findings.append(Finding("error", "MANIFEST_SIZE_MISMATCH", f"Größe stimmt nicht: {rel}", ("manifest",)))
            valid = False
        expected_hash = str(item.get("sha256") or "")
        if expected_hash and expected_hash != sha256_file(path):
            findings.append(Finding("error", "MANIFEST_HASH_MISMATCH", f"SHA-256 stimmt nicht: {rel}", ("manifest",)))
            valid = False
    return valid


def load_ci_snapshot(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {"schema_version": 1, "status": "unknown", "checks": [], "source": "not supplied"}
    value = read_json(path)
    value.setdefault("checks", [])
    value.setdefault("status", "unknown")
    value.setdefault("source", str(path))
    return value


def github_json(url: str, token: str | None) -> Any:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "provoware-release-readiness-dashboard/1",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=15) as response:
            return json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError) as exc:
        raise EvidenceError(f"GitHub-CI-Status nicht lesbar: {exc}") from exc


def fetch_github_ci(repository: str, sha: str, token: str | None) -> dict[str, Any]:
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
        raise EvidenceError(f"Ungültiger GitHub-Repositoryname: {repository}")
    if not re.fullmatch(r"[0-9a-fA-F]{7,64}", sha):
        raise EvidenceError(f"Ungültige Commit-SHA: {sha}")
    base = f"https://api.github.com/repos/{repository}"
    check_payload = github_json(f"{base}/commits/{sha}/check-runs?per_page=100", token)
    run_payload = github_json(f"{base}/actions/runs?head_sha={sha}&per_page=100", token)
    checks: list[dict[str, str]] = []
    for item, kind in [
        *((item, "check-run") for item in check_payload.get("check_runs", []) if isinstance(check_payload, dict)),
        *((item, "workflow-run") for item in run_payload.get("workflow_runs", []) if isinstance(run_payload, dict)),
    ]:
        raw = item.get("conclusion") or item.get("status") or "unknown"
        checks.append({
            "name": str(item.get("name") or "unnamed"),
            "status": normalize_status(raw),
            "raw_status": str(raw),
            "url": str(item.get("html_url") or ""),
            "kind": kind,
        })
    statuses = {item["status"] for item in checks}
    status = "fail" if "fail" in statuses else "running" if "running" in statuses else "pass" if checks and statuses <= {"pass"} else "unknown"
    return {"schema_version": 1, "repository": repository, "sha": sha, "status": status, "checks": checks, "source": "GitHub REST API"}


def build_gates(documents: Mapping[str, Mapping[str, Any]], ci: Mapping[str, Any], manifest_valid: bool) -> list[Gate]:
    manifest, development, quality, build = (documents[key] for key in ("manifest", "development", "quality", "build"))
    external = quality.get("external_gates") if isinstance(quality.get("external_gates"), Mapping) else {}
    tests = integer(build, "tests", "passed")
    failed = integer(quality, "internal_gates", "tests", "failed")
    gates = [
        Gate("automated-tests", "Automatisierte Tests", "pass" if tests and failed in (None, 0) else "fail" if failed else "unknown", f"Buildbericht: {tests or 0} bestanden; Qualitätsquelle: {failed if failed is not None else 'unbekannt'} fehlgeschlagen", "Buildbericht + Qualitätsstatus"),
        Gate("release-manifest", "Release-Manifest", "pass" if manifest_valid and integer(manifest, "file_count") == integer(build, "release_manifest_files") else "fail", f"Manifest={integer(manifest, 'file_count')}, Buildbericht={integer(build, 'release_manifest_files')}", "RELEASE_MANIFEST.json + Buildbericht"),
    ]
    for key, label in (
        ("ruff_0_16_1", "Ruff 0.16.1"),
        ("mypy_2_3_0", "MyPy 2.3.0"),
        ("bandit_1_9_4", "Bandit 1.9.4"),
        ("pip_audit_2_10_1", "pip-audit 2.10.1"),
        ("physical_kde_x11_wayland", "Physische KDE-X11-/Wayland-Abnahme"),
        ("large_media_soak", "Langzeitrender mit großer Medienauswahl"),
    ):
        raw = external.get(key, "unknown")
        gates.append(Gate(key, label, normalize_status(raw), str(raw), "QUALITY_ENVIRONMENT_STATUS.json"))
    checks = ci.get("checks") if isinstance(ci.get("checks"), list) else []
    gates.append(Gate("ci", "CI-Status des geprüften Commits", normalize_status(ci.get("status")), f"{len(checks)} Checks; Quelle: {ci.get('source', 'unknown')}", "CI-Snapshot/GitHub API"))
    blockers = development.get("stable_blockers") if isinstance(development.get("stable_blockers"), list) else []
    gates.append(Gate("blocker-contract", "Stable-Blockerliste", "open" if blockers else "pass", f"{len(blockers)} offene Blocker", "DEVELOPMENT_STATUS.json"))
    return gates


def analyze(root: Path, documents: Mapping[str, Mapping[str, Any]], ci: Mapping[str, Any]) -> tuple[list[Finding], list[Gate]]:
    manifest, development, quality, release_files, build = (documents[key] for key in ("manifest", "development", "quality", "release_files", "build"))
    findings: list[Finding] = []
    manifest_valid = validate_manifest(root, manifest, findings)
    compare(findings, "VERSION_MISMATCH", "Version", {
        "manifest": manifest.get("build"), "development": development.get("version"), "quality": quality.get("build"), "release_files": release_files.get("version"), "build": build.get("version"),
    })
    compare(findings, "MANIFEST_COUNT_MISMATCH", "Manifest-Dateizahl", {
        "manifest": integer(manifest, "file_count"), "quality": integer(quality, "internal_gates", "release_manifest_files"), "build": integer(build, "release_manifest_files"),
    })
    compare(findings, "TEST_COUNT_MISMATCH", "bestandene Tests", {
        "quality": integer(quality, "internal_gates", "tests", "passed"), "build": integer(build, "tests", "passed"),
    })
    compare(findings, "STABLE_READY_MISMATCH", "Stable-Bereitschaft", {
        "development": development.get("stable_ready"), "quality": quality.get("stable_ready"), "build": build.get("stable_ready"),
    })
    blockers = development.get("stable_blockers") if isinstance(development.get("stable_blockers"), list) else []
    build_blockers = build.get("stable_blockers") if isinstance(build.get("stable_blockers"), list) else []
    if any(document.get("stable_ready") is True for document in (development, quality, build)) and (blockers or build_blockers):
        findings.append(Finding("error", "READY_WITH_BLOCKERS", "Stable wurde freigegeben, obwohl Blocker eingetragen sind.", ("development", "build")))
    listed = {str(item.get("path")) for item in manifest.get("files", []) if isinstance(item, Mapping)}
    for item in release_files.get("ready", []) if isinstance(release_files.get("ready"), list) else []:
        if not isinstance(item, Mapping):
            continue
        rel = str(item.get("path") or "")
        if "_save_" not in Path(rel).stem:
            findings.append(Finding("error", "READY_SUFFIX_MISSING", f"Releasefertig ohne `_save_`: {rel}", ("release_files",)))
        if rel not in listed:
            findings.append(Finding("error", "READY_FILE_NOT_MANIFESTED", f"Releasefertige Datei fehlt im Manifest: {rel}", ("release_files", "manifest")))
        if rel and not safe_join(root, rel).is_file():
            findings.append(Finding("error", "READY_FILE_MISSING", f"Releasefertige Datei fehlt physisch: {rel}", ("release_files",)))
    if str(manifest.get("channel") or "").lower() == "stable" and blockers:
        findings.append(Finding("error", "STABLE_CHANNEL_WITH_BLOCKERS", "Manifestkanal ist stable, obwohl Stable-Blocker offen sind.", ("manifest", "development")))
    ci_status = normalize_status(ci.get("status"))
    if ci_status == "fail":
        findings.append(Finding("error", "CI_FAILED", "Mindestens ein CI-Check ist fehlgeschlagen.", ("ci",)))
    elif ci_status in {"unknown", "running"}:
        findings.append(Finding("warning", "CI_NOT_FINAL", f"CI-Status ist {ci_status}; keine belastbare Freigabe möglich.", ("ci",)))
    coverage = floating(build, "tests", "line_coverage_percent")
    if coverage is None:
        findings.append(Finding("warning", "COVERAGE_MISSING", "Zeilenabdeckung fehlt im Buildbericht.", ("build",)))
    elif coverage < 77.0:
        findings.append(Finding("error", "COVERAGE_BELOW_GATE", f"Zeilenabdeckung {coverage:.2f} % liegt unter 77 %.", ("build",)))
    return findings, build_gates(documents, ci, manifest_valid)


def overall(findings: Sequence[Finding], gates: Sequence[Gate]) -> str:
    if any(item.severity == "error" for item in findings) or any(gate.status == "fail" for gate in gates if gate.required):
        return "red"
    if any(item.severity == "warning" for item in findings) or any(gate.status in {"open", "unknown", "running"} for gate in gates if gate.required):
        return "yellow"
    return "green"


def result_document(documents: Mapping[str, Mapping[str, Any]], ci: Mapping[str, Any], findings: Sequence[Finding], gates: Sequence[Gate], hashes: Mapping[str, str], source_sha: str | None, generated_at: str) -> dict[str, Any]:
    status = overall(findings, gates)
    required = [gate for gate in gates if gate.required]
    readiness = round(100 * sum(gate.status == "pass" for gate in required) / len(required)) if required else 0
    build = documents["build"]
    return {
        "schema_version": 1,
        "generated_at": generated_at,
        "generator": "provoware-release-readiness-dashboard",
        "read_only_inputs_verified": not any(item.code == "INPUT_MUTATED" for item in findings),
        "release": {"name": build.get("name"), "version": build.get("version"), "channel": build.get("release_channel"), "source_sha": source_sha},
        "overall_status": status,
        "stable_ready": status == "green" and all(gate.status == "pass" for gate in required),
        "readiness_percent": readiness,
        "summary": {
            "errors": sum(item.severity == "error" for item in findings),
            "warnings": sum(item.severity == "warning" for item in findings),
            "gates_passed": sum(gate.status == "pass" for gate in required),
            "gates_total": len(required),
        },
        "gates": [asdict(gate) for gate in gates],
        "findings": [asdict(item) for item in findings],
        "ci": ci,
        "input_hashes": dict(sorted(hashes.items())),
    }
