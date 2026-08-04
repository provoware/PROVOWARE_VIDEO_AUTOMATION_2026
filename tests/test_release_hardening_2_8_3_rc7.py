from __future__ import annotations

import json
import subprocess
import threading
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import pytest

from videobatch_fast.event_buffer import EventBuffer
from videobatch_fast.ffmpeg_capabilities import _parse_encoders, _parse_filters, required_filter_names
from videobatch_fast.instance_lock import ApplicationLock, InstanceAlreadyRunning
from videobatch_fast.job_journal import BatchJournal, recoverable_batches
from videobatch_fast.models import JobResult, MediaInfo, PairJob
from videobatch_fast.runner_process import ProcessExecution, _ProgressState
from videobatch_fast.safe_io import atomic_write_json, quarantine_file, read_json
from videobatch_fast.task_manager import TaskManager
from videobatch_fast.text_resources import SUPPORTED_CATALOG_VERSION, text, validate_text_resources
from videobatch_fast.verification import verify_output

ROOT = Path(__file__).parents[1]


def _job(root: Path, index: int = 1) -> PairJob:
    audio = root / f"audio-{index}.wav"
    medium = root / f"image-{index}.png"
    output = root / f"output-{index}.mp4"
    audio.write_bytes(b"a")
    medium.write_bytes(b"i")
    return PairJob(
        index,
        audio,
        medium,
        output,
        MediaInfo(audio, "audio", duration=10.0),
        MediaInfo(medium, "image"),
        False,
        "test",
    )


def test_atomic_json_and_quarantine_are_durable(tmp_path: Path) -> None:
    target = tmp_path / "state.json"
    atomic_write_json(target, {"value": "ok"})
    assert read_json(target) == {"value": "ok"}
    assert target.stat().st_mode & 0o777 == 0o600
    quarantined = quarantine_file(target, label="broken")
    assert quarantined is not None and quarantined.is_file()
    assert not target.exists()
    assert "broken" in quarantined.name


def test_application_lock_blocks_second_instance(tmp_path: Path) -> None:
    path = tmp_path / "app.lock"
    first = ApplicationLock(path).acquire()
    try:
        with pytest.raises(InstanceAlreadyRunning, match="läuft bereits"):
            ApplicationLock(path).acquire()
    finally:
        first.release()
    ApplicationLock(path).acquire().release()


def test_batch_journal_tracks_and_recovers_active_jobs(tmp_path: Path) -> None:
    job = _job(tmp_path)
    with mock.patch("videobatch_fast.job_journal.state_dir", return_value=tmp_path / "state"):
        journal = BatchJournal("operation", [job])
        journal.mark_started(job.index)
        active = recoverable_batches()
        assert active[0]["recoverable_jobs"] == 1
        result = JobResult(job, False, 9, 1.2, "Fehler", retried=True)
        journal.mark_finished(result)
        destination = journal.finish(terminal_event="batch_finished", cancelled=False)
        payload = json.loads(destination.read_text(encoding="utf-8"))
    assert payload["jobs"][0]["state"] == "failed"
    assert payload["jobs"][0]["last_error"] == "Fehler"
    assert not list((tmp_path / "state" / "jobs" / "active").glob("*.json"))


def test_watchdog_terminates_process_without_activity(tmp_path: Path) -> None:
    events: list[tuple[str, dict]] = []
    execution = ProcessExecution(
        emit=lambda name, **payload: events.append((name, payload)),
        cancelled=lambda: False,
        set_process=lambda process: None,
        terminate=lambda process: 143,
        cpu_ticks=lambda pid: 1,
        warning_timeout=1.0,
        stall_timeout=5.0,
    )
    process = SimpleNamespace(pid=123, returncode=None, poll=lambda: None)
    state = _ProgressState(started=0.0, duration=10.0, last_progress=0.0, last_ticks=1)
    with mock.patch("videobatch_fast.runner_process.time.monotonic", return_value=10.0):
        code = execution._monitor(process, __import__("queue").Queue(), state, ["ffmpeg"], _job(tmp_path), 1, 1)
    assert code == 143
    assert "kontrolliert beendet" in state.watchdog_message
    assert any(name == "log" and payload.get("level") == "error" for name, payload in events)


def test_event_buffer_coalesces_progress_and_preserves_terminal_event() -> None:
    buffer = EventBuffer(maxsize=10)
    for value in range(30):
        buffer.put(("progress", {"value": value}))
    buffer.put(("batch_finished", {"ok": True}))
    items = []
    while True:
        try:
            items.append(buffer.get_nowait())
        except __import__("queue").Empty:
            break
    assert items[-1][0] == "batch_finished"
    progress = [item for item in items if item[0] == "progress"]
    assert len(progress) == 1 and progress[0][1]["value"] == 29


def test_task_manager_prevents_duplicate_and_waits() -> None:
    manager = TaskManager()
    release = threading.Event()
    assert manager.start("same", lambda: release.wait(0.2))
    assert not manager.start("same", lambda: None)
    release.set()
    assert manager.shutdown(timeout=1.0) == ()


