from __future__ import annotations

import os
import signal
import subprocess
import time

try:
    import resource
except ImportError:  # Windows: Ressourcenlimits bleiben sichtbar, aber ohne prlimit-Hardlimit.
    resource = None

from .execution_control import ExecutionControl
from .runner_process import ProcessExecution, _ProgressState

SIGSTOP = getattr(signal, "SIGSTOP", None)
SIGCONT = getattr(signal, "SIGCONT", None)


def _signal_group(process: subprocess.Popen[str], sig) -> bool:
    if sig is None or process.poll() is not None:
        return False
    try:
        if hasattr(os, "killpg"):
            os.killpg(process.pid, sig)
        else:
            process.send_signal(sig)
        return True
    except (OSError, ProcessLookupError):
        try:
            process.send_signal(sig)
            return True
        except (OSError, ProcessLookupError):
            return False


class ControlledProcessExecution(ProcessExecution):
    """FFmpeg execution with exact process pause, 50% duty throttle and live RAM limit."""

    def __init__(self, *, control: ExecutionControl, **kwargs) -> None:
        super().__init__(**kwargs)
        self.control = control
        self._applied_memory: dict[int, int | None] = {}
        self._pause_supported_notice = False

    def _apply_memory_limit(self, process: subprocess.Popen[str]) -> None:
        requested = self.control.snapshot().memory_limit_bytes
        if self._applied_memory.get(process.pid, object()) == requested:
            return
        if resource is None or not hasattr(resource, "prlimit"):
            self._applied_memory[process.pid] = requested
            if requested is not None:
                self.emit("log", level="warning", message="RAM-Hardlimit benötigt Linux-prlimit und ist hier nicht verfügbar.")
            return
        try:
            _soft, hard = resource.prlimit(process.pid, resource.RLIMIT_AS)
            effective = requested
            if effective is not None and hard not in (-1, resource.RLIM_INFINITY):
                effective = min(effective, int(hard))
            new_soft = hard if effective is None else effective
            resource.prlimit(process.pid, resource.RLIMIT_AS, (new_soft, hard))
            self._applied_memory[process.pid] = requested
            label = "ohne RAM-Limit" if requested is None else f"RAM-Limit {requested / 1024**3:.1f} GB"
            self.emit("log", level="info", message=f"FFmpeg läuft mit {label}.")
        except (AttributeError, OSError, ValueError) as exc:
            self._applied_memory[process.pid] = requested
            self.emit("log", level="warning", message=f"RAM-Limit konnte nicht gesetzt werden: {exc}")

    def _pause_signal(self, process: subprocess.Popen[str], sig, message: str) -> bool:
        if _signal_group(process, sig):
            return True
        if not self._pause_supported_notice:
            self._pause_supported_notice = True
            self.emit("log", level="warning", message=message)
        return False

    def _sync_manual_pause(
        self,
        process: subprocess.Popen[str],
        state: _ProgressState,
        pause_started: float | None,
    ) -> float | None:
        requested = self.control.snapshot().paused
        now = time.monotonic()
        if requested and pause_started is None:
            if not self._pause_signal(process, SIGSTOP, "Prozesspause wird auf diesem System nicht unterstützt."):
                self.control.resume()
                return None
            self.emit("log", level="info", message="Render pausiert; FFmpeg-Zustand bleibt im Speicher erhalten.")
            return now
        if not requested and pause_started is not None:
            self._pause_signal(process, SIGCONT, "Fortsetzen-Signal wird auf diesem System nicht unterstützt.")
            state.started += max(0.0, now - pause_started)
            state.last_progress = now
            state.warned = False
            self.emit("log", level="info", message="Render exakt am pausierten Prozesszustand fortgesetzt.")
            return None
        return pause_started

    def _paced_sleep(self, process: subprocess.Popen[str]) -> None:
        if self.control.snapshot().cpu_limit_percent != 50 or SIGSTOP is None or SIGCONT is None:
            time.sleep(0.5)
            return
        time.sleep(0.25)
        if process.poll() is not None or self.control.snapshot().paused:
            return
        _signal_group(process, SIGSTOP)
        time.sleep(0.25)
        if process.poll() is None and not self.control.snapshot().paused and not self.cancelled():
            _signal_group(process, SIGCONT)

    def _monitor(
        self,
        process: subprocess.Popen[str],
        stdout_queue,
        state: _ProgressState,
        command: list[str],
        job,
        position: int,
        total: int,
    ) -> int:
        pause_started: float | None = None
        try:
            while process.poll() is None:
                if self.cancelled():
                    _signal_group(process, SIGCONT)
                    return self.terminate(process)
                self._apply_memory_limit(process)
                pause_started = self._sync_manual_pause(process, state, pause_started)
                if pause_started is not None:
                    time.sleep(0.1)
                    continue
                changed = self._drain_progress(stdout_queue, state)
                self._update_activity(process, job.output, state, changed)
                inactive = self._emit_progress(state, command, job, position, total)
                if inactive >= self.stall_timeout:
                    state.watchdog_message = (
                        f"FFmpeg wurde nach {inactive:.0f} Sekunden ohne Fortschritt, CPU-Aktivität "
                        "oder Dateiwachstum kontrolliert beendet."
                    )
                    self.emit("log", level="error", message=state.watchdog_message)
                    return self.terminate(process)
                self._paced_sleep(process)
            return int(process.returncode or 0)
        finally:
            if process.poll() is None:
                _signal_group(process, SIGCONT)
