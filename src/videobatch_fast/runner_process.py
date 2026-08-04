from __future__ import annotations

import queue
import subprocess
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from .models import JobResult, PairJob, ProgressSnapshot

EmitCallback = Callable[..., None]
CancelCallback = Callable[[], bool]
ProcessCallback = Callable[[subprocess.Popen[str] | None], None]
TerminateCallback = Callable[[subprocess.Popen[str]], int]
CpuTicksCallback = Callable[[int], int]


@dataclass(slots=True)
class _ProgressState:
    started: float
    duration: float
    out_time: float = 0.0
    speed: str = ""
    frame: int | None = None
    fps: float | None = None
    last_progress: float = 0.0
    last_ticks: int = 0
    last_size: int = 0
    warned: bool = False
    watchdog_message: str = ""
    values: dict[str, str] = field(default_factory=dict)


class ProcessExecution:
    """Run one FFmpeg command while keeping monitoring and cleanup testable."""

    def __init__(
        self,
        *,
        emit: EmitCallback,
        cancelled: CancelCallback,
        set_process: ProcessCallback,
        terminate: TerminateCallback,
        cpu_ticks: CpuTicksCallback,
        warning_timeout: float = 20.0,
        stall_timeout: float = 90.0,
    ) -> None:
        self.emit = emit
        self.cancelled = cancelled
        self.set_process = set_process
        if warning_timeout <= 0 or stall_timeout <= warning_timeout:
            raise ValueError("Watchdog-Grenzen sind ungültig.")
        self.terminate = terminate
        self.cpu_ticks = cpu_ticks
        self.warning_timeout = warning_timeout
        self.stall_timeout = stall_timeout

    def run(self, command: list[str], job: PairJob, position: int, total: int) -> JobResult:
        started = time.monotonic()
        self.emit("command", command=command)
        process, error = self._spawn(command)
        if process is None:
            return JobResult(job, False, 127, 0.0, error, command=command)
        self.set_process(process)
        stdout_queue: queue.Queue[str] = queue.Queue()
        stderr_lines: list[str] = []
        threads = self._start_readers(process, stdout_queue, stderr_lines)
        state = self._new_progress_state(process, job, started)
        try:
            returncode = self._monitor(process, stdout_queue, state, command, job, position, total)
        finally:
            self._close_process_streams(process, threads)
            self.set_process(None)
        return self._result(
            command,
            job,
            position,
            total,
            returncode,
            stderr_lines,
            started,
            override_message=state.watchdog_message,
        )

    @staticmethod
    def _spawn(command: list[str]) -> tuple[subprocess.Popen[str] | None, str]:
        try:
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
                start_new_session=True,
            )
            return process, ""
        except OSError as exc:
            return None, str(exc)

    @staticmethod
    def _reader(stream, sink: Callable[[str], None]) -> None:
        if stream is None:
            return
        for line in stream:
            sink(line.rstrip("\r\n"))

    def _start_readers(
        self,
        process: subprocess.Popen[str],
        stdout_queue: queue.Queue[str],
        stderr_lines: list[str],
    ) -> tuple[threading.Thread, threading.Thread]:
        def append_stderr(value: str) -> None:
            stderr_lines.append(value)
            if len(stderr_lines) > 120:
                del stderr_lines[:40]

        stdout_thread = threading.Thread(
            target=self._reader,
            args=(process.stdout, stdout_queue.put),
            daemon=True,
            name="ffmpeg-stdout",
        )
        stderr_thread = threading.Thread(
            target=self._reader,
            args=(process.stderr, append_stderr),
            daemon=True,
            name="ffmpeg-stderr",
        )
        stdout_thread.start()
        stderr_thread.start()
        return stdout_thread, stderr_thread

    def _new_progress_state(self, process: subprocess.Popen[str], job: PairJob, started: float) -> _ProgressState:
        return _ProgressState(
            started=started,
            duration=job.audio_info.duration or 0.0,
            last_progress=time.monotonic(),
            last_ticks=self.cpu_ticks(process.pid),
        )

    def _monitor(
        self,
        process: subprocess.Popen[str],
        stdout_queue: queue.Queue[str],
        state: _ProgressState,
        command: list[str],
        job: PairJob,
        position: int,
        total: int,
    ) -> int:
        while process.poll() is None:
            if self.cancelled():
                return self.terminate(process)
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
            time.sleep(0.5)
        return int(process.returncode or 0)

    def _drain_progress(self, stdout_queue: queue.Queue[str], state: _ProgressState) -> bool:
        changed = False
        while True:
            try:
                line = stdout_queue.get_nowait()
            except queue.Empty:
                return changed
            changed = self._apply_progress_line(line, state) or changed

    @staticmethod
    def _apply_progress_line(line: str, state: _ProgressState) -> bool:
        if "=" not in line:
            return False
        key, value = line.split("=", 1)
        state.values[key] = value
        if key in {"out_time_us", "out_time_ms"}:
            return ProcessExecution._set_out_time(value, state)
        if key == "speed":
            state.speed = value
        elif key == "frame":
            state.frame = ProcessExecution._parse_int(value, state.frame)
        elif key == "fps":
            state.fps = ProcessExecution._parse_float(value, state.fps)
        return False

    @staticmethod
    def _set_out_time(value: str, state: _ProgressState) -> bool:
        current = ProcessExecution._parse_float(value, 0.0) / 1_000_000
        if current <= state.out_time:
            return False
        state.out_time = current
        return True

    @staticmethod
    def _parse_int(value: str, default: int | None) -> int | None:
        try:
            return int(value)
        except ValueError:
            return default

    @staticmethod
    def _parse_float(value: str, default: float | None) -> float:
        try:
            return float(value)
        except ValueError:
            return float(default or 0.0)

    def _update_activity(self, process: subprocess.Popen[str], output: Path, state: _ProgressState, changed: bool) -> None:
        size = self._output_size(output)
        ticks = self.cpu_ticks(process.pid)
        if changed or size > state.last_size or ticks > state.last_ticks:
            state.last_progress = time.monotonic()
            state.warned = False
        state.last_ticks = ticks
        state.last_size = size

    @staticmethod
    def _output_size(output: Path) -> int:
        try:
            return output.stat().st_size
        except OSError:
            return 0

    def _emit_progress(
        self,
        state: _ProgressState,
        command: list[str],
        job: PairJob,
        position: int,
        total: int,
    ) -> float:
        now = time.monotonic()
        inactive = now - state.last_progress
        if inactive > self.warning_timeout and not state.warned:
            state.warned = True
            self.emit(
                "log",
                level="warning",
                message="Der Prozentwert steht länger still. CPU und Dateiwachstum werden weiter überwacht.",
            )
        self.emit(
            "progress",
            snapshot=self._snapshot(state, command, job, position, total, now, inactive),
            job=job,
        )
        return inactive

    @staticmethod
    def _snapshot(
        state: _ProgressState,
        command: list[str],
        job: PairJob,
        position: int,
        total: int,
        now: float,
        inactive: float,
    ) -> ProgressSnapshot:
        elapsed = now - state.started
        local = min(99.0, (state.out_time / state.duration * 100.0) if state.duration > 0 else 0.0)
        eta = max(0.0, elapsed * (100.0 - local) / local) if local > 0.5 else None
        total_percent = ((position - 1) + local / 100.0) / max(1, total) * 100.0
        return ProgressSnapshot(
            job_index=position,
            job_total=total,
            job_percent=local,
            total_percent=total_percent,
            phase=ProcessExecution._phase(command, job),
            elapsed_seconds=elapsed,
            eta_seconds=eta,
            speed=state.speed,
            frame=state.frame,
            fps=state.fps,
            output_size=state.last_size,
            last_activity_seconds=inactive,
            detail="Prozentwert unverändert – Prozessaktivität wird geprüft" if inactive > 8 else "Aktive Verarbeitung",
        )

    @staticmethod
    def _phase(command: list[str], job: PairJob) -> str:
        if job.fast_path and "copy" in command:
            return "Schnellkopie"
        return "Schneller 1-Pass-Render" if "-vf" in command else "Video wird codiert"

    @staticmethod
    def _close_process_streams(
        process: subprocess.Popen[str], threads: tuple[threading.Thread, threading.Thread]
    ) -> None:
        for stream in (process.stdout, process.stderr):
            try:
                if stream is not None:
                    stream.close()
            except OSError:
                pass
        for thread in threads:
            thread.join(timeout=1.0)

    def _result(
        self,
        command: list[str],
        job: PairJob,
        position: int,
        total: int,
        returncode: int,
        stderr_lines: list[str],
        started: float,
        *,
        override_message: str = "",
    ) -> JobResult:
        elapsed = time.monotonic() - started
        if self.cancelled():
            return JobResult(job, False, returncode, elapsed, "Vom Nutzer abgebrochen.", command=command)
        if returncode:
            meaningful = [line for line in stderr_lines if line.strip()]
            message = override_message or (meaningful[-1] if meaningful else f"FFmpeg endete mit Code {returncode}.")
            return JobResult(job, False, returncode, elapsed, message, command=command)
        self.emit(
            "progress",
            snapshot=ProgressSnapshot(
                position,
                total,
                100.0,
                position / max(1, total) * 100.0,
                "Prüfung",
                elapsed,
                0.0,
                "",
                output_size=self._output_size(job.output),
            ),
            job=job,
        )
        return JobResult(job, True, 0, elapsed, "FFmpeg abgeschlossen.", command=command)
