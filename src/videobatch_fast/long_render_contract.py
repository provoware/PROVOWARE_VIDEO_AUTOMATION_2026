from __future__ import annotations

import signal
import time
from pathlib import Path
from typing import Any

from .long_render_execution import Executor, batch_options, build_pair_job, execute_job
from .long_render_schema import (
    TERMINAL_STATES,
    LoadedContract,
    LongRenderContractError,
    build_input_manifest,
    canonical_hash,
    load_contract,
    sha256_file,
    utc_now,
    verify_input_manifest,
)
from .long_render_state import (
    append_event,
    archive_partial,
    ensure_reservation,
    job_by_id,
    load_state,
    new_state,
    release_reservations,
    reservation_path,
    state_directory,
    write_heartbeat,
    write_state,
)
from .long_render_target import validate_hard_limit_runtime, validate_target
from .models import JobResult, PairJob, ProgressSnapshot
from .probe import ffmpeg_path, ffprobe_path
from .safe_io import atomic_write_json, fsync_directory
from .verification import verify_output

_reservation_path = reservation_path


class LongRenderAcceptance:
    def __init__(
        self,
        contract: LoadedContract,
        *,
        allow_rehearsal_target: bool = False,
        allow_soft_limits: bool = False,
        executor: Executor | None = None,
    ) -> None:
        self.contract = contract
        self.allow_rehearsal_target = allow_rehearsal_target
        self.allow_soft_limits = allow_soft_limits
        self.executor = executor
        self._cancelled = False
        self._last_heartbeat = 0.0
        self._invocation_started = 0.0
        self._accounted_at = 0.0
        self._timeout_reason = ""
        self._state: dict[str, Any] = {}

    def prepare(self, *, resume: bool) -> dict[str, Any]:
        contract = self.contract
        if self.executor is None and (not ffmpeg_path() or not ffprobe_path()):
            raise LongRenderContractError("FFmpeg und FFprobe müssen vor dem Langzeitrender verfügbar sein.")
        if not self.allow_rehearsal_target and contract.package is None:
            raise LongRenderContractError("Der physische Abnahmelauf benötigt ein gebundenes RC24-Paket.")
        if contract.target_policy.require_hard_limits and self.allow_soft_limits and not self.allow_rehearsal_target:
            raise LongRenderContractError(
                "Weiche Ressourcengrenzen sind nur im ausdrücklich markierten Probelauf erlaubt."
            )
        target = validate_target(contract, allow_rehearsal_target=self.allow_rehearsal_target)
        hard_limits = contract.target_policy.require_hard_limits and not self.allow_soft_limits
        if hard_limits:
            validate_hard_limit_runtime(contract.limits)
        target["resource_mode"] = "hard-systemd" if hard_limits else "soft-rehearsal"

        if resume:
            state = load_state(contract)
            if state.get("state") in TERMINAL_STATES:
                raise LongRenderContractError("Ein terminal abgeschlossener Lauf darf nicht wiederaufgenommen werden.")
            self._verify_resume_target(state, target)
            state["resume_count"] = int(state.get("resume_count", 0)) + 1
            verify_input_manifest(state.get("input_manifest", {}), full_hash=True)
        else:
            if contract.state_file.exists():
                raise LongRenderContractError(
                    "Zustandsdatei existiert bereits; --resume verwenden oder bewusst archivieren."
                )
            for spec in contract.jobs:
                output = contract.target_dir / spec.output_name
                if output.exists():
                    raise LongRenderContractError(
                        f"Zieldatei existiert bereits; nichts wird überschrieben: {output}"
                    )
            state = new_state(contract, target, build_input_manifest(contract))
            self._state = state
            write_state(contract, state)

        run_id = str(state.get("run_id", ""))
        created_reservations: list[Path] = []
        try:
            for spec in contract.jobs:
                output = contract.target_dir / spec.output_name
                record = job_by_id(state, spec.job_id)
                lock = reservation_path(output)
                existed = lock.exists()
                ensure_reservation(
                    output,
                    run_id=run_id,
                    job_id=spec.job_id,
                    contract_digest=contract.digest,
                )
                if not existed:
                    created_reservations.append(lock)
                if record.get("state") == "completed":
                    self._verify_completed_output(spec.job_id, output, record)
                elif resume and output.exists():
                    record["partial_archived"] = str(archive_partial(contract, output))
                    record["state"] = "pending"
        except Exception:
            if not resume:
                for lock in created_reservations:
                    lock.unlink(missing_ok=True)
                fsync_directory(contract.target_dir)
            raise

        state["state"] = "prepared"
        self._state = state
        write_state(contract, state)
        return state

    @staticmethod
    def _verify_resume_target(state: dict[str, Any], current: dict[str, Any]) -> None:
        stored = state.get("target")
        if not isinstance(stored, dict):
            raise LongRenderContractError("Gespeicherte Zielidentität fehlt; Wiederaufnahme blockiert.")
        identity_fields = (
            "mount_point",
            "filesystem",
            "source",
            "external_usb",
            "device_serial",
            "filesystem_uuid",
            "resource_mode",
            "rehearsal_target",
        )
        changed = [field for field in identity_fields if stored.get(field) != current.get(field)]
        if changed:
            raise LongRenderContractError(
                "Zielidentität oder Ressourcenmodus wurde seit dem ersten Lauf verändert: "
                + ", ".join(changed)
            )
        expected_rehearsal = bool(current.get("rehearsal_target") or current.get("resource_mode") != "hard-systemd")
        if bool(state.get("rehearsal_only")) != expected_rehearsal:
            raise LongRenderContractError("Der Probelauf-/Physikmodus darf bei Wiederaufnahme nicht wechseln.")

    def _verify_completed_output(self, job_id: str, output: Path, record: dict[str, Any]) -> None:
        if not output.is_file():
            raise LongRenderContractError(f"Als fertig markierte Ausgabe fehlt: {output}")
        if output.stat().st_size != int(record.get("output_size", -1)):
            raise LongRenderContractError(f"Größe einer fertigen Ausgabe hat sich verändert: {output}")
        if sha256_file(output) != str(record.get("output_sha256", "")):
            raise LongRenderContractError(f"SHA-256 einer fertigen Ausgabe hat sich verändert: {output}")
        spec = next((item for item in self.contract.jobs if item.job_id == job_id), None)
        if spec is None:
            raise LongRenderContractError(f"Auftrag fehlt im Vertrag: {job_id}")
        job = build_pair_job(spec, output)
        valid, message = verify_output(output, job, "Vollständig")
        if not valid:
            raise LongRenderContractError(
                f"Fertige Ausgabe besteht Wiederaufnahmeprüfung nicht: {message}"
            )

    def request_cancel(self) -> None:
        self._cancelled = True

    def run(self, *, checkpoint_stop_after: int = 0) -> dict[str, Any]:
        if not self._state:
            raise LongRenderContractError("Der Langzeitrender wurde nicht vorbereitet.")
        contract = self.contract
        state = self._state
        self._invocation_started = time.monotonic()
        self._accounted_at = self._invocation_started
        self._last_heartbeat = 0.0
        self._timeout_reason = ""
        self._cancelled = False
        if not state.get("started_at"):
            state["started_at"] = utc_now()
        state["state"] = "running"
        append_event(contract, state, "invocation_started", resume_count=state.get("resume_count", 0))
        write_state(contract, state)
        completed_this_invocation = 0
        try:
            for position, spec in enumerate(contract.jobs, start=1):
                record = job_by_id(state, spec.job_id)
                if record.get("state") == "completed":
                    continue
                self._enforce_time_budget(state)
                if self._timeout_reason:
                    return self._pause("paused_timeout", self._timeout_reason)
                if self._cancelled:
                    return self._pause("paused", "Abbruch angefordert")
                output = contract.target_dir / spec.output_name
                record["state"] = "running"
                record["attempts"] = int(record.get("attempts", 0)) + 1
                record["updated_at"] = utc_now()
                state["current_job"] = spec.job_id
                write_state(contract, state)
                job = build_pair_job(spec, output)
                result = self._execute(job, position, len(contract.jobs))
                self._account_elapsed()
                if not result.success:
                    if self._timeout_reason:
                        return self._pause("paused_timeout", self._timeout_reason)
                    if self._cancelled:
                        return self._pause("paused", "Abbruch angefordert")
                    record["state"] = "failed"
                    record["last_error"] = result.message
                    record["updated_at"] = utc_now()
                    append_event(contract, state, "job_failed", job_id=spec.job_id, message=result.message)
                    write_state(contract, state)
                    return self._pause("paused_failure", result.message)
                verify_input_manifest(state.get("input_manifest", {}), full_hash=False)
                record["state"] = "completed"
                record["last_error"] = ""
                record["output_size"] = output.stat().st_size
                record["output_sha256"] = sha256_file(output)
                record["updated_at"] = utc_now()
                completed_this_invocation += 1
                append_event(contract, state, "job_completed", job_id=spec.job_id, output=spec.output_name)
                write_state(contract, state)
                write_heartbeat(contract, state)
                if self._timeout_reason:
                    return self._pause("paused_timeout", self._timeout_reason)
                if self._cancelled:
                    return self._pause("paused", "Abbruch angefordert")
                if checkpoint_stop_after and completed_this_invocation >= checkpoint_stop_after:
                    return self._pause("paused", "Kontrollierter Checkpoint-Stopp")
            return self._complete()
        except KeyboardInterrupt:
            self.request_cancel()
            return self._pause("paused", "Tastaturabbruch")
        except Exception as exc:
            return self._finish("failed", "run_failed", f"{type(exc).__name__}: {exc}")

    def _execute(self, job: PairJob, position: int, total: int) -> JobResult:
        state = self._state
        options = batch_options(self.contract)

        def emit(_name: str, payload: dict[str, Any]) -> None:
            snapshot = payload.get("snapshot")
            if isinstance(snapshot, ProgressSnapshot):
                state["last_progress"] = {
                    "job": state.get("current_job"),
                    "position": position,
                    "total": total,
                    "job_percent": round(snapshot.job_percent, 3),
                    "total_percent": round(
                        ((position - 1) + snapshot.job_percent / 100) / max(1, total) * 100,
                        3,
                    ),
                    "elapsed_seconds": round(snapshot.elapsed_seconds, 3),
                    "output_size": snapshot.output_size,
                    "speed": snapshot.speed,
                }
            self._heartbeat_if_due()
            self._enforce_time_budget(state, raise_on_total=False)

        if self.executor is not None:
            return self.executor(job, options, emit, lambda: self._cancelled)
        hard_limits = self.contract.target_policy.require_hard_limits and not self.allow_soft_limits
        return execute_job(
            job,
            options,
            emit,
            lambda: self._cancelled,
            hard_limits=hard_limits,
            limits=self.contract.limits,
        )

    def _heartbeat_if_due(self) -> None:
        now = time.monotonic()
        if self._last_heartbeat and now - self._last_heartbeat < self.contract.limits.heartbeat_seconds:
            return
        self._last_heartbeat = now
        self._account_elapsed(now)
        write_state(self.contract, self._state)
        write_heartbeat(self.contract, self._state)

    def _account_elapsed(self, now: float | None = None) -> None:
        current = now if now is not None else time.monotonic()
        if self._accounted_at <= 0:
            self._accounted_at = current
            return
        delta = max(0.0, current - self._accounted_at)
        self._state["elapsed_seconds"] = round(
            float(self._state.get("elapsed_seconds", 0.0)) + delta,
            3,
        )
        self._accounted_at = current

    def _enforce_time_budget(self, state: dict[str, Any], *, raise_on_total: bool = True) -> None:
        now = time.monotonic()
        invocation_elapsed = now - self._invocation_started
        total = float(state.get("elapsed_seconds", 0.0)) + max(0.0, now - self._accounted_at)
        if invocation_elapsed >= self.contract.limits.invocation_timeout_seconds:
            self._timeout_reason = (
                "Definierter Aufruf-Timeout wurde erreicht; Zustand ist wiederaufnehmbar."
            )
            self.request_cancel()
        if total >= self.contract.limits.total_timeout_seconds:
            self.request_cancel()
            if raise_on_total:
                raise LongRenderContractError("Gesamt-Timeout des Abnahmevertrags wurde erreicht.")
            self._timeout_reason = "Gesamt-Timeout des Abnahmevertrags wurde erreicht."

    def _pause(self, state_name: str, reason: str) -> dict[str, Any]:
        self._account_elapsed()
        state = self._state
        state["state"] = state_name
        state["current_job"] = ""
        append_event(self.contract, state, "invocation_paused", reason=reason)
        write_state(self.contract, state)
        write_heartbeat(self.contract, state)
        return state

    def _finish(self, state_name: str, terminal_event: str, reason: str) -> dict[str, Any]:
        self._account_elapsed()
        state = self._state
        state["state"] = state_name
        state["terminal_event"] = terminal_event
        state["terminal_reason"] = reason
        state["current_job"] = ""
        state["finished_at"] = utc_now()
        append_event(self.contract, state, terminal_event, reason=reason)
        write_state(self.contract, state)
        write_heartbeat(self.contract, state)
        release_reservations(self.contract)
        return state

    def _complete(self) -> dict[str, Any]:
        self._account_elapsed()
        state = self._state
        verify_input_manifest(state.get("input_manifest", {}), full_hash=True)
        outputs: list[dict[str, Any]] = []
        for spec in self.contract.jobs:
            record = job_by_id(state, spec.job_id)
            output = self.contract.target_dir / spec.output_name
            self._verify_completed_output(spec.job_id, output, record)
            outputs.append(
                {
                    "job_id": spec.job_id,
                    "path": str(output),
                    "size": record["output_size"],
                    "sha256": record["output_sha256"],
                }
            )
        state["output_manifest"] = {"entries": outputs, "digest": canonical_hash(outputs)}
        state["state"] = "completed"
        state["terminal_event"] = "run_completed"
        state["current_job"] = ""
        state["finished_at"] = utc_now()
        append_event(self.contract, state, "run_completed", output_count=len(outputs))
        write_state(self.contract, state)
        write_heartbeat(self.contract, state)
        release_reservations(self.contract)
        self._write_report()
        return state

    def _write_report(self) -> None:
        state = self._state
        report = {
            "schema_version": 1,
            "run_id": state.get("run_id"),
            "candidate": state.get("candidate"),
            "status": state.get("state"),
            "terminal_event": state.get("terminal_event"),
            "started_at": state.get("started_at"),
            "finished_at": state.get("finished_at"),
            "elapsed_seconds": state.get("elapsed_seconds"),
            "resume_count": state.get("resume_count"),
            "target": state.get("target"),
            "limits": state.get("limits"),
            "input_manifest_digest": (state.get("input_manifest") or {}).get("digest"),
            "output_manifest": state.get("output_manifest"),
            "jobs": state.get("jobs"),
            "rehearsal_only": bool(state.get("rehearsal_only")),
        }
        atomic_write_json(state_directory(self.contract) / "final-report.json", report)


def install_signal_handlers(controller: LongRenderAcceptance) -> None:
    def handler(_signum: int, _frame: Any) -> None:
        controller.request_cancel()

    signal.signal(signal.SIGINT, handler)
    signal.signal(signal.SIGTERM, handler)


__all__ = [
    "LongRenderAcceptance",
    "LongRenderContractError",
    "_reservation_path",
    "install_signal_handlers",
    "load_contract",
]
