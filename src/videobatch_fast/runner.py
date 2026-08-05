from __future__ import annotations

import os
import signal
import subprocess
import threading
import time
import traceback
import uuid
from pathlib import Path
from typing import Callable

from .command_builder import build_command, resolved_options
from .job_journal import BatchJournal
from .models import BatchOptions, JobResult, PairJob
from .naming import OutputReservation, release_output_reservations, reserve_output_targets
from .quick_modes import fallback_options, mode_spec
from .runner_process import ProcessExecution
from .verification import verify_output

EventCallback = Callable[[str, dict], None]


def _process_cpu_ticks(pid: int) -> int:
    try:
        fields = Path(f"/proc/{pid}/stat").read_text(encoding="utf-8").split()
        return int(fields[13]) + int(fields[14])
    except (OSError, ValueError, IndexError):
        return 0


def _signal_process_group(process: subprocess.Popen[str], sig: signal.Signals) -> None:
    if process.poll() is not None:
        return
    try:
        os.killpg(process.pid, sig)
    except (OSError, ProcessLookupError):
        try:
            process.send_signal(sig)
        except (OSError, ProcessLookupError):
            pass


def terminate_process_group(
    process: subprocess.Popen[str], *, term_timeout: float = 5.0, kill_timeout: float = 3.0
) -> int:
    """Terminate a complete FFmpeg process group with bounded escalation."""
    if process.poll() is not None:
        return int(process.returncode or 0)
    _signal_process_group(process, signal.SIGTERM)
    try:
        return process.wait(timeout=term_timeout)
    except subprocess.TimeoutExpired:
        _signal_process_group(process, signal.SIGKILL)
        try:
            return process.wait(timeout=kill_timeout)
        except subprocess.TimeoutExpired:
            try:
                process.kill()
            except OSError:
                pass
            try:
                return process.wait(timeout=1.0)
            except subprocess.TimeoutExpired:
                return -signal.SIGKILL


