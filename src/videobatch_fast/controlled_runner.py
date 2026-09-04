from __future__ import annotations

from .execution_control import ExecutionControl
from .resource_process import ControlledProcessExecution
from .runner import BatchRunner, _process_cpu_ticks, terminate_process_group


class ControlledBatchRunner(BatchRunner):
    """BatchRunner extension that keeps resource policies separate from batch semantics."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.execution_control = ExecutionControl()

    @property
    def paused(self) -> bool:
        return self.execution_control.paused

    def _log_control(self, message: str) -> None:
        self._publish_mapping("log", level="info", message=message)

    def pause(self) -> None:
        if self.running:
            self.execution_control.pause()
            self._log_control("Laufender FFmpeg-Prozess wird pausiert.")

    def resume(self) -> None:
        was_paused = self.execution_control.paused
        self.execution_control.resume()
        if was_paused:
            self._log_control("FFmpeg wird am gehaltenen Zustand fortgesetzt.")

    def set_cpu_limit_50(self, enabled: bool) -> None:
        self.execution_control.set_cpu_limit_50(enabled)
        state = "aktiv" if enabled else "aus"
        self._log_control(f"CPU-Limit 50 %: {state}.")

    def set_memory_limit_gb(self, gigabytes: float | None) -> None:
        self.execution_control.set_memory_limit_gb(gigabytes)
        state = "aus" if gigabytes is None else f"{gigabytes:g} GB"
        self._log_control(f"RAM-Limit: {state}.")

    def start(self, jobs, options) -> None:
        self.execution_control.resume()
        super().start(jobs, options)

    def cancel(self) -> None:
        self.execution_control.resume()
        super().cancel()

    def _execute(self, command, job, position, total):
        execution = ControlledProcessExecution(
            control=self.execution_control,
            emit=self._publish_mapping,
            cancelled=self._cancel.is_set,
            set_process=self._set_process,
            terminate=terminate_process_group,
            cpu_ticks=_process_cpu_ticks,
        )
        return execution.run(command, job, position, total)
