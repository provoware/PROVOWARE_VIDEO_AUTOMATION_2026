from __future__ import annotations

import hashlib
import json
import re
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Mapping

PASS_WORDS = ("pass", "passed", "success", "successful", "green", "completed")
FAIL_WORDS = ("failed", "failure", "error", "cancelled", "timed_out", "action_required")
OPEN_WORDS = ("required", "open", "pending", "not installed", "not executed", "blocked", "missing", "unknown")
RUNNING_WORDS = ("queued", "in_progress", "waiting", "requested", "running")


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
    if text in RUNNING_WORDS or any(word in text for word in RUNNING_WORDS):
        return "running"
    if any(word in text for word in PASS_WORDS):
        return "pass"
    if any(word in text for word in OPEN_WORDS):
        return "open"
    return "unknown"


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
        "evidence": "diagnostics/release_readiness/RELEASE_EVIDENCE.json",
        "manifest": "RELEASE_MANIFEST.json",
        "development": "DEVELOPMENT_STATUS.json",
        "quality": "QUALITY_ENVIRONMENT_STATUS.json",
        "release_files": "RELEASE_FILE_STATUS.json",
        "readme": "README.md",
    }
    documents: dict[str, dict[str, Any]] = {}
    paths: dict[str, Path] = {}
    hashes: dict[str, str] = {}
    for key, relative in required.items():
        path = safe_join(root, relative)
        if not path.is_file():
            raise EvidenceError(f"Pflichtquelle fehlt: {relative}")
        paths[key] = path
        hashes[key] = sha256_file(path)
        if key != "readme":
            documents[key] = read_json(path)
    report = str(documents["evidence"].get("approved_quality_report") or "").strip()
    if not report:
        raise EvidenceError("Kanonische Quelle benennt keinen Buildbericht.")
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
            findings.append(
                Finding(
                    "error",
                    "INPUT_UNREADABLE_AFTER_RUN",
                    f"Quelle nach Lauf nicht lesbar: {paths[key]}: {exc}",
                    (key,),
                )
            )
            continue
        if current != expected:
            findings.append(
                Finding(
                    "error",
                    "INPUT_MUTATED",
                    f"Eingabequelle wurde verändert: {paths[key]}",
                    (key,),
                )
            )
    return findings


def integer(document: Mapping[str, Any], *path: str) -> int | None:
    value: Any = document
    for part in path:
        if not isinstance(value, Mapping) or part not in value:
            return None
        value = value[part]
    if isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def floating(document: Mapping[str, Any], *path: str) -> float | None:
    value: Any = document
    for part in path:
        if not isinstance(value, Mapping) or part not in value:
            return None
        value = value[part]
    if isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def validate_manifest(root: Path, manifest: Mapping[str, Any], findings: list[Finding]) -> bool:
    items = manifest.get("files")
    if not isinstance(items, list):
        findings.append(Finding("error", "MANIFEST_FILES_INVALID", "Manifestfeld `files` ist keine Liste.", ("manifest",)))
        return False
    valid = integer(manifest, "file_count") == len(items)
    if not valid:
        findings.append(
            Finding(
                "error",
                "MANIFEST_SELF_COUNT_MISMATCH",
                f"Manifest nennt {integer(manifest, 'file_count')} Dateien, enthält aber {len(items)} Einträge.",
                ("manifest",),
            )
        )
    seen: set[str] = set()
    for index, item in enumerate(items):
        if not isinstance(item, Mapping):
            findings.append(Finding("error", "MANIFEST_ITEM_INVALID", f"Eintrag {index} ist kein Objekt.", ("manifest",)))
            valid = False
            continue
        relative = str(item.get("path") or "")
        try:
            path = safe_join(root, relative)
        except EvidenceError as exc:
            findings.append(Finding("error", "MANIFEST_PATH_UNSAFE", str(exc), ("manifest",)))
            valid = False
            continue
        if relative in seen:
            findings.append(Finding("error", "MANIFEST_PATH_DUPLICATE", f"Doppelter Manifestpfad: {relative}", ("manifest",)))
            valid = False
            continue
        seen.add(relative)
        if not path.is_file() or path.is_symlink():
            findings.append(Finding("error", "MANIFEST_FILE_MISSING", f"Manifestdatei fehlt oder ist ein Link: {relative}", ("manifest",)))
            valid = False
            continue
        if int(item.get("size", -1)) != path.stat().st_size:
            findings.append(Finding("error", "MANIFEST_SIZE_MISMATCH", f"Größe stimmt nicht: {relative}", ("manifest",)))
            valid = False
        expected_hash = str(item.get("sha256") or "")
        if expected_hash and expected_hash != sha256_file(path):
            findings.append(Finding("error", "MANIFEST_HASH_MISMATCH", f"SHA-256 stimmt nicht: {relative}", ("manifest",)))
            valid = False
    return valid