def test_text_contract_has_no_missing_or_embedded_static_ui_texts() -> None:
    assert validate_text_resources(ROOT) == []
    manifest = json.loads((ROOT / "resources" / "texts" / "de.json").read_text(encoding="utf-8"))
    assert manifest["catalog_version"] == SUPPORTED_CATALOG_VERSION
    assert len(manifest["files"]) > 1
    assert text("app.title") == "provoware - videoautomation - 2026"
    assert text("ui.area_zoom.label") == "Tab-Zoom für Text und Bedienelemente"
    assert text("ui.settings.global_zoom") == "Globaler Zoom für die ganze Oberfläche"
    zoom_note = text("ui.settings.zoom_note")
    assert "ganze Oberfläche" in zoom_note
    assert "jeweiligen Bereich" in zoom_note
    assert "Text und Bedienelemente" in zoom_note


def test_ffmpeg_capability_parsers_and_required_filters() -> None:
    encoders = _parse_encoders(" V..... libx264 H.264\n A..... aac AAC")
    filters = _parse_filters(" T.. fade V->V\n ... eq V->V\n ... unsharp V->V")
    assert {"libx264", "aac"}.issubset(encoders)
    assert {"fade", "eq", "unsharp"}.issubset(filters)
    assert {"eq", "unsharp", "fade"}.issubset(required_filter_names("hardtechno", "soft"))


def test_full_output_verification_decodes_complete_file(tmp_path: Path) -> None:
    job = _job(tmp_path)
    output = job.output
    output.write_bytes(b"x" * 60_000)
    probe = SimpleNamespace(
        stdout=json.dumps(
            {
                "streams": [
                    {"codec_type": "video", "codec_name": "h264", "duration": "10"},
                    {"codec_type": "audio", "codec_name": "aac", "duration": "10"},
                ],
                "format": {"duration": "10"},
            }
        ),
        stderr="",
        returncode=0,
    )
    decode = SimpleNamespace(stdout="", stderr="", returncode=0)
    with (
        mock.patch("videobatch_fast.verification.ffprobe_path", return_value="ffprobe"),
        mock.patch("videobatch_fast.verification.ffmpeg_path", return_value="ffmpeg"),
        mock.patch("videobatch_fast.verification.subprocess.run", side_effect=[probe, decode]) as run,
    ):
        valid, message = verify_output(output, job, "Vollständig")
    assert valid and "vollständig dekodiert" in message
    assert "-xerror" in run.call_args_list[1].args[0]


def test_full_output_verification_rejects_decode_error(tmp_path: Path) -> None:
    job = _job(tmp_path)
    output = job.output
    output.write_bytes(b"x" * 60_000)
    probe = SimpleNamespace(
        stdout=json.dumps(
            {
                "streams": [
                    {"codec_type": "video", "duration": "10"},
                    {"codec_type": "audio", "duration": "10"},
                ],
                "format": {"duration": "10"},
            }
        ),
        stderr="",
        returncode=0,
    )
    decode = SimpleNamespace(stdout="", stderr="invalid frame", returncode=1)
    with (
        mock.patch("videobatch_fast.verification.ffprobe_path", return_value="ffprobe"),
        mock.patch("videobatch_fast.verification.ffmpeg_path", return_value="ffmpeg"),
        mock.patch("videobatch_fast.verification.subprocess.run", side_effect=[probe, decode]),
    ):
        valid, message = verify_output(output, job, "Vollständig")
    assert not valid and "Dekodierfehler" in message


def test_recovery_requeues_only_unfinished_inputs_and_preserves_options(tmp_path, monkeypatch):
    from videobatch_fast import job_journal
    from videobatch_fast.models import BatchOptions, MediaInfo, PairJob

    monkeypatch.setattr(job_journal, "state_dir", lambda: tmp_path)
    audio1, audio2 = tmp_path / "a1.wav", tmp_path / "a2.wav"
    media1, media2 = tmp_path / "m1.png", tmp_path / "m2.png"
    for path in (audio1, audio2, media1, media2):
        path.write_bytes(b"fixture")
    jobs = [
        PairJob(1, audio1, media1, tmp_path / "o1.mp4", MediaInfo(audio1, "audio"), MediaInfo(media1, "image"), False, "test"),
        PairJob(2, audio2, media2, tmp_path / "o2.mp4", MediaInfo(audio2, "audio"), MediaInfo(media2, "image"), False, "test"),
    ]
    journal = job_journal.BatchJournal("recover", jobs, BatchOptions(tmp_path / "out", codec="libx265", quick_mode="safe"))
    journal.mark_started(1)
    journal.mark_finished(JobResult(jobs[0], True, 0, 1.0, "ok"))
    payloads = job_journal.recoverable_batches()
    audio, media = job_journal.recovery_input_paths(payloads)
    assert audio == [audio2]
    assert media == [media2]
    assert job_journal.recovery_options(payloads)["codec"] == "libx265"
    archived = job_journal.acknowledge_recovery(payloads[0]["journal_path"], action="controlled_requeue")
    saved = json.loads(archived.read_text(encoding="utf-8"))
    assert saved["state"] == "recovered"
    assert saved["recovery_action"] == "controlled_requeue"
    assert not journal.path.exists() or journal.path == archived
