from __future__ import annotations

import hashlib
import json
import time
import zipfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .recovery_consistency import ConsistencyReport, inspect_recovery_consistency
from .safe_io import atomic_write_json
from .transaction_store import (
    TransactionError,
    TransactionHealth,
    inspect_transaction_state,
    prune_orphan_revisions,
    recover_pending_transaction,
    rollback_pending_transaction,
    transaction_audit_timeline,
)

POLICY_SCHEMA_VERSION = 1
MAX_ATTEMPTS_PER_SIGNATURE = 3
MAX_ACTIONS_PER_RUN = 5
RETRY_WINDOW_SECONDS = 3600


@dataclass(frozen=True, slots=True)
class RecoverySignal:
    domain: str
    severity: str
    code: str
    message: str


@dataclass(frozen=True, slots=True)
class RecoveryDecision:
    action: str
    severity: str
    reason: str
    signature: str
    automatic: bool = True


@dataclass(frozen=True, slots=True)
class RecoveryReport:
    schema_version: int
    generated_at_unix_ns: int
    health_score: int
    health_status: str
    decision: RecoveryDecision
    signals: tuple[RecoverySignal, ...]
    correlated_domains: tuple[str, ...]
    actions_executed: tuple[str, ...]
    budget_exhausted: bool
    transaction_health: TransactionHealth
    job_consistency_status: str
    diagnostic_package: str = ""

    def as_payload(self) -> dict[str, Any]:
        return asdict(self)


def _policy_dir(root: Path) -> Path:
    return root / ".videobatch-recovery"


def _budget_path(root: Path) -> Path:
    return _policy_dir(root) / "budget.json"


def _diagnostics_dir(root: Path) -> Path:
    return _policy_dir(root) / "diagnostics"


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _signature(signals: list[RecoverySignal]) -> str:
    stable = [(item.domain, item.severity, item.code) for item in signals]
    return hashlib.sha256(_canonical(stable)).hexdigest()[:24]


def _read_budget(root: Path) -> dict[str, Any]:
    path = _budget_path(root)
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"schema_version": POLICY_SCHEMA_VERSION, "signatures": {}}
    if not isinstance(value, dict) or int(value.get("schema_version", 0) or 0) != POLICY_SCHEMA_VERSION:
        return {"schema_version": POLICY_SCHEMA_VERSION, "signatures": {}}
    if not isinstance(value.get("signatures"), dict):
        value["signatures"] = {}
    return value


def _budget_allows(root: Path, signature: str) -> bool:
    state = _read_budget(root)
    record = state["signatures"].get(signature, {})
    now = time.time()
    first = float(record.get("window_started", now) or now)
    attempts = int(record.get("attempts", 0) or 0)
    if now - first > RETRY_WINDOW_SECONDS:
        return True
    return attempts < MAX_ATTEMPTS_PER_SIGNATURE


def _consume_budget(root: Path, signature: str) -> None:
    directory = _policy_dir(root)
    directory.mkdir(parents=True, exist_ok=True)
    state = _read_budget(root)
    now = time.time()
    record = state["signatures"].get(signature, {})
    first = float(record.get("window_started", now) or now)
    attempts = int(record.get("attempts", 0) or 0)
    if now - first > RETRY_WINDOW_SECONDS:
        first, attempts = now, 0
    state["signatures"][signature] = {"window_started": first, "attempts": attempts + 1, "last_attempt": now}
    atomic_write_json(_budget_path(root), state)


def _config_signal(config_path: Path | None) -> list[RecoverySignal]:
    if config_path is None or not config_path.exists():
        return []
    try:
        value = json.loads(config_path.read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            raise ValueError("root")
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError):
        return [RecoverySignal("config", "error", "config_corrupt", "Konfiguration ist nicht als gültiges JSON-Objekt lesbar.")]
    return []


def _project_signal(project_path: Path | None) -> list[RecoverySignal]:
    if project_path is None or not project_path.exists():
        return []
    try:
        value = json.loads(project_path.read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            raise ValueError("root")
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError):
        return [RecoverySignal("project", "critical", "project_corrupt", "Projektzustand ist nicht als gültiges JSON-Objekt lesbar.")]
    return []


