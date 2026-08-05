from __future__ import annotations

import errno
import json
import os
import signal
import subprocess
import tempfile
import time
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable, Iterator

from .config import DEFAULT_CONFIG, normalize_config
from .job_journal import BatchJournal, recovery_input_paths
from .models import BatchOptions, JobResult, MediaInfo, PairJob
from .runner import terminate_process_group
from .runner_process import ProcessExecution
from .safe_io import atomic_write_json, atomic_write_text, quarantine_file
from .validation import validate_output_dir


@dataclass(frozen=True, slots=True)
class FaultLabResult:
    scenario_id: str
    status: str
    message: str
    duration_seconds: float
    evidence: str = ""


@contextmanager
def _environment(**values: str) -> Iterator[None]:
    previous = {key: os.environ.get(key) for key in values}
    os.environ.update(values)
    try:
        yield
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def _job(root: Path, index: int = 1, *, duration: float = 2.0) -> PairJob:
    root.mkdir(parents=True, exist_ok=True)
    audio = root / f"audio-{index}.wav"
    media = root / f"media-{index}.png"
    audio.write_bytes(b"audio")
    media.write_bytes(b"media")
    return PairJob(
        index=index,
        audio=audio,
        media=media,
        output=root / f"output-{index}.mp4",
        audio_info=MediaInfo(audio, "audio", duration=duration, size_bytes=5),
        media_info=MediaInfo(media, "image", size_bytes=5),
        fast_path=False,
        reason="fault-lab",
    )


def _result(scenario_id: str, started: float, ok: bool, message: str, evidence: str = "") -> FaultLabResult:
    return FaultLabResult(scenario_id, "pass" if ok else "fail", message, round(time.monotonic() - started, 3), evidence)


def _atomic_write_disk_full(root: Path) -> FaultLabResult:
    from . import safe_io
    started = time.monotonic()
    target = root / "disk-full.json"
    target.write_text("original", encoding="utf-8")
    original = safe_io.os.replace
    def fail_replace(_source, _target):
        raise OSError(errno.ENOSPC, "No space left on device")
    safe_io.os.replace = fail_replace
    caught = False
    try:
        atomic_write_text(target, "new")
    except OSError as exc:
        caught = exc.errno == errno.ENOSPC
    finally:
        safe_io.os.replace = original
    leftovers = list(root.glob(".disk-full.json.*.tmp"))
    ok = caught and target.read_text(encoding="utf-8") == "original" and not leftovers
    return _result("atomic_write_disk_full", started, ok, "Original bleibt bei simuliertem ENOSPC unverändert.")


def _atomic_write_interrupted(root: Path) -> FaultLabResult:
    started = time.monotonic()
    target = root / "interrupted.json"
    target.write_text("old", encoding="utf-8")
    stale = root / ".interrupted.json.crash.tmp"
    stale.write_text("partial", encoding="utf-8")
    atomic_write_text(target, "new")
    ok = target.read_text(encoding="utf-8") == "new" and stale.read_text(encoding="utf-8") == "partial"
    stale.unlink(missing_ok=True)
    return _result("atomic_write_interrupted", started, ok, "Unvollständige Tempdatei überschreibt das Ziel nicht.")


def _read_only_output(root: Path) -> FaultLabResult:
    from . import validation
    started = time.monotonic()
    target = root / "readonly"
    target.mkdir()
    original = validation.os.access
    validation.os.access = lambda path, mode: False if Path(path) == target else original(path, mode)
    try:
        issues = validate_output_dir(target)
    finally:
        validation.os.access = original
    ok = any(item.code == "OUTPUT_PERMISSION" for item in issues)
    return _result("read_only_output", started, ok, "Nicht beschreibbares Ziel wird vor dem Rendern blockiert.")


def _removed_external_target(root: Path) -> FaultLabResult:
    started = time.monotonic()
    target = root / "usb-target"
    target.mkdir()
    target.rmdir()
    issues = validate_output_dir(target)
    ok = target.is_dir() and not issues
    return _result("removed_external_target", started, ok, "Verschwundenes leeres Ziel wird kontrolliert neu bereitgestellt.")


def _run_fake_process(root: Path, body: str, *, warning: float = 0.2, stall: float = 0.7) -> tuple[int, str]:
    script = root / "fake-ffmpeg.sh"
    script.write_text("#!/usr/bin/env bash\nset -eu\n" + body + "\n", encoding="utf-8")
    script.chmod(0o755)
    events: list[str] = []
    execution = ProcessExecution(
        emit=lambda name, **payload: events.append(f"{name}:{payload.get('message','')}") ,
        cancelled=lambda: False,
        set_process=lambda _process: None,
        terminate=lambda process: terminate_process_group(process, term_timeout=0.2, kill_timeout=0.2),
        cpu_ticks=lambda _pid: 0,
        warning_timeout=warning,
        stall_timeout=stall,
    )
    result = execution.run([str(script)], _job(root), 1, 1)
    return result.returncode, result.message + "\n" + "\n".join(events)


