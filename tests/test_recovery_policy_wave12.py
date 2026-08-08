from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest

from videobatch_fast.recovery_policy import (
    RecoverySignal,
    decide_recovery,
    run_autonomous_recovery,
    simulate_disaster_recovery,
    write_recovery_diagnostic_package,
)
from videobatch_fast.transaction_store import transactional_write_json


def test_decision_matrix_is_deterministic():
    assert decide_recovery([RecoverySignal("transaction", "warning", "pending_valid", "x")], budget_allowed=True).action == "REDO"
    assert decide_recovery([RecoverySignal("transaction", "warning", "pending_valid", "x")], budget_allowed=False).action == "ROLLBACK"
    assert decide_recovery([RecoverySignal("transaction", "critical", "pending_corrupt", "x")], budget_allowed=True).action == "QUARANTINE"
    assert decide_recovery([RecoverySignal("transaction", "warning", "orphan_revisions", "x")], budget_allowed=True).action == "REBUILD"


def test_valid_pending_is_redone(tmp_path: Path):
    target = tmp_path / "state.json"
    with pytest.raises(RuntimeError):
        transactional_write_json(tmp_path, {target: {"g": 1}}, _crash_after_writes=0)
    report = run_autonomous_recovery(tmp_path)
    assert report.actions_executed == ("REDO",)
    assert json.loads(target.read_text()) == {"g": 1}
    assert report.health_score == 100


def test_corrupt_pending_is_quarantined(tmp_path: Path):
    control = tmp_path / ".videobatch-transactions"
    control.mkdir()
    (control / "pending.json").write_text('{"schema_version":1,"transaction_id":"bad","writes":[],"revisions":{"x":1}}', encoding="utf-8")
    report = run_autonomous_recovery(tmp_path)
    assert report.actions_executed == ("QUARANTINE",)
    assert not (control / "pending.json").exists()
    assert list((control / "quarantine").glob("pending.json.*.quarantine"))


def test_orphan_revision_is_rebuilt_metadata_only(tmp_path: Path):
    target = tmp_path / "state.json"
    transactional_write_json(tmp_path, {target: {"ok": True}})
    target.unlink()
    report = run_autonomous_recovery(tmp_path)
    assert report.decision.action == "REBUILD"
    assert report.actions_executed == ("REBUILD_REVISIONS",)
    assert report.transaction_health.orphan_revisions == ()


def test_budget_forces_rollback_after_repeated_same_fault(tmp_path: Path):
    target = tmp_path / "state.json"
    transactional_write_json(tmp_path, {target: {"g": 0}})
    with pytest.raises(RuntimeError):
        transactional_write_json(tmp_path, {target: {"g": 1}}, _crash_after_writes=1)
    # Consume identical signature without executing until budget is exhausted.
    for _ in range(3):
        report = run_autonomous_recovery(tmp_path, execute=False)
        from videobatch_fast.recovery_policy import _consume_budget
        _consume_budget(tmp_path, report.decision.signature)
    report = run_autonomous_recovery(tmp_path)
    assert report.decision.action == "ROLLBACK"
    assert report.actions_executed == ("ROLLBACK",)
    assert json.loads(target.read_text()) == {"g": 0}


def test_correlated_config_and_job_faults_reduce_health(tmp_path: Path):
    tx = tmp_path / "tx"
    tx.mkdir()
    config = tmp_path / "config.json"
    config.write_text("not-json", encoding="utf-8")
    jobs = tmp_path / "jobs"
    (jobs / "active").mkdir(parents=True)
    (jobs / "history").mkdir()
    (jobs / "retry_queue.json").write_text("not-json", encoding="utf-8")
    report = run_autonomous_recovery(tx, jobs_root=jobs, config_path=config, execute=False)
    assert {"config", "jobs"}.issubset(set(report.correlated_domains))
    assert report.health_score < 60
    assert report.health_status == "critical"


def test_diagnostic_package_contains_metadata_not_project_data(tmp_path: Path):
    report = run_autonomous_recovery(tmp_path, execute=False)
    package = write_recovery_diagnostic_package(tmp_path, report)
    with zipfile.ZipFile(package) as archive:
        assert set(archive.namelist()) == {"manifest.json", "recovery-report.json", "transaction-audit.json"}
        manifest = json.loads(archive.read("manifest.json"))
    assert "keine Projekt-Nutzdaten" in manifest["privacy"]


def test_disaster_recovery_simulator_is_deterministic(tmp_path: Path):
    result = simulate_disaster_recovery(tmp_path)
    assert result["scenario_count"] == 6
    assert result["passed"] is True
    assert [item["scenario"] for item in result["results"]] == [
        "crash-after-wal", "torn-cross-file", "corrupt-wal", "orphan-revision-rebuild",
        "retry-budget-rollback", "correlated-config-job-fault",
    ]


def test_project_and_backup_are_distinct_correlated_domains(tmp_path: Path):
    tx = tmp_path / "tx"
    tx.mkdir()
    project = tmp_path / "project.json"
    project.write_text("not-json", encoding="utf-8")
    backup = tmp_path / "backups"
    backup.mkdir()
    (backup / "history.json").write_text("[]", encoding="utf-8")
    (backup / "history.meta.json").write_text('{"schema_version":1,"count":9,"history_sha256":"bad"}', encoding="utf-8")
    report = run_autonomous_recovery(tx, project_path=project, backup_dir=backup, execute=False)
    assert {"project", "backup"}.issubset(set(report.correlated_domains))
    assert report.health_status == "critical"


def test_backup_history_rebuild_uses_only_verified_archives(monkeypatch, tmp_path: Path):
    import videobatch_fast.project_backup as backup

    directory = tmp_path / "backups"
    directory.mkdir()
    monkeypatch.setattr(backup, "project_backup_directory", lambda: directory)
    project = tmp_path / "project.json"
    project.write_text('{"schema_version":3,"project_name":"W12"}', encoding="utf-8")
    created = backup.create_project_backup(project)
    (directory / "history.meta.json").write_text('{"schema_version":1,"count":999,"history_sha256":"bad"}', encoding="utf-8")
    report = run_autonomous_recovery(directory, backup_dir=directory)
    assert report.decision.action == "REBUILD"
    assert "REBUILD_BACKUP_HISTORY" in report.actions_executed
    assert [item.path for item in backup.list_project_backups(limit=10)] == [created.path]
