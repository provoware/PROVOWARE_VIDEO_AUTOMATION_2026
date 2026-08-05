from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

from .paths import state_dir

REPORT_SCHEMA_VERSION = 1
RETRY_SCHEMA_VERSION = 1
JOURNAL_SCHEMA_VERSION = 2


@dataclass(frozen=True, slots=True)
class SourceSnapshot:
    kind: str
    path: str
    exists: bool
    valid: bool
    sha256: str
    size: int
    schema_version: int | None
    error: str


@dataclass(frozen=True, slots=True)
class ConsistencyFinding:
    severity: str
    code: str
    source: str
    operation_id: str
    job_id: str
    message: str


@dataclass(frozen=True, slots=True)
class ConsistencyReport:
    schema_version: int
    jobs_root: str
    retry_path: str
    active_dir: str
    history_dir: str
    source_files: int
    valid_sources: int
    invalid_sources: int
    retry_entries: int
    active_journals: int
    history_journals: int
    findings: tuple[ConsistencyFinding, ...]
    sources: tuple[SourceSnapshot, ...]

    @property
    def status(self) -> str:
        if self.invalid_sources or any(item.severity == "error" for item in self.findings):
            return "red"
        if self.findings:
            return "yellow"
        return "green"

    def as_payload(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["status"] = self.status
        payload["finding_count"] = len(self.findings)
        return payload


def default_jobs_root() -> Path:
    return state_dir() / "jobs"


def _safe_int(value: object, default: int = 0) -> int:
    if not isinstance(value, (str, bytes, bytearray, int, float)):
        return default
    try:
        return int(value)
    except (TypeError, ValueError, OverflowError):
        return default


def _job_identity(item: dict[str, Any]) -> str:
    sequence = item.get("media_sequence", [])
    sequence_values = sequence if isinstance(sequence, list) else []
    stable = {
        "audio": str(item.get("audio", "")),
        "media": str(item.get("media", "")),
        "media_sequence": [str(value) for value in sequence_values],
        "output": str(item.get("output", "")),
    }
    encoded = json.dumps(stable, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _read_json(path: Path, *, kind: str, expected_schema: int) -> tuple[SourceSnapshot, dict[str, Any] | None]:
    try:
        exists = path.is_file()
    except OSError:
        exists = False
    if not exists:
        return SourceSnapshot(kind, str(path), False, True, "", 0, None, ""), None
    try:
        raw = path.read_bytes()
    except OSError as exc:
        return SourceSnapshot(kind, str(path), True, False, "", 0, None, f"Datei nicht lesbar: {exc}"), None
    digest = hashlib.sha256(raw).hexdigest()
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        return SourceSnapshot(kind, str(path), True, False, digest, len(raw), None, f"Ungültiges JSON: {exc}"), None
    if not isinstance(payload, dict):
        return SourceSnapshot(kind, str(path), True, False, digest, len(raw), None, "JSON-Wurzel ist kein Objekt."), None
    schema = _safe_int(payload.get("schema_version"), -1)
    if schema != expected_schema:
        return (
            SourceSnapshot(
                kind,
                str(path),
                True,
                False,
                digest,
                len(raw),
                schema,
                f"Nicht unterstützte Schema-Version {schema}; erwartet {expected_schema}.",
            ),
            None,
        )
    return SourceSnapshot(kind, str(path), True, True, digest, len(raw), schema, ""), payload


def _json_files(directory: Path) -> tuple[Path, ...]:
    try:
        if not directory.is_dir():
            return ()
        return tuple(sorted(path for path in directory.glob("*.json") if path.is_file()))
    except OSError:
        return ()


def _input_paths(item: dict[str, Any]) -> tuple[tuple[str, Path], ...]:
    values: list[tuple[str, Path]] = []
    audio = str(item.get("audio", ""))
    if audio:
        values.append(("Audio", Path(audio).expanduser()))
    sequence = item.get("media_sequence", [])
    if isinstance(sequence, list) and sequence:
        values.extend((f"Medium {index}", Path(str(value)).expanduser()) for index, value in enumerate(sequence, 1))
    else:
        media = str(item.get("media", ""))
        if media:
            values.append(("Medium", Path(media).expanduser()))
    return tuple(values)


def _missing_inputs(item: dict[str, Any]) -> tuple[str, ...]:
    missing: list[str] = []
    for label, path in _input_paths(item):
        try:
            valid = path.is_file()
        except OSError:
            valid = False
        if not valid:
            missing.append(f"{label}: {path}")
    return tuple(missing)


def _load_retry(
    retry: Path,
    sources: list[SourceSnapshot],
    findings: list[ConsistencyFinding],
) -> list[dict[str, Any]]:
    snapshot, payload = _read_json(retry, kind="retry", expected_schema=RETRY_SCHEMA_VERSION)
    sources.append(snapshot)
    if payload is None:
        return []
    raw_entries = payload.get("entries", [])
    if not isinstance(raw_entries, list):
        findings.append(
            ConsistencyFinding("error", "retry_entries_invalid", str(retry), "", "", "Feld 'entries' ist keine Liste.")
        )
        return []
    entries: list[dict[str, Any]] = []
    for index, item in enumerate(raw_entries):
        if not isinstance(item, dict) or not str(item.get("job_id", "")):
            findings.append(
                ConsistencyFinding(
                    "error",
                    "retry_entry_invalid",
                    str(retry),
                    "",
                    "",
                    f"Ungültiger Wiederanlaufeintrag an Position {index}.",
                )
            )
        else:
            entries.append(item)
    return entries


def _load_journals(
    active: Path,
    history: Path,
    sources: list[SourceSnapshot],
) -> list[tuple[str, Path, dict[str, Any]]]:
    journals: list[tuple[str, Path, dict[str, Any]]] = []
    for kind, directory in (("active", active), ("history", history)):
        for path in _json_files(directory):
            snapshot, payload = _read_json(path, kind=kind, expected_schema=JOURNAL_SCHEMA_VERSION)
            sources.append(snapshot)
            if payload is not None:
                journals.append((kind, path, payload))
    return journals


def _analyze_retry_entries(
    entries: Iterable[dict[str, Any]],
    retry: Path,
    findings: list[ConsistencyFinding],
) -> dict[str, list[dict[str, Any]]]:
    by_job: dict[str, list[dict[str, Any]]] = {}
    for item in entries:
        job_id = str(item.get("job_id", ""))
        group = by_job.setdefault(job_id, [])
        group.append(item)
        operation_id = str(item.get("operation_id", ""))
        attempts = max(0, _safe_int(item.get("attempts"), 0))
        maximum = max(1, _safe_int(item.get("max_attempts"), 1))
        allowed = bool(item.get("retry_allowed"))
        state = str(item.get("state", ""))
        if len(group) > 1:
            findings.append(
                ConsistencyFinding(
                    "error",
                    "duplicate_retry_job_id",
                    str(retry),
                    operation_id,
                    job_id,
                    "Auftrags-ID kommt mehrfach in der Wiederanlaufliste vor.",
                )
            )
        if state == "limit_reached" and allowed:
            findings.append(
                ConsistencyFinding(
                    "error",
                    "retry_limit_contradiction",
                    str(retry),
                    operation_id,
                    job_id,
                    "Status 'limit_reached' widerspricht retry_allowed=true.",
                )
            )
        if attempts >= maximum and allowed:
            findings.append(
                ConsistencyFinding(
                    "error",
                    "retry_attempt_contradiction",
                    str(retry),
                    operation_id,
                    job_id,
                    "Versuchslimit ist erreicht, Eintrag ist aber weiter freigegeben.",
                )
            )
        for missing in _missing_inputs(item):
            findings.append(
                ConsistencyFinding(
                    "warning",
                    "missing_retry_input",
                    str(retry),
                    operation_id,
                    job_id,
                    f"Fehlende Eingabe im Wiederanlaufeintrag: {missing}",
                )
            )
    return by_job


def _journal_state_findings(
    kind: str,
    path: Path,
    payload: dict[str, Any],
    findings: list[ConsistencyFinding],
) -> None:
    operation_id = str(payload.get("operation_id", ""))
    state = str(payload.get("state", ""))
    if kind == "active" and state != "running":
        findings.append(
            ConsistencyFinding(
                "error",
                "active_terminal_state",
                str(path),
                operation_id,
                "",
                f"Aktives Journal hat terminalen oder unbekannten Zustand {state!r}.",
            )
        )
    if kind == "history" and state == "running":
        findings.append(
            ConsistencyFinding(
                "error",
                "history_running_state",
                str(path),
                operation_id,
                "",
                "Verlaufsjournal ist weiterhin als laufend markiert.",
            )
        )


def _analyze_journal_jobs(
    kind: str,
    path: Path,
    payload: dict[str, Any],
    findings: list[ConsistencyFinding],
    journal_jobs: dict[str, list[tuple[str, Path, dict[str, Any], dict[str, Any]]]],
) -> None:
    operation_id = str(payload.get("operation_id", ""))
    jobs = payload.get("jobs", [])
    if not isinstance(jobs, list):
        findings.append(
            ConsistencyFinding("error", "journal_jobs_invalid", str(path), operation_id, "", "Feld 'jobs' ist keine Liste.")
        )
        return
    seen: set[str] = set()
    for position, item in enumerate(jobs):
        if not isinstance(item, dict):
            findings.append(
                ConsistencyFinding(
                    "error",
                    "journal_job_invalid",
                    str(path),
                    operation_id,
                    "",
                    f"Ungültiger Journaleintrag an Position {position}.",
                )
            )
            continue
        job_id = _job_identity(item)
        if job_id in seen:
            findings.append(
                ConsistencyFinding(
                    "error",
                    "duplicate_journal_job",
                    str(path),
                    operation_id,
                    job_id,
                    "Derselbe Auftrag kommt mehrfach im Journal vor.",
                )
            )
        seen.add(job_id)
        journal_jobs.setdefault(job_id, []).append((kind, path, payload, item))
        job_state = str(item.get("state", ""))
        if kind == "history" and str(payload.get("state", "")) == "completed" and job_state != "completed":
            findings.append(
                ConsistencyFinding(
                    "error",
                    "completed_history_has_open_job",
                    str(path),
                    operation_id,
                    job_id,
                    f"Abgeschlossenes Verlaufsjournal enthält Auftrag im Zustand {job_state!r}.",
                )
            )
        for missing in _missing_inputs(item):
            findings.append(
                ConsistencyFinding(
                    "warning",
                    "missing_journal_input",
                    str(path),
                    operation_id,
                    job_id,
                    f"Fehlende Journaleingabe: {missing}",
                )
            )


def _analyze_journals(
    journals: Iterable[tuple[str, Path, dict[str, Any]]],
    findings: list[ConsistencyFinding],
) -> tuple[
    dict[str, list[tuple[str, Path, dict[str, Any]]]],
    dict[str, list[tuple[str, Path, dict[str, Any], dict[str, Any]]]],
]:
    operations: dict[str, list[tuple[str, Path, dict[str, Any]]]] = {}
    journal_jobs: dict[str, list[tuple[str, Path, dict[str, Any], dict[str, Any]]]] = {}
    for kind, path, payload in journals:
        operation_id = str(payload.get("operation_id", ""))
        operations.setdefault(operation_id, []).append((kind, path, payload))
        _journal_state_findings(kind, path, payload, findings)
        _analyze_journal_jobs(kind, path, payload, findings, journal_jobs)
    return operations, journal_jobs


def _analyze_operations(
    operations: dict[str, list[tuple[str, Path, dict[str, Any]]]],
    findings: list[ConsistencyFinding],
) -> None:
    for operation_id, records in operations.items():
        if not operation_id:
            for kind, path, _payload in records:
                findings.append(
                    ConsistencyFinding(
                        "error",
                        "missing_operation_id",
                        str(path),
                        "",
                        "",
                        f"{kind.title()}-Journal enthält keine Operations-ID.",
                    )
                )
            continue
        if len(records) <= 1:
            continue
        kinds = {kind for kind, _path, _payload in records}
        code = "operation_active_and_history" if kinds == {"active", "history"} else "duplicate_operation_id"
        findings.append(
            ConsistencyFinding(
                "error",
                code,
                " | ".join(str(path) for _kind, path, _payload in records),
                operation_id,
                "",
                "Operations-ID kommt in mehreren Journaldateien vor.",
            )
        )


def _cross_check_jobs(
    retry: Path,
    retry_by_job: dict[str, list[dict[str, Any]]],
    journal_jobs: dict[str, list[tuple[str, Path, dict[str, Any], dict[str, Any]]]],
    findings: list[ConsistencyFinding],
) -> None:
    for job_id, retry_items in retry_by_job.items():
        records = journal_jobs.get(job_id, [])
        operation_id = str(retry_items[-1].get("operation_id", ""))
        if not records:
            findings.append(
                ConsistencyFinding(
                    "warning",
                    "orphan_retry_entry",
                    str(retry),
                    operation_id,
                    job_id,
                    "Wiederanlaufeintrag besitzt keinen zugehörigen aktiven oder historischen Journalauftrag.",
                )
            )
        elif any(kind == "history" and str(item.get("state", "")) == "completed" for kind, _path, _payload, item in records):
            findings.append(
                ConsistencyFinding(
                    "error",
                    "retry_for_completed_job",
                    str(retry),
                    operation_id,
                    job_id,
                    "Erfolgreich abgeschlossener Auftrag steht weiterhin in der Wiederanlaufliste.",
                )
            )

    retry_ids = set(retry_by_job)
    for job_id, records in journal_jobs.items():
        unfinished = [record for record in records if str(record[3].get("state", "")) in {"pending", "running", "failed"}]
        if not unfinished or job_id in retry_ids:
            continue
        kind, path, payload, item = unfinished[-1]
        findings.append(
            ConsistencyFinding(
                "warning",
                "unfinished_journal_without_retry",
                str(path),
                str(payload.get("operation_id", "")),
                job_id,
                f"{kind.title()}-Journalauftrag im Zustand {item.get('state')!r} fehlt in der Wiederanlaufliste.",
            )
        )


def inspect_recovery_consistency(
    jobs_root: Path | None = None,
    *,
    retry_path: Path | None = None,
    active_dir: Path | None = None,
    history_dir: Path | None = None,
) -> ConsistencyReport:
    """Compare retry and journal state without writing, repairing, moving or deleting files."""
    root = Path(jobs_root) if jobs_root is not None else default_jobs_root()
    root = root.expanduser()
    retry = (Path(retry_path) if retry_path is not None else root / "retry_queue.json").expanduser()
    active = (Path(active_dir) if active_dir is not None else root / "active").expanduser()
    history = (Path(history_dir) if history_dir is not None else root / "history").expanduser()
    sources: list[SourceSnapshot] = []
    findings: list[ConsistencyFinding] = []
    retry_entries = _load_retry(retry, sources, findings)
    journals = _load_journals(active, history, sources)
    retry_by_job = _analyze_retry_entries(retry_entries, retry, findings)
    operations, journal_jobs = _analyze_journals(journals, findings)
    _analyze_operations(operations, findings)
    _cross_check_jobs(retry, retry_by_job, journal_jobs, findings)
    invalid_sources = sum(source.exists and not source.valid for source in sources)
    return ConsistencyReport(
        REPORT_SCHEMA_VERSION,
        str(root),
        str(retry),
        str(active),
        str(history),
        sum(source.exists for source in sources),
        sum(source.exists and source.valid for source in sources),
        invalid_sources,
        len(retry_entries),
        sum(kind == "active" for kind, _path, _payload in journals),
        sum(kind == "history" for kind, _path, _payload in journals),
        tuple(findings),
        tuple(sources),
    )


def _human(report: ConsistencyReport) -> str:
    lines = [
        "WIEDERANLAUF-/JOURNAL-KONSISTENZ · vollständig lesend",
        f"Status: {report.status.upper()}",
        f"Jobs-Verzeichnis: {report.jobs_root}",
        f"Quellen: {report.source_files} · gültig: {report.valid_sources} · ungültig: {report.invalid_sources}",
        f"Wiederanlauf: {report.retry_entries} · aktive Journale: {report.active_journals} · Verlauf: {report.history_journals}",
        f"Befunde: {len(report.findings)}",
    ]
    for index, finding in enumerate(report.findings, 1):
        lines.extend(
            [
                "",
                f"[{index}] {finding.severity.upper()} · {finding.code}",
                f"    Quelle: {finding.source or '-'}",
                f"    Operation: {finding.operation_id or '-'} · Auftrag: {finding.job_id or '-'}",
                f"    Befund: {finding.message}",
            ]
        )
    lines.extend(
        [
            "",
            "Schreibschutz: Keine Datei wurde repariert, verschoben, gestartet, erzeugt oder gelöscht.",
        ]
    )
    return "\n".join(lines)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Wiederanlauf- und Journalzustände vollständig lesend vergleichen.")
    parser.add_argument("--jobs-root", type=Path)
    parser.add_argument("--retry-path", type=Path)
    parser.add_argument("--active-dir", type=Path)
    parser.add_argument("--history-dir", type=Path)
    parser.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    report = inspect_recovery_consistency(
        args.jobs_root,
        retry_path=args.retry_path,
        active_dir=args.active_dir,
        history_dir=args.history_dir,
    )
    if args.json:
        print(json.dumps(report.as_payload(), ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(_human(report))
    if report.invalid_sources:
        return 2
    return 1 if report.findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