def _backup_signal(backup_dir: Path | None) -> list[RecoverySignal]:
    if backup_dir is None:
        return []
    history = backup_dir / "history.json"
    meta = backup_dir / "history.meta.json"
    if not history.exists() and not meta.exists():
        return []
    try:
        items = json.loads(history.read_text(encoding="utf-8"))
        metadata = json.loads(meta.read_text(encoding="utf-8"))
        if not isinstance(items, list) or not isinstance(metadata, dict):
            raise ValueError("shape")
        digest = hashlib.sha256(json.dumps(items, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
        if int(metadata.get("schema_version", 0) or 0) != 1 or int(metadata.get("count", -1)) != len(items) or str(metadata.get("history_sha256", "")) != digest:
            raise ValueError("integrity")
    except (OSError, UnicodeError, json.JSONDecodeError, TypeError, ValueError):
        return [RecoverySignal("backup", "error", "backup_history_inconsistent", "Backuphistorie und Integritätsmetadaten sind nicht konsistent rekonstruierbar dargestellt.")]
    return []


def _transaction_signals(health: TransactionHealth) -> list[RecoverySignal]:
    signals: list[RecoverySignal] = []
    if health.pending:
        corrupt = any("Beschädigtes Pending-Journal" in issue for issue in health.issues)
        signals.append(RecoverySignal("transaction", "critical" if corrupt else "warning", "pending_corrupt" if corrupt else "pending_valid", health.issues[0] if health.issues else "Pending-Transaktion erkannt."))
    if health.orphan_revisions:
        signals.append(RecoverySignal("transaction", "warning", "orphan_revisions", f"{len(health.orphan_revisions)} verwaiste Revisionen erkannt."))
    if health.quarantined_count:
        signals.append(RecoverySignal("transaction", "warning", "quarantine_present", f"{health.quarantined_count} Quarantäneartefakt(e) vorhanden."))
    for issue in health.issues:
        if "Pending-Journal" not in issue and "verwaiste" not in issue:
            signals.append(RecoverySignal("transaction", "error", "transaction_metadata", issue))
    return signals


def _job_signals(report: ConsistencyReport | None) -> list[RecoverySignal]:
    if report is None:
        return []
    signals: list[RecoverySignal] = []
    if report.invalid_sources:
        signals.append(RecoverySignal("jobs", "critical", "invalid_job_sources", f"{report.invalid_sources} ungültige Journal-/Retry-Quelle(n)."))
    errors = sum(1 for item in report.findings if item.severity == "error")
    warnings = len(report.findings) - errors
    if errors:
        signals.append(RecoverySignal("jobs", "error", "job_consistency_errors", f"{errors} harte Wiederanlauf-/Journal-Inkonsistenz(en)."))
    if warnings:
        signals.append(RecoverySignal("jobs", "warning", "job_consistency_warnings", f"{warnings} Wiederanlaufwarnung(en)."))
    return signals


def _health_score(signals: list[RecoverySignal]) -> int:
    penalty = {"info": 2, "warning": 8, "error": 20, "critical": 35}
    domains = {item.domain for item in signals if item.severity in {"error", "critical"}}
    score = 100 - sum(penalty.get(item.severity, 10) for item in signals)
    if len(domains) >= 2:
        score -= min(20, 5 * (len(domains) - 1))
    return max(0, min(100, score))


def _severity(signals: list[RecoverySignal]) -> str:
    order = {"info": 0, "warning": 1, "error": 2, "critical": 3}
    return max((item.severity for item in signals), key=lambda value: order.get(value, 0), default="info")


def decide_recovery(signals: list[RecoverySignal], *, budget_allowed: bool) -> RecoveryDecision:
    sig = _signature(signals)
    codes = {item.code for item in signals}
    severity = _severity(signals)
    if "pending_corrupt" in codes:
        return RecoveryDecision("QUARANTINE", "critical", "Beschädigtes WAL darf nicht angewandt werden.", sig)
    if "pending_valid" in codes and not budget_allowed:
        return RecoveryDecision("ROLLBACK", "error", "Recovery-Budget ist für denselben Fehlerzustand erschöpft.", sig)
    if "pending_valid" in codes:
        return RecoveryDecision("REDO", "warning", "Vollständiges WAL besitzt eindeutige Commit-Absicht.", sig)
    if "backup_history_inconsistent" in codes:
        return RecoveryDecision("REBUILD", "error", "Backuphistorie ist aus verifizierten Archiven deterministisch rekonstruierbar.", sig)
    if "orphan_revisions" in codes:
        return RecoveryDecision("REBUILD", "warning", "Revisionsmetadaten sind aus vorhandenem Dateizustand bereinigbar.", sig)
    if {"project_corrupt", "config_corrupt", "invalid_job_sources", "transaction_metadata"} & codes:
        return RecoveryDecision("QUARANTINE", severity, "Unklare oder beschädigte Metadaten dürfen nicht automatisch in Nutzdaten überführt werden.", sig)
    return RecoveryDecision("NONE", severity, "Kein autonomer Reparatureingriff erforderlich.", sig, automatic=False)


def run_autonomous_recovery(
    transaction_root: Path | str,
    *,
    jobs_root: Path | str | None = None,
    config_path: Path | str | None = None,
    project_path: Path | str | None = None,
    backup_dir: Path | str | None = None,
    execute: bool = True,
) -> RecoveryReport:
    root = Path(transaction_root).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    tx_health = inspect_transaction_state(root, recover=False)
    jobs_report = inspect_recovery_consistency(Path(jobs_root)) if jobs_root is not None else None
    signals = (_transaction_signals(tx_health) + _job_signals(jobs_report) + _config_signal(Path(config_path) if config_path is not None else None) + _project_signal(Path(project_path) if project_path is not None else None) + _backup_signal(Path(backup_dir) if backup_dir is not None else None))
    signature = _signature(signals)
    allowed = _budget_allows(root, signature)
    decision = decide_recovery(signals, budget_allowed=allowed)
    actions: list[str] = []
    budget_exhausted = not allowed and decision.action != "NONE"
    if execute and decision.action != "NONE":
        _consume_budget(root, signature)
        if decision.action == "REDO":
            recover_pending_transaction(root)
            actions.append("REDO")
        elif decision.action == "ROLLBACK":
            rollback_pending_transaction(root)
            actions.append("ROLLBACK")
        elif decision.action == "QUARANTINE":
            # Recovery path performs evidence-preserving quarantine for corrupt WAL.
            try:
                recover_pending_transaction(root)
            except TransactionError:
                actions.append("QUARANTINE")
        elif decision.action == "REBUILD":
            if any(item.code == "backup_history_inconsistent" for item in signals) and backup_dir is not None:
                from .project_backup import rebuild_project_backup_history
                rebuild_project_backup_history(backup_dir)
                actions.append("REBUILD_BACKUP_HISTORY")
            if tx_health.orphan_revisions:
                prune_orphan_revisions(root)
                actions.append("REBUILD_REVISIONS")
    final_health = inspect_transaction_state(root, recover=False)
    final_signals = (_transaction_signals(final_health) + _job_signals(jobs_report) + _config_signal(Path(config_path) if config_path is not None else None) + _project_signal(Path(project_path) if project_path is not None else None) + _backup_signal(Path(backup_dir) if backup_dir is not None else None))
    score = _health_score(final_signals)
    status = "healthy" if score >= 90 else "degraded" if score >= 60 else "critical"
    provisional = RecoveryReport(
        POLICY_SCHEMA_VERSION,
        time.time_ns(),
        score,
        status,
        decision,
        tuple(final_signals),
        tuple(sorted({item.domain for item in final_signals})),
        tuple(actions[:MAX_ACTIONS_PER_RUN]),
        budget_exhausted,
        final_health,
        jobs_report.status if jobs_report is not None else "not_checked",
        "",
    )
    package = ""
    if execute and status != "healthy":
        try:
            package = str(write_recovery_diagnostic_package(root, provisional))
        except (OSError, zipfile.BadZipFile):
            package = ""
    return RecoveryReport(
        provisional.schema_version, provisional.generated_at_unix_ns, provisional.health_score,
        provisional.health_status, provisional.decision, provisional.signals, provisional.correlated_domains,
        provisional.actions_executed, provisional.budget_exhausted, provisional.transaction_health,
        provisional.job_consistency_status, package,
    )


def write_recovery_diagnostic_package(root: Path | str, report: RecoveryReport) -> Path:
    base = Path(root).expanduser().resolve()
    directory = _diagnostics_dir(base)
    directory.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    target = directory / f"recovery_diagnostic_{stamp}_{time.time_ns() % 1_000_000:06d}.zip"
    payload = report.as_payload()
    audit = transaction_audit_timeline(base, limit=100)
    manifest = {
        "schema_version": POLICY_SCHEMA_VERSION,
        "generated_at_unix_ns": time.time_ns(),
        "files": ["recovery-report.json", "transaction-audit.json"],
        "privacy": "Metadaten und Recovery-Audit; keine Projekt-Nutzdaten enthalten.",
    }
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("recovery-report.json", json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        archive.writestr("transaction-audit.json", json.dumps(audit, ensure_ascii=False, indent=2, sort_keys=True))
        archive.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True))
    return target


def simulate_disaster_recovery(root: Path | str) -> dict[str, Any]:
    """Run deterministic, isolated multi-fault chains under ``root/simulator``."""
    base = Path(root).expanduser().resolve() / "simulator"
    base.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, Any]] = []

    def scenario(name: str, build) -> None:
        area = base / name
        area.mkdir(parents=True, exist_ok=True)
        outcome = build(area)
        results.append({"scenario": name, **outcome})

    from .transaction_store import transactional_write_json

    def crash_then_redo(area: Path) -> dict[str, Any]:
        target = area / "state.json"
        try:
            transactional_write_json(area, {target: {"generation": 1}}, _crash_after_writes=0)
        except RuntimeError:
            pass
        report = run_autonomous_recovery(area)
        return {"passed": target.exists() and report.actions_executed == ("REDO",), "action": report.actions_executed}

    def torn_then_redo(area: Path) -> dict[str, Any]:
        a, b = area / "a.json", area / "b.json"
        try:
            transactional_write_json(area, {a: {"g": 2}, b: {"g": 2}}, _crash_after_writes=1)
        except RuntimeError:
            pass
        report = run_autonomous_recovery(area)
        same = json.loads(a.read_text()) == json.loads(b.read_text()) == {"g": 2}
        return {"passed": same and report.actions_executed == ("REDO",), "action": report.actions_executed}

    def corrupt_wal(area: Path) -> dict[str, Any]:
        control = area / ".videobatch-transactions"
        control.mkdir(parents=True, exist_ok=True)
        (control / "pending.json").write_text('{"schema_version":1,"transaction_id":"bad","writes":[],"revisions":{"x":1}}', encoding="utf-8")
        report = run_autonomous_recovery(area)
        quarantine = list((control / "quarantine").glob("pending.json.*.quarantine"))
        return {"passed": bool(quarantine) and report.actions_executed == ("QUARANTINE",), "action": report.actions_executed}

    def orphan_rebuild(area: Path) -> dict[str, Any]:
        target = area / "state.json"
        transactional_write_json(area, {target: {"ok": True}})
        target.unlink()
        report = run_autonomous_recovery(area)
        return {"passed": report.actions_executed == ("REBUILD_REVISIONS",) and not report.transaction_health.orphan_revisions, "action": report.actions_executed}

    def budget_rollback(area: Path) -> dict[str, Any]:
        target = area / "state.json"
        transactional_write_json(area, {target: {"g": 0}})
        try:
            transactional_write_json(area, {target: {"g": 1}}, _crash_after_writes=1)
        except RuntimeError:
            pass
        probe = run_autonomous_recovery(area, execute=False)
        for _ in range(MAX_ATTEMPTS_PER_SIGNATURE):
            _consume_budget(area, probe.decision.signature)
        report = run_autonomous_recovery(area)
        restored = json.loads(target.read_text(encoding="utf-8")) == {"g": 0}
        return {"passed": restored and report.actions_executed == ("ROLLBACK",), "action": report.actions_executed}

    def correlated_detection(area: Path) -> dict[str, Any]:
        jobs = area / "jobs"
        (jobs / "active").mkdir(parents=True, exist_ok=True)
        (jobs / "history").mkdir()
        (jobs / "retry_queue.json").write_text("not-json", encoding="utf-8")
        config = area / "config.json"
        config.write_text("not-json", encoding="utf-8")
        report = run_autonomous_recovery(area / "tx", jobs_root=jobs, config_path=config, execute=False)
        domains = set(report.correlated_domains)
        return {"passed": {"config", "jobs"}.issubset(domains) and report.health_status == "critical", "action": report.decision.action}

    scenario("crash-after-wal", crash_then_redo)
    scenario("torn-cross-file", torn_then_redo)
    scenario("corrupt-wal", corrupt_wal)
    scenario("orphan-revision-rebuild", orphan_rebuild)
    scenario("retry-budget-rollback", budget_rollback)
    scenario("correlated-config-job-fault", correlated_detection)
    return {
        "schema_version": 1,
        "scenario_count": len(results),
        "passed": all(item["passed"] for item in results),
        "results": results,
    }
