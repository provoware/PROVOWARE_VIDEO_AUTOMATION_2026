from __future__ import annotations

import os
import subprocess
import sys
import threading
import time
from pathlib import Path

from videobatch_fast.models import JobResult, MediaInfo, PairJob
from videobatch_fast.retry_policy import classify_retry
from videobatch_fast.runner import BatchRunner, terminate_process_group
from videobatch_fast.runner_process import ProcessExecution


ROOT = Path(__file__).resolve().parents[1]


def _job(output: Path) -> PairJob:
    audio = output.with_suffix(".wav")
    media = output.with_suffix(".mp4")
    return PairJob(
        index=1,
        audio=audio,
        media=media,
        output=output,
        audio_info=MediaInfo(audio, "audio", duration=2.0),
        media_info=MediaInfo(media, "video", duration=2.0),
        fast_path=False,
        reason="CP-09 evidence fixture",
    )


def _executor(*, cancelled=lambda: False, warning_timeout: float = 0.2, stall_timeout: float = 0.8):
    process_refs: list[subprocess.Popen[str] | None] = []
    events: list[tuple[str, dict[str, object]]] = []

    def emit(name: str, **payload: object) -> None:
        events.append((name, payload))

    execution = ProcessExecution(
        emit=emit,
        cancelled=cancelled,
        set_process=process_refs.append,
        terminate=terminate_process_group,
        cpu_ticks=lambda _pid: 0,
        warning_timeout=warning_timeout,
        stall_timeout=stall_timeout,
    )
    return execution, process_refs, events


def _pid_active(pid: int) -> bool:
    stat = Path(f"/proc/{pid}/stat")
    if not stat.exists():
        return False
    try:
        fields = stat.read_text(encoding="utf-8").split()
    except OSError:
        return False
    return len(fields) > 2 and fields[2] != "Z"


def test_normal_completion_leaves_no_ffmpeg_reader_threads(tmp_path: Path) -> None:
    output = tmp_path / "normal.out"
    execution, refs, _events = _executor(warning_timeout=1.0, stall_timeout=4.0)
    command = [
        sys.executable,
        "-c",
        "import sys; print('out_time_us=1000000', flush=True); "
        "print('progress=end', flush=True); print('diagnostic', file=sys.stderr, flush=True)",
    ]

    result = execution.run(command, _job(output), 1, 1)

    assert result.success is True
    assert refs and refs[-1] is None
    leaked = [
        thread.name
        for thread in threading.enumerate()
        if thread.name in {"ffmpeg-stdout", "ffmpeg-stderr"} and thread.is_alive()
    ]
    assert leaked == []


def test_watchdog_does_not_kill_when_output_keeps_growing(tmp_path: Path) -> None:
    output = tmp_path / "growing.out"
    execution, _refs, events = _executor(warning_timeout=0.2, stall_timeout=0.8)
    script = (
        "import pathlib,time; p=pathlib.Path(r'" + str(output) + "'); "
        "f=p.open('wb'); "
        "\nfor _ in range(6):\n f.write(b'x'*4096); f.flush(); time.sleep(0.22)\n"
        "f.close()"
    )

    result = execution.run([sys.executable, "-c", script], _job(output), 1, 1)

    assert result.success is True
    assert "kontrolliert beendet" not in result.message.casefold()
    assert not any(
        name == "log" and "kontrolliert beendet" in str(payload.get("message", "")).casefold()
        for name, payload in events
    )


def test_watchdog_reproducibly_stops_true_stall(tmp_path: Path) -> None:
    output = tmp_path / "stall.out"
    execution, _refs, events = _executor(warning_timeout=0.2, stall_timeout=0.8)

    started = time.monotonic()
    result = execution.run(
        [sys.executable, "-c", "import time; time.sleep(30)"],
        _job(output),
        1,
        1,
    )
    elapsed = time.monotonic() - started

    assert result.success is False
    assert elapsed < 5.0
    assert "kontrolliert beendet" in result.message.casefold()
    assert any(
        name == "log" and payload.get("level") == "error"
        for name, payload in events
    )


def test_process_group_termination_stops_spawned_child(tmp_path: Path) -> None:
    child_pid_file = tmp_path / "child.pid"
    script = (
        "import pathlib,subprocess,sys,time; "
        "child=subprocess.Popen([sys.executable,'-c','import time; time.sleep(30)']); "
        f"pathlib.Path(r'{child_pid_file}').write_text(str(child.pid), encoding='utf-8'); "
        "time.sleep(30)"
    )
    process = subprocess.Popen(
        [sys.executable, "-c", script],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
    )
    try:
        deadline = time.monotonic() + 3.0
        while not child_pid_file.exists() and time.monotonic() < deadline:
            time.sleep(0.05)
        assert child_pid_file.exists()
        child_pid = int(child_pid_file.read_text(encoding="utf-8"))

        terminate_process_group(process, term_timeout=1.0, kill_timeout=1.0)
        deadline = time.monotonic() + 3.0
        while _pid_active(child_pid) and time.monotonic() < deadline:
            time.sleep(0.05)

        assert process.poll() is not None
        assert _pid_active(child_pid) is False
    finally:
        if process.poll() is None:
            terminate_process_group(process, term_timeout=0.2, kill_timeout=0.2)


def test_internal_exception_cleanup_removes_incomplete_output(tmp_path: Path) -> None:
    output = tmp_path / "partial.mp4"
    output.write_bytes(b"incomplete")
    runner = BatchRunner(lambda _event: None)

    safe, protection = runner._recover_after_job_exception(_job(output))

    assert safe is True
    assert output.exists() is False
    assert "entfernt" in protection.casefold()


def test_fallback_policy_blocks_known_unsafe_failure_classes(tmp_path: Path) -> None:
    job = _job(tmp_path / "policy.mp4")
    blocked = [
        JobResult(job, False, 143, 1.0, "Vom Nutzer abgebrochen."),
        JobResult(job, False, 1, 1.0, "No space left on device"),
        JobResult(job, False, 1, 1.0, "Invalid data found when processing input"),
        JobResult(job, False, 1, 1.0, "I/O error"),
    ]
    for result in blocked:
        assert classify_retry(result).safe_fallback_allowed is False

    verification = JobResult(job, False, 0, 1.0, "Ausgabeprüfung fehlgeschlagen")
    assert classify_retry(verification).safe_fallback_allowed is True


def test_ffprobe_preparation_is_dispatched_off_qt_main_thread() -> None:
    source = (ROOT / "src/videobatch_fast/qt_ui.py").read_text(encoding="utf-8")

    assert "def prepare() -> None:" in source
    assert "jobs = build_jobs(audios, media, options)" in source
    assert 'threading.Thread(target=prepare' in source
    assert 'name="VideoBatch-Qt-Prepare"' in source