class BatchRunner:
    def __init__(self, callback: EventCallback, *, max_consecutive_internal_failures: int = 2) -> None:
        if max_consecutive_internal_failures < 1:
            raise ValueError("Die interne Fehlerschwelle muss mindestens eins betragen.")
        self.callback = callback
        self.max_consecutive_internal_failures = max_consecutive_internal_failures
        self._cancel = threading.Event()
        self._process: subprocess.Popen[str] | None = None
        self._thread: threading.Thread | None = None
        self._reservations: list[OutputReservation] = []
        self._callback_errors: list[str] = []
        self.operation_id = ""
        self._journal: BatchJournal | None = None

    @property
    def running(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    def start(self, jobs: list[PairJob], options: BatchOptions) -> None:
        if self.running:
            raise RuntimeError("Ein Stapel läuft bereits.")
        self._cancel.clear()
        self._callback_errors.clear()
        self.operation_id = uuid.uuid4().hex[:16]
        try:
            self._reservations = reserve_output_targets(job.output for job in jobs)
            self._journal = BatchJournal(self.operation_id, jobs, options)
        except Exception as exc:
            release_output_reservations(self._reservations)
            self._reservations = []
            self._journal = None
            raise RuntimeError(f"Stapel konnte nicht sicher vorbereitet werden: {exc}") from exc
        self._thread = threading.Thread(
            target=self._run_batch,
            args=(jobs, options),
            daemon=True,
            name=f"VideoBatch-{self.operation_id}",
        )
        try:
            self._thread.start()
        except Exception:
            release_output_reservations(self._reservations)
            self._reservations = []
            self._journal = None
            raise

    def cancel(self) -> None:
        self._cancel.set()
        process = self._process
        if process and process.poll() is None:
            _signal_process_group(process, signal.SIGTERM)

    def wait(self, timeout: float | None = None) -> bool:
        thread = self._thread
        if thread is None:
            return True
        thread.join(timeout=timeout)
        return not thread.is_alive()

    def _remember_internal_notice(self, message: str) -> None:
        self._callback_errors.append(message)
        if len(self._callback_errors) > 20:
            del self._callback_errors[:-20]

    def _emit(self, name: str, **payload) -> None:
        payload.setdefault("operation_id", self.operation_id or "general")
        try:
            self.callback(name, payload)
        except Exception as exc:
            self._remember_internal_notice(f"Callbackfehler: {type(exc).__name__}: {exc}")

    def _journal_call(self, method: str, *args) -> bool:
        journal = self._journal
        if journal is None:
            return True
        try:
            getattr(journal, method)(*args)
            return True
        except Exception as exc:
            message = f"Journalfehler bei {method}: {type(exc).__name__}: {exc}"
            self._remember_internal_notice(message)
            self._emit(
                "log",
                level="warning",
                message=(
                    f"{message}. Der Stapel läuft weiter; die Wiederaufnahmeinformation für diesen Schritt "
                    "kann unvollständig sein."
                ),
            )
            return False

    def _recover_after_job_exception(self, job: PairJob) -> tuple[bool, str]:
        safe = True
        actions: list[str] = []
        process = self._process
        if process is not None and process.poll() is None:
            returncode = terminate_process_group(process)
            stopped = process.poll() is not None
            safe = safe and stopped
            actions.append(
                f"Laufender FFmpeg-Prozess kontrolliert beendet (Code {returncode})."
                if stopped
                else "FFmpeg-Prozess konnte nicht eindeutig beendet werden."
            )
        self._process = None
        try:
            if job.output.exists() or job.output.is_symlink():
                job.output.unlink()
                actions.append("Unvollständige Ausgabedatei entfernt.")
            else:
                actions.append("Keine unvollständige Ausgabedatei vorhanden.")
        except OSError as exc:
            safe = False
            actions.append(f"Unvollständige Ausgabe konnte nicht entfernt werden: {exc}")
        return safe, " ".join(actions)

    def _internal_job_failure(
        self,
        job: PairJob,
        exc: Exception,
    ) -> tuple[JobResult, str, bool, str]:
        detail = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))[-16_000:]
        recoverable, protection = self._recover_after_job_exception(job)
        result = JobResult(job, False, 70, 0.0, f"Interner Fehler: {type(exc).__name__}: {exc}")
        return result, detail, recoverable, protection

    def _run_batch(self, jobs: list[PairJob], options: BatchOptions) -> None:
        started = time.monotonic()
        results: list[JobResult] = []
        internal_error = ""
        terminal_event = "batch_finished"
        consecutive_internal_failures = 0
        try:
            self._emit("batch_started", total=len(jobs))
            for position, job in enumerate(jobs, start=1):
                if self._cancel.is_set():
                    terminal_event = "batch_cancelled"
                    break
                self._journal_call("mark_started", job.index)
                try:
                    result = self._run_job(job, position, len(jobs), options)
                except Exception as exc:
                    consecutive_internal_failures += 1
                    result, internal_error, recovered, protection = self._internal_job_failure(job, exc)
                    results.append(result)
                    self._journal_call("mark_finished", result)
                    continue_allowed = (
                        recovered
                        and consecutive_internal_failures < self.max_consecutive_internal_failures
                        and not self._cancel.is_set()
                    )
                    self._emit(
                        "job_failed_internal",
                        job=job,
                        position=position,
                        total=len(jobs),
                        message=result.message,
                        traceback=internal_error,
                        protection=protection,
                        recoverable=continue_allowed,
                        consecutive_failures=consecutive_internal_failures,
                        failure_limit=self.max_consecutive_internal_failures,
                    )
                    self._emit("job_finished", result=result, position=position, total=len(jobs))
                    if not continue_allowed:
                        terminal_event = "batch_failed_internal"
                        reason = (
                            "Der Prozesszustand konnte nicht sicher bereinigt werden."
                            if not recovered
                            else (
                                f"Die Schutzschwelle von {self.max_consecutive_internal_failures} "
                                "aufeinanderfolgenden internen Fehlern wurde erreicht."
                            )
                        )
                        self._emit(
                            "batch_failed_internal",
                            job=job,
                            position=position,
                            total=len(jobs),
                            message=f"{result.message} {reason}",
                            traceback=internal_error,
                            protection=protection,
                        )
                        break
                    terminal_event = "batch_completed_with_internal_failures"
                    self._emit(
                        "log",
                        level="warning",
                        message=(
                            f"Auftrag {position}/{len(jobs)} wurde isoliert als fehlgeschlagen markiert. "
                            "Der nächste Auftrag wird mit bereinigtem Prozesszustand fortgesetzt."
                        ),
                    )
                    continue

                consecutive_internal_failures = 0
                results.append(result)
                self._journal_call("mark_finished", result)
                self._emit("job_finished", result=result, position=position, total=len(jobs))
        except Exception as exc:
            terminal_event = "batch_failed_internal"
            internal_error = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))[-16_000:]
            self._emit(
                "batch_failed_internal",
                message=f"Interner Stapelfehler: {type(exc).__name__}: {exc}",
                traceback=internal_error,
                protection="Reservierungen und laufende Prozesse werden im Abschlussblock bereinigt.",
            )
        finally:
            process = self._process
            if process and process.poll() is None:
                terminate_process_group(process)
            self._process = None
            release_output_reservations(self._reservations)
            self._reservations = []
            cancelled = self._cancel.is_set()
            if cancelled:
                terminal_event = "batch_cancelled"
            successes = sum(result.success for result in results)
            if self._journal is not None:
                try:
                    self._journal.finish(
                        terminal_event=terminal_event,
                        cancelled=cancelled,
                        internal_error=internal_error,
                    )
                except Exception as journal_error:
                    self._remember_internal_notice(
                        f"Journalfehler beim Abschluss: {type(journal_error).__name__}: {journal_error}"
                    )
                finally:
                    self._journal = None
            self._emit(
                "batch_finished",
                terminal_event=terminal_event,
                cancelled=cancelled,
                successes=successes,
                failures=len(results) - successes,
                unprocessed=max(0, len(jobs) - len(results)),
                total=len(jobs),
                elapsed=time.monotonic() - started,
                results=results,
                internal_error=internal_error,
                callback_errors=tuple(self._callback_errors),
            )

    def _run_job(self, job: PairJob, position: int, total: int, options: BatchOptions) -> JobResult:
        start = time.monotonic()
        self._emit("job_started", job=job, position=position, total=total)
        selected = resolved_options(job, options)
        command = build_command(job, options)
        result = self._execute(command, job, position, total)
        retried = False
        fallback_mode = ""
        if result.returncode == 0:
            valid, message = verify_output(job.output, job, selected.verification)
        else:
            valid, message = False, result.message

        if not valid and not self._cancel.is_set() and job.fast_path:
            retried = True
            self._emit(
                "log",
                level="warning",
                message=f"Schnellkopie nicht gültig: {message} · sichere Neucodierung wird einmal versucht.",
            )
            job.output.unlink(missing_ok=True)
            command = build_command(job, options, force_encode=True)
            result = self._execute(command, job, position, total)
            valid, message = (
                verify_output(job.output, job, selected.verification)
                if result.returncode == 0
                else (False, result.message)
            )

        if not valid and not self._cancel.is_set() and not job.fast_path:
            safe_options = fallback_options(options)
            if safe_options is not None:
                retried = True
                fallback_mode = mode_spec(safe_options.quick_mode).label
                self._emit(
                    "log",
                    level="warning",
                    message=(
                        f"Der gewählte Look konnte nicht sicher fertiggestellt werden: {message} · "
                        f"{fallback_mode} wird automatisch einmal als sichere Alternative verwendet."
                    ),
                )
                job.output.unlink(missing_ok=True)
                command = build_command(job, safe_options)
                result = self._execute(command, job, position, total)
                safe_selected = resolved_options(job, safe_options)
                if result.returncode == 0:
                    valid, message = verify_output(job.output, job, safe_selected.verification)
                    if valid:
                        message = f"Sichere Alternative {fallback_mode} erfolgreich · {message}"
                else:
                    valid, message = False, result.message

        elapsed = time.monotonic() - start
        return JobResult(
            job,
            valid,
            result.returncode,
            elapsed,
            message,
            retried=retried,
            command=command,
            fallback_mode=fallback_mode,
        )

    def _execute(self, command: list[str], job: PairJob, position: int, total: int) -> JobResult:
        execution = ProcessExecution(
            emit=self._emit,
            cancelled=self._cancel.is_set,
            set_process=self._set_process,
            terminate=terminate_process_group,
            cpu_ticks=_process_cpu_ticks,
        )
        return execution.run(command, job, position, total)

    def _set_process(self, process: subprocess.Popen[str] | None) -> None:
        self._process = process