def _ffmpeg_crash(root: Path) -> FaultLabResult:
    started = time.monotonic()
    returncode, detail = _run_fake_process(root, "echo 'simulated crash' >&2; exit 23")
    return _result("ffmpeg_crash", started, returncode == 23, "FFmpeg-Absturz wird als kontrollierter Jobfehler erfasst.", detail[-1000:])


def _ffmpeg_stall_watchdog(root: Path) -> FaultLabResult:
    started = time.monotonic()
    returncode, detail = _run_fake_process(root, "sleep 5", warning=0.15, stall=0.55)
    ok = returncode != 0 and "kontrolliert beendet" in detail
    return _result("ffmpeg_stall_watchdog", started, ok, "Stillstand wird zeitlich begrenzt beendet.", detail[-1000:])


def _suspend_resume_process(root: Path) -> FaultLabResult:
    started = time.monotonic()
    process = subprocess.Popen(["sleep", "2"], start_new_session=True)
    try:
        os.killpg(process.pid, signal.SIGSTOP)
        time.sleep(0.1)
        stopped = process.poll() is None
        os.killpg(process.pid, signal.SIGCONT)
        process.terminate()
        process.wait(timeout=2)
        ok = stopped
    finally:
        if process.poll() is None:
            process.kill()
    return _result("suspend_resume_process", started, ok, "SIGSTOP/SIGCONT lässt sich ohne verlorenen Prozesszustand behandeln.")


def _hundred_job_journal(root: Path) -> FaultLabResult:
    started = time.monotonic()
    state = root / "state"
    jobs = [_job(root / "jobs", index, duration=1.0) for index in range(1, 101)]
    options = BatchOptions(output_dir=root / "out")
    with _environment(XDG_STATE_HOME=str(state)):
        journal = BatchJournal("fault-lab-100", jobs, options)
        payload = json.loads(journal.path.read_text(encoding="utf-8"))
        ok = len(payload.get("jobs", [])) == 100 and journal.path.stat().st_size < 250_000
        journal.finish(terminal_event="fault_lab", cancelled=True)
    return _result("hundred_job_journal", started, ok, "100 Aufträge werden dauerhaft und kompakt journalisiert.")


def _long_duration_progress(root: Path) -> FaultLabResult:
    from .runner_process import _ProgressState
    started = time.monotonic()
    state = _ProgressState(started=started, duration=8 * 3600, last_progress=started)
    changed = ProcessExecution._set_out_time(str(int(7.5 * 3600 * 1_000_000)), state)
    ok = changed and 26999 <= state.out_time <= 27001
    return _result("long_duration_progress", started, ok, "Acht-Stunden-Zeitwerte bleiben ohne Überlauf auswertbar.")


def _corrupt_configuration_recovery(root: Path) -> FaultLabResult:
    started = time.monotonic()
    normalized = normalize_config({"font_scale": "invalid", "codec": object(), "resolution": None})
    ok = normalized.get("font_scale") == DEFAULT_CONFIG["font_scale"] and normalized.get("codec") == "libx264" and normalized.get("resolution") == "Original"
    return _result("corrupt_configuration_recovery", started, ok, "Beschädigte Werte werden auf sichere Standards normalisiert.")


def _corrupt_project_quarantine(root: Path) -> FaultLabResult:
    started = time.monotonic()
    project = root / "project.json"
    project.write_text("{broken", encoding="utf-8")
    moved = quarantine_file(project, label="fault-lab")
    ok = moved is not None and moved.is_file() and not project.exists()
    return _result("corrupt_project_quarantine", started, ok, "Beschädigtes Projekt wird erhalten und aus dem aktiven Pfad entfernt.", str(moved or ""))


def _recovery_without_duplicate_completed_jobs(root: Path) -> FaultLabResult:
    started = time.monotonic()
    audio_done = root / "done.wav"; media_done = root / "done.png"
    audio_open = root / "open.wav"; media_open = root / "open.png"
    for path in (audio_done, media_done, audio_open, media_open): path.write_bytes(b"x")
    payload = {"jobs": [
        {"state": "completed", "audio": str(audio_done), "media": str(media_done)},
        {"state": "pending", "audio": str(audio_open), "media": str(media_open)},
    ]}
    audio, media = recovery_input_paths([payload])
    ok = audio == [audio_open] and media == [media_open]
    return _result("recovery_without_duplicate_completed_jobs", started, ok, "Abgeschlossene Jobs werden bei Recovery nicht doppelt eingereiht.")