def load_ci_snapshot(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {"schema_version": 1, "status": "unknown", "source": "not supplied", "checks": []}
    return read_json(path)


def _github_get(url: str, token: str | None) -> dict[str, Any]:
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "videobatch-release-readiness/1", "X-GitHub-Api-Version": "2022-11-28"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            value = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise EvidenceError(f"GitHub-Leseabfrage fehlgeschlagen: {exc}") from exc
    if not isinstance(value, dict):
        raise EvidenceError("GitHub-Antwort ist kein Objekt.")
    return value


def fetch_github_ci(repository: str, sha: str, token: str | None) -> dict[str, Any]:
    if not re.fullmatch(r"[A-Za-z0-9._-]+/[A-Za-z0-9._-]+", repository):
        raise EvidenceError("Unnültiger GitHub-Repositoryname.")
    if not re.fullmatch(r"[0-9a-fA-F]{7,40}", sha):
        raise EvidenceError("Unültige GitHub-Commit-SHA.")
    base = f"https://api.github.com/repos/{repository}"
    checks_payload = _github_get(f"{base}/commits/{sha}/check-runs?per_page=100", token)
    runs_payload = _github_get(f"{base}/actions/runs?head_sha={sha}&per_page=100", token)
    checks: list[dict[str, Any]] = []
    for check in checks_payload.get("check_runs", []):
        if isinstance(check, Mapping):
            raw = check.get("conclusion") or check.get("status")
            checks.append({"name": str(check.get("name") or "check-run"), "status": normalize_status(raw), "raw_status": str(raw), "url": str(check.get("html_url") or ""), "kind": "check-run"})
    for run in runs_payload.get("workflow_runs", []):
        if isinstance(run, Mapping):
            raw = run.get("conclusion") or run.get("status")
            checks.append({"name": str(run.get("name") or "workflow-run"), "status": normalize_status(raw), "raw_status": str(raw), "url": str(run.get("html_url") or ""), "kind": "workflow-run"})
    statuses = [check["status"] for check in checks]
    status = "fail" if "fail" in statuses else "running" if "running" in statuses else "open" if any(state in {"open", "unknown"} for state in statuses) or not checks else "pass"
    return {"schema_version": 1, "status": status, "source": "GitHub REST API", "repository": repository, "sha": sha, "checks": checks}


def compare_value(findings: list[Finding], code: str, label: str, expected: Any, actual: Any, sources: tuple[str, ...]) -> None:
    if expected != actual:
        findings.append(Finding("error", code, f"{label} stimmt nicht: kanonisch {expected!r} · abgeleitet {actual!r}", sources))


def readme_release_status(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    version_match = re.search(r"# [\w\-] [\w\-]*(¥)? ([0-9]+\.[0-9]+\.[0-9]+-rc[0-9]+)", text, flags=re.IGNORECASE)
    test_match = re.search(r"([0-9]+)/([0-9]+) automatisierte Tests bestanden", text)
    manifest_match = re.search(r"Release-Manifest_`? tragen `?([0-9]+)`Dateien", text)
    blockers_match = re.search("`stable_blockers`? umfasst `g?([0-9]+)`", text)
    return {
        "version": version_match.group(1) if version_match else None,
        "tests_passed": int(test_match.group(1)) if test_match else None,
        "manifest_files": int(manifest_match.group(1)) if manifest_match else None,
        "blockers": int(blockers_match.group(1)) if blockers_match else None,
    }


def analyze(root: Path, documents: Mapping[str, Mapping[str, Any]], ci: Mapping[str, Any]) -> tuple[list[Finding], list[Gate]]:
    findings: list[Finding] = []
    evidence = documents["evidence"]
    manifest = documents["manifest"]
    development = documents["development"]
    quality = documents["quality"]
    release_files = documents["release_files"]
    build = documents["build"]
    product = evidence.get("product") if isinstance(evidence.get("product"), Mapping) else {}
    canonical_manifest = evidence.get("manifest") if isinstance(evidence.get("manifest"), Mapping) else {}
    tests = evidence.get("tests") if isinstance(evidence.get("tests"), Mapping) else {}
    canonical_files = evidence.get("release_files") if isinstance(evidence.get("release_files"), Mapping) else {}
    gates_raw = evidence.get("stable_gates") if isinstance(evidence.get("stable_gates"), list) else []

    manifest_valid = validate_manifest(root, manifest, findings)
    canonical_blockers = [str(item.get("label") or item.get("id") or "Unbenannt") for item in gates_raw if isinstance(item, Mapping) and normalize_status(item.get("status")) != "pass"]

    compare_value(findings, "DEVELOPMENT_VERSION_DRIFT", "Entwicklungsstatus-Version", product.get("version"), development.get("version"), ("evidence", "development"))
    compare_value(findings, "QUALITY_VERSION_DRIFT", "Qualitätsstatus-Version", product.get("version"), quality.get("build"), ("evidence", "quality"))
    compare_value(findings, "BUILD_VERSION_DRIFT", "Buildbericht-Version", product.get("version"), build.get("version"), ("evidence", "build"))
    compare_value(findings, "RELEASE_FILE_VERSION_DRIFT", "Release-Dateistatus-Version", product.get("version"), release_files.get("version"), ("evidence", "release_files"))
    compare_value(findings, "MANIFEST_COUNT_DRIFT", "Manifest-Dateizahl", canonical_manifest.get("file_count"), manifest.get("file_count"), ("evidence", "manifest"))
    compare_value(findings, "QUALITY_MANIFEST_DRIFT", "Qualitätsstatus-Manifestzahl", canonical_manifest.get("file_count"), integer(quality, "internal_gates", "release_manifest_files"), ("evidence", "quality"))
    compare_value(findings, "BUILD_MANIFEST_DRIFT", "Buildbericht-Manifestzahl", canonical_manifest.get("file_count"), build.get("release_manifest_files"), ("evidence", "build"))
    compare_value(findings, "TEST_COUNT_DRIFT", "Testzahl Entwicklungs-/Qualitätsstatus", tests.get("passed"), integer(quality, "internal_gates", "tests", "passed"), ("evidence", "quality"))
    compare_value(findings, "BUILD_TEST_COUNT_DRIFT", "Testzahl Buildbericht", tests.get("passed"), integer(build, "tests", "passed"), ("evidence", "build"))
    compare_value(findings, "STABLE_READY_DRIFT", "Stable-Bereitschaft Entwicklung", evidence.get("stable_ready"), development.get("stable_ready"), ("evidence", "development"))
    compare_value(findings, "QUALITY_STABLE_READY_DRIFT", "Stable-Bereitschaft Qualität", evidence.get("stable_ready"), quality.get("stable_ready"), ("evidence", "quality"))
    compare_value(findings, "BUILD_STABLE_READY_DRIFT", "Stable-Bereitschaft Build", evidence.get("stable_ready"), build.get("stable_ready"), ("evidence", "build"))
    compare_value(findings, "BLOCKER_DRIFT", "Stable-Blockerliste", canonical_blockers, development.get("stable_blockers"), ("evidence", "development"))
    compare_value(findings, "RELEASE_READY_LIST_DRIFT", "Releasefertige Dateien", canonical_files.get("ready"), release_files.get("ready"), ("evidence", "release_files"))
    compare_value(findings, "RELEASE_UNFINISHED_LIST_DRIFT", "Unfertige Dateien", canonical_files.get("unfinished"), release_files.get("unfinished"), ("evidence", "release_files"))

    readme = readme_release_status(root / "README.md")
    compare_value(findings, "README_VERSION_DRIFT", "README-Version", product.get("version"), readme["version"], ("evidence", "readme"))
    compare_value(findings, "README_TEST_COUNT_DRIFT", "README-Testzahl", tests.get("passed"), readme["tests_passed"], ("evidence", "readme"))
    compare_value(findings, "README_MANIFEST_COUNT_DRIFT", "README-Manifestzahl", canonical_manifest.get("file_count"), readme["manifest_files"], ("evidence", "readme"))
    compare_value(findings, "README_BLOCKER_DRIFT", "README-Blockerliste", canonical_blockers, readme["blockers"], ("evidence", "readme"))

    gates: list[Gate] = [
        Gate(
            "automated-tests",
            "Automatisierte Tests",
            "pass" if int(tests.get("passed", 0)) > 0 and int(tests.get("failed", 1)) == 0 else "fail",
            f"{tests.get('passed', 0)} bestanden · {tests.get('failed', 0)} fehlgeschlagen · {tests.get('skipped', 0)} übersprungen",
            "RELEASE_EVIDENCE.json",
        ),
        Gate(
            "release-manifest",
            "Release-Manifest",
            "pass" if manifest_valid and canonical_manifest.get("file_count") == manifest.get("file_count") else "fail",
            f"{manifest.get('file_count')} Dateien · SHA-256 und Größen geprüft",
            "RELEASE_EVIDENCE.json + RELEASE_MANIFEST.json",
        ),
        Gate(
            "kubuntu-ci-matrix",
            "Kubuntu-CI-Matrix",
            normalize_status(evidence.get("matrix", {}).get("status")),
            f"{evidence.get('matrix', {}).get('passed_targets')}/{evidence.get('matrix', {}).get('total_targets')} Kombinationen · Run {evidence.get('matrix', {}).get('workflow_run_id')}",
            "RELEASE_EVIDENCE.json",
        ),
    ]
    for gate in gates_raw:
        if isinstance(gate, Mapping):
            gates.append(
                Gate(
                    str(gate.get("id") or "unknown"),
                    str(gate.get("label") or gate.get("id") or "Unbenannt"),
                    normalize_status(gate.get("status")),
                    str(gate.get("reason") or ""),
                    "RELEASE_EVIDENCE.json",
                )
            )
    checks = ci.get("checks") if isinstance(ci.get("checks"), list) else []
    gates.append(
        Gate(
            "ci",
            "CI-Status des geprüften Commits",
            normalize_status(ci.get("status")),
            f"{len(checks)} Checks · Quelle: {ci.get('source', 'unknown')}",
            "CI-Snapshot/GitHub API",
        )
    )

    if any(item.severity == "error" for item in findings):
        findings.append(
            Finding(
                "error",
                "DERIVED_EVIDENCE_DRIFT",
                "Mindestens ein abgeleitetes Release-Datei stimmt nicht mit RELEASE_EVIDENCE.json überein.",
                ("evidence",),
            )
        )
    if normalize_status(ci.get("status")) in {"unknown", "running", "open"}:
        findings.append(
            Finding(
                "warning",
                "CI_NOT_FINAL",
                f"CI ist noch nicht endgültig: {normalize_status(ci.get('status'))}",
                ("ci",),
            )
        )
    elif normalize_status(ci.get("status")) == "fail":
        findings.append(Finding("error", "CI_FAILED", "CI des geprüften Commits ist fehlgeschlagen.", ("ci",)))

    return findings, gates


def result_document(
    documents: Mapping[str, Mapping[str, Any]],
    ci: Mapping[str, Any],
    findings: list[Finding],
    gates: list[Gate],
    input_hashes: Mapping[str, str],
    source_sha: str | None,
    generated_at: str,
) -> dict[str, Any]:
    errors = sum(1 for item in findings if item.severity == "error")
    warnings = sum(1 for item in findings if item.severity == "warning")
    required = [gate for gate in gates if gate.required]
    passed = sum(1 for gate in required if gate.status == "pass")
    if errors:
        overall = "red"
    elif passed == len(required):
        overall = "green"
    else:
        overall = "yellow"
    readiness = 0 if not required else round((passed / len(required)) * 100)
    evidence = documents["evidence"]
    product = evidence.get("product") if isinstance(evidence.get("product"), Mapping) else {}
    return {
        "schema_version": 2,
        "generated_at": generated_at,
        "overall_status": overall,
        "readiness_percent": readiness,
        "read_only_inputs_verified": not any(item.code == "INPUT_MUTATED" for item in findings),
        "release": {
            "name": product.get("name"),
            "version": product.get("version"),
            "channel": product.get("channel"),
            "source_sha": source_sha or evidence.get("provenance", {}).get("verified_source_commit"),
            "canonical_source": "diagnostics/release_readiness/RELEASE_EVIDENCE.json",
        },
        "summary": {
            "gates_total": len(required),
            "gates_passed": passed,
            "errors": errors,
            "warnings": warnings,
        },
        "gates": [asdict(gate) for gate in gates],
        "findings": [asdict(item) for item in findings],
        "ci": dict(ci),
        "input_sha256": dict(input_hashes),
    }
