from __future__ import annotations

import signal

import pytest

from videobatch_fast.canonical_resource_control_mixin import CanonicalResourceControlMixin
from videobatch_fast.canonical_ui import CanonicalVideoBatchFastUI
from videobatch_fast.controlled_runner import ControlledBatchRunner
from videobatch_fast.execution_control import ExecutionControl, GIB, RAM_LIMIT_PRESETS_GB
from videobatch_fast.resource_process import ControlledProcessExecution, _ProgressState
from videobatch_fast.system_resources import SystemResourceMonitor, format_bytes


class _FakeProcess:
    pid = 424242

    @staticmethod
    def poll():
        return None


def _execution(control: ExecutionControl):
    events = []
    execution = ControlledProcessExecution(
        control=control,
        emit=lambda name, **payload: events.append((name, payload)),
        cancelled=lambda: False,
        set_process=lambda _process: None,
        terminate=lambda _process: 0,
        cpu_ticks=lambda _pid: 0,
    )
    return execution, events


def test_execution_control_exposes_exact_requested_presets() -> None:
    control = ExecutionControl()
    control.set_cpu_limit_50(True)
    control.set_memory_limit_gb(1.5)
    control.pause()
    snapshot = control.snapshot()
    assert snapshot.paused is True
    assert snapshot.cpu_limit_percent == 50
    assert snapshot.memory_limit_bytes == int(1.5 * GIB)
    control.resume()
    control.set_cpu_limit_50(False)
    control.set_memory_limit_gb(None)
    assert control.snapshot().paused is False
    assert RAM_LIMIT_PRESETS_GB == (1.0, 1.5, 2.0, 2.5)
    with pytest.raises(ValueError):
        control.set_memory_limit_gb(3.0)


def test_pause_resume_preserves_progress_clock(monkeypatch) -> None:
    control = ExecutionControl()
    execution, events = _execution(control)
    monkeypatch.setattr(execution, "_pause_signal", lambda *_args: True)
    moments = iter((10.0, 12.5))
    monkeypatch.setattr("videobatch_fast.resource_process.time.monotonic", lambda: next(moments))
    state = _ProgressState(started=2.0, duration=30.0, last_progress=8.0)
    control.pause()
    paused_at = execution._sync_manual_pause(_FakeProcess(), state, None)
    assert paused_at == 10.0
    control.resume()
    assert execution._sync_manual_pause(_FakeProcess(), state, paused_at) is None
    assert state.started == 4.5
    assert state.last_progress == 12.5
    assert any("pausiert" in payload.get("message", "") for _, payload in events)
    assert any("fortgesetzt" in payload.get("message", "") for _, payload in events)


def test_cpu_50_duty_cycle_stops_and_continues_process(monkeypatch) -> None:
    if not hasattr(signal, "SIGSTOP") or not hasattr(signal, "SIGCONT"):
        pytest.skip("POSIX-Prozesssignale nicht verfügbar")
    control = ExecutionControl()
    control.set_cpu_limit_50(True)
    execution, _events = _execution(control)
    signals = []
    monkeypatch.setattr("videobatch_fast.resource_process.time.sleep", lambda _seconds: None)
    monkeypatch.setattr(
        "videobatch_fast.resource_process._signal_group",
        lambda _process, sig: signals.append(sig) or True,
    )
    execution._paced_sleep(_FakeProcess())
    assert signals == [signal.SIGSTOP, signal.SIGCONT]


def test_system_resource_monitor_reports_bounded_live_values(tmp_path) -> None:
    monitor = SystemResourceMonitor()
    monitor.sample(tmp_path)
    snapshot = monitor.sample(tmp_path)
    assert 0.0 <= snapshot.cpu_percent <= 100.0
    assert 0 <= snapshot.ram_used <= snapshot.ram_total
    assert 0 <= snapshot.swap_used <= snapshot.swap_total
    assert 0 <= snapshot.zram_used <= snapshot.zram_total
    assert 0 < snapshot.disk_free <= snapshot.disk_total
    assert format_bytes(1024**3) == "1.0 GB"


def test_controlled_runner_and_canonical_shell_use_resource_control_layer() -> None:
    runner = ControlledBatchRunner(lambda _event: None)
    runner.set_cpu_limit_50(True)
    runner.set_memory_limit_gb(2.5)
    snapshot = runner.execution_control.snapshot()
    assert snapshot.cpu_limit_percent == 50
    assert snapshot.memory_limit_bytes == int(2.5 * GIB)
    assert issubclass(CanonicalVideoBatchFastUI, CanonicalResourceControlMixin)