def _retry_queue_attempt_limit(root: Path) -> FaultLabResult:
    from .retry_queue import RetryQueueStore

    started = time.monotonic()
    job = _job(root)
    queue = RetryQueueStore(root / "retry.json", max_entries=4, max_attempts=2)
    first = queue.record_failure(
        JobResult(job, False, 70, 0.1, "ursprünglicher Fehler"),
        operation_id="fault-1",
        protection="Originaldateien geschützt.",
    )
    second = queue.record_failure(
        JobResult(job, False, 70, 0.1, "erneuter Fehler"),
        operation_id="fault-2",
        protection="Prozesszustand bereinigt.",
    )
    ok = (
        first.get("retry_allowed") is True
        and second.get("retry_allowed") is False
        and second.get("state") == "limit_reached"
        and second.get("attempts") == 2
        and second.get("first_error") == "ursprünglicher Fehler"
        and second.get("latest_error") == "erneuter Fehler"
        and not queue.eligible_entries()
    )
    return _result(
        "retry_queue_attempt_limit",
        started,
        ok,
        "Wiederholungen enden nach zwei Fehlversuchen ohne automatische Endlosschleife.",
        str(queue.path),
    )


def _retry_queue_preserves_unstarted(root: Path) -> FaultLabResult:
    from .retry_queue import RetryQueueStore

    started = time.monotonic()
    queue = RetryQueueStore(root / "retry.json", max_entries=4, max_attempts=2)
    entry = queue.record_not_started(
        _job(root),
        operation_id="fault-open",
        reason="Schutzstopp nach vorherigem Auftrag.",
        protection="Dieser Auftrag wurde nicht gestartet; Eingaben blieben unverändert.",
    )
    ok = (
        entry.get("state") == "not_started"
        and entry.get("attempts") == 0
        and entry.get("retry_allowed") is True
        and bool(entry.get("first_error"))
        and bool(entry.get("protection"))
    )
    return _result(
        "retry_queue_preserves_unstarted",
        started,
        ok,
        "Nicht gestartete Aufträge bleiben ohne verbrauchten Versuch nachvollziehbar erhalten.",
        str(queue.path),
    )


def _ui_event_handler_isolation(root: Path) -> FaultLabResult:
    from .ui_event_handlers_mixin import UiEventHandlersMixin

    started = time.monotonic()

    class Value:
        def __init__(self) -> None:
            self.value = ""

        def set(self, value: str) -> None:
            self.value = value

    class Logger:
        def __init__(self) -> None:
            self.calls = 0

        def write(self, *_args, **_kwargs) -> None:
            self.calls += 1

    class FakeUi(UiEventHandlersMixin):
        def __init__(self) -> None:
            self.current_operation_id = "fault-ui"
            self._ui_event_errors: list[str] = []
            self.status_text = Value()
            self.guidance_text = Value()
            self.logger = Logger()
            self.handled: list[str] = []

        def _dispatch_event(self, name: str, payload: dict) -> None:
            if name == "broken":
                raise RuntimeError("simulierter Anzeigehandlerfehler")
            self.handled.append(name)

    ui = FakeUi()
    failed = ui._handle_event_safely("broken", {"operation_id": "fault-ui"})
    continued = ui._handle_event_safely("next", {})
    ok = (
        failed is False
        and continued is True
        and ui.handled == ["next"]
        and len(ui._ui_event_errors) == 1
        and ui.logger.calls == 1
        and "Bedienfehler" in ui.status_text.value
        and "Andere Funktionen" in ui.guidance_text.value
    )
    return _result(
        "ui_event_handler_isolation",
        started,
        ok,
        "Fehlerhafte UI-Ereignisse werden protokolliert; nachfolgende Ereignisse laufen weiter.",
    )


SCENARIOS: tuple[Callable[[Path], FaultLabResult], ...] = (
    _atomic_write_disk_full,
    _atomic_write_interrupted,
    _read_only_output,
    _removed_external_target,
    _ffmpeg_crash,
    _ffmpeg_stall_watchdog,
    _suspend_resume_process,
    _hundred_job_journal,
    _long_duration_progress,
    _corrupt_configuration_recovery,
    _corrupt_project_quarantine,
    _recovery_without_duplicate_completed_jobs,
    _retry_queue_attempt_limit,
    _retry_queue_preserves_unstarted,
    _ui_event_handler_isolation,
)


def run_fault_lab(workspace: Path | None = None) -> list[FaultLabResult]:
    temporary = tempfile.TemporaryDirectory(prefix="videobatch-fault-lab-") if workspace is None else None
    root = Path(temporary.name) if temporary else Path(workspace)
    root.mkdir(parents=True, exist_ok=True)
    results: list[FaultLabResult] = []
    for handler in SCENARIOS:
        scenario_root = root / handler.__name__.lstrip("_")
        scenario_root.mkdir(parents=True, exist_ok=True)
        try:
            results.append(handler(scenario_root))
        except Exception as exc:
            results.append(FaultLabResult(handler.__name__.lstrip("_"), "fail", f"{type(exc).__name__}: {exc}", 0.0))
    if temporary:
        temporary.cleanup()
    return results


def report_payload(results: list[FaultLabResult]) -> dict[str, object]:
    passed = sum(result.status == "pass" for result in results)
    return {"schema_version": 1, "status": "passed" if passed == len(results) else "failed", "passed": passed,
            "failed": len(results) - passed, "total": len(results), "results": [asdict(item) for item in results]}
