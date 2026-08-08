from videobatch_fast.scheduler_readiness import inspect_scheduler_readiness


def test_scheduler_readiness_enables_only_when_all_runtime_requirements_exist(monkeypatch) -> None:
    monkeypatch.setattr("videobatch_fast.scheduler_readiness.shutil.which", lambda _name: "/usr/bin/tool")
    result = inspect_scheduler_readiness(user_manager_probe=lambda: True)
    assert result.ready is True
    assert "Scheduler bereit" in result.summary
    assert len(result.checks) == 5
    assert all(ok for _name, ok, _detail in result.checks)


def test_scheduler_readiness_reports_missing_host_capabilities(monkeypatch) -> None:
    monkeypatch.setattr("videobatch_fast.scheduler_readiness.shutil.which", lambda _name: None)
    result = inspect_scheduler_readiness(user_manager_probe=lambda: False)
    assert result.ready is False
    assert "0/5" in result.summary
    assert not any(ok for _name, ok, _detail in result.checks)
