from __future__ import annotations

import subprocess
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import pytest

from videobatch_fast.calendar_tasks import (
    CalendarTask,
    CalendarTaskOverview,
    collect_calendar_tasks,
    filter_calendar_tasks,
)
from videobatch_fast.error_handling import error_definition
from videobatch_fast.jobs import build_jobs
from videobatch_fast.media_library import LibraryItem, sort_paths
from videobatch_fast.models import BatchOptions, MediaInfo, PairJob
from videobatch_fast.playlist import AudioPlayer, Playlist
from videobatch_fast.validation import validate_output_dir, validate_pairs, validate_runtime


def test_error_definition_reads_registry_and_falls_back() -> None:
    known = {
        "errors": {
            "E1": {
                "title": "Titel",
                "cause": "Ursache",
                "effect": "Wirkung",
                "automatic_action": "Sicherung",
                "solution": "Lösung",
                "alternative": "Alternative",
                "severity": "warning",
                "actions": ["retry", "", 7],
            }
        }
    }
    with mock.patch("videobatch_fast.error_handling.load_json", return_value=known):
        result = error_definition("E1")
    assert result.title == "Titel"
    assert result.severity == "warning"
    assert result.actions == ("retry", "7")

    with mock.patch("videobatch_fast.error_handling.load_json", return_value={"errors": []}):
        fallback = error_definition("UNKNOWN")
    assert fallback.code == "UNKNOWN"
    assert fallback.severity == "blocking"
    assert fallback.actions == ("open_logs",)


def test_build_jobs_rejects_mismatch_and_builds_reserved_outputs(tmp_path: Path) -> None:
    audio = tmp_path / "audio.wav"
    image = tmp_path / "image.png"
    audio.write_bytes(b"audio")
    image.write_bytes(b"image")
    options = BatchOptions(tmp_path / "out")
    assert build_jobs([audio], [], options) == []

    audio_info = MediaInfo(audio, "audio", duration=5.0)
    image_info = MediaInfo(image, "image")
    output = options.output_dir / "result.mp4"
    with (
        mock.patch("videobatch_fast.jobs.probe_media", side_effect=[audio_info, image_info]),
        mock.patch("videobatch_fast.jobs.unique_output_path", return_value=output) as unique,
        mock.patch("videobatch_fast.jobs.can_use_fast_copy", return_value=(False, "encode")),
    ):
        jobs = build_jobs([audio], [image], options)
    assert options.output_dir.is_dir()
    assert jobs[0].output == output
    assert jobs[0].reason == "encode"
    assert unique.call_args.kwargs["index"] == 1

    beside = BatchOptions(tmp_path / "ignored", output_mode="Neben Mediendatei")
    with (
        mock.patch("videobatch_fast.jobs.probe_media", side_effect=[audio_info, image_info]),
        mock.patch("videobatch_fast.jobs.unique_output_path", return_value=tmp_path / "beside.mp4") as unique,
        mock.patch("videobatch_fast.jobs.can_use_fast_copy", return_value=(True, "copy")),
    ):
        jobs = build_jobs([audio], [image], beside)
    assert jobs[0].fast_path
    assert unique.call_args.args[0] == image.parent


def test_playlist_state_transitions_and_navigation(tmp_path: Path) -> None:
    first = tmp_path / "one.wav"
    second = tmp_path / "two.wav"
    first.write_bytes(b"1")
    second.write_bytes(b"2")
    missing = tmp_path / "missing.wav"

    playlist = Playlist()
    playlist.add([first, first, missing, second])
    assert playlist.items == [first, second]
    assert playlist.current == 0
    assert playlist.next_index() == 1

    playlist.current = 1
    assert playlist.next_index() is None
    playlist.repeat = "all"
    assert playlist.next_index() == 0
    playlist.repeat = "one"
    assert playlist.next_index() == 1
    playlist.repeat = "off"
    playlist.shuffle = True
    with mock.patch("videobatch_fast.playlist.random.choice", return_value=0):
        assert playlist.next_index() == 0

    playlist.remove([99, 1, 1])
    assert playlist.items == [first]
    assert playlist.current == 0
    playlist.remove([0])
    assert playlist.current == -1
    assert playlist.next_index() is None


class _FakeProcess:
    def __init__(self, *, running: bool = True, timeout: bool = False) -> None:
        self.pid = 456
        self.running = running
        self.timeout = timeout
        self.terminated = False
        self.killed = False

    def poll(self) -> int | None:
        return None if self.running else 0

    def terminate(self) -> None:
        self.terminated = True

    def wait(self, timeout: int) -> int:
        if self.timeout:
            raise subprocess.TimeoutExpired("ffplay", timeout)
        self.running = False
        return 0

    def kill(self) -> None:
        self.killed = True
        self.running = False


def test_audio_player_all_control_paths(tmp_path: Path) -> None:
    player = AudioPlayer()
    with mock.patch("videobatch_fast.playlist.shutil.which", return_value=None):
        assert not player.available
        with pytest.raises(RuntimeError, match="FFplay"):
            player.play(tmp_path / "x.wav")

    spawned = _FakeProcess()
    with (
        mock.patch("videobatch_fast.playlist.shutil.which", return_value="/usr/bin/ffplay"),
        mock.patch("videobatch_fast.playlist.subprocess.Popen", return_value=spawned) as popen,
    ):
        player.play(tmp_path / "x.wav")
    assert player.available or popen.called
    assert player.process is spawned
    assert "-nodisp" in popen.call_args.args[0]

    with mock.patch("videobatch_fast.playlist.os.killpg") as killpg:
        assert player.toggle_pause()
        assert not player.toggle_pause()
    assert killpg.call_count == 2

    player.stop()
    assert spawned.terminated
    assert player.process is None
    assert not player.paused
    assert not player.toggle_pause()

    timed_out = _FakeProcess(timeout=True)
    player.process = timed_out
    player.paused = True
    player.stop()
    assert timed_out.terminated and timed_out.killed


def test_validation_runtime_output_and_pair_failures(tmp_path: Path) -> None:
    with (
        mock.patch("videobatch_fast.validation.validate_quick_modes", return_value=["Modus kaputt"]),
        mock.patch("videobatch_fast.validation.ffmpeg_path", return_value=""),
        mock.patch("videobatch_fast.validation.ffprobe_path", return_value=""),
    ):
        codes = [issue.code for issue in validate_runtime()]
    assert codes == ["QUICK_MODE_INVALID", "FFMPEG_MISSING", "FFPROBE_MISSING"]

    blocked = tmp_path / "blocked"
    with mock.patch("pathlib.Path.mkdir", side_effect=PermissionError("verweigert")):
        assert validate_output_dir(blocked)[0].code == "OUTPUT_CREATE_FAILED"

    writable = tmp_path / "writable"
    writable.mkdir()
    with mock.patch("videobatch_fast.validation.os.access", return_value=False):
        assert validate_output_dir(writable)[0].code == "OUTPUT_PERMISSION"

    options = BatchOptions(tmp_path, quick_mode="unknown")
    with (
        mock.patch("videobatch_fast.validation.validate_runtime", return_value=[]),
        mock.patch("videobatch_fast.validation.validate_output_dir", return_value=[]),
    ):
        empty_codes = [issue.code for issue in validate_pairs([], options)]
    assert empty_codes == ["QUICK_MODE_UNKNOWN", "NO_JOBS"]

    audio = tmp_path / "missing.wav"
    medium = tmp_path / "missing.bin"
    output = tmp_path / "nested" / "out.mp4"
    job = PairJob(
        1,
        audio,
        medium,
        output,
        MediaInfo(audio, "unknown", duration=1000.0),
        MediaInfo(medium, "unknown"),
        False,
        "",
    )
    with (
        mock.patch("videobatch_fast.validation.validate_runtime", return_value=[]),
        mock.patch("videobatch_fast.validation.validate_output_dir", return_value=[]),
        mock.patch("videobatch_fast.validation.shutil.disk_usage", return_value=SimpleNamespace(free=1)),
    ):
        codes = {issue.code for issue in validate_pairs([job], BatchOptions(tmp_path, quick_mode="custom"))}
    assert {"AUDIO_MISSING", "MEDIA_MISSING", "AUDIO_INVALID", "MEDIA_INVALID", "DISK_LOW"} <= codes

    with (
        mock.patch("videobatch_fast.validation.validate_runtime", return_value=[]),
        mock.patch("videobatch_fast.validation.validate_output_dir", return_value=[]),
        mock.patch("videobatch_fast.validation.shutil.disk_usage", side_effect=OSError("weg")),
    ):
        assert validate_pairs([job], BatchOptions(tmp_path, quick_mode="custom"))


def test_media_library_all_sort_contracts(tmp_path: Path) -> None:
    paths = [tmp_path / "b.mp4", tmp_path / "a.wav", tmp_path / "missing.bin"]
    items = {
        paths[0]: LibraryItem(paths[0], 0, 20, 20.0, None, 12.0, "video", True),
        paths[1]: LibraryItem(paths[1], 1, 10, 10.0, 30.0, 2.0, "audio", True),
        paths[2]: LibraryItem(paths[2], 2, 0, 0.0, None, None, "unknown", False),
    }
    with mock.patch("videobatch_fast.media_library.item_for", side_effect=lambda path, index: items[path]):
        for key in (
            "import",
            "name_asc",
            "name_desc",
            "size_asc",
            "size_desc",
            "modified_new",
            "modified_old",
            "created_new",
            "created_old",
            "duration_short",
            "duration_long",
            "type",
            "not-known",
        ):
            result = sort_paths(paths, key)
            assert sorted(result) == sorted(paths)
            if key != "import" and key != "not-known":
                assert result[-1] == paths[2]


def test_calendar_collection_filters_and_refresh() -> None:
    notes = {
        "2026-08-02": {"entry_type": "task", "color": "active", "note": " Bauen "},
        "2026-08-03": {"entry_type": "appointment", "color": "warning", "note": "Prüfen"},
        "2026-09-01": {"entry_type": "note", "color": "success", "note": "Archiv"},
        "bad": {"note": "ungültig"},
        "2026-08-04": "kein Objekt",
        "2026-08-05": {"note": "  "},
    }
    tasks = collect_calendar_tasks(notes)
    assert [item.note for item in tasks] == ["Bauen", "Prüfen", "Archiv"]
    today = date(2026, 8, 2)
    assert len(filter_calendar_tasks(tasks, "today", today)) == 1
    assert len(filter_calendar_tasks(tasks, "week", today)) == 2
    assert len(filter_calendar_tasks(tasks, "month", today)) == 2
    assert len(filter_calendar_tasks(tasks, "tasks", today)) == 1
    assert len(filter_calendar_tasks(tasks, "appointments", today)) == 1
    assert len(filter_calendar_tasks(tasks, "open", today)) == 2
    assert filter_calendar_tasks(tasks, "all", today) == tasks
    assert tasks[0].type_label == "Aufgabe"
    assert tasks[0].status_label == "Aktiv"
    custom = CalendarTask("x", today, "custom", "custom", "x")
    assert custom.type_label == "custom"
    assert custom.status_label == "custom"

    class Value:
        def __init__(self, value: str = "") -> None:
            self.value = value

        def get(self) -> str:
            return self.value

        def set(self, value: str) -> None:
            self.value = value

    class Tree:
        def __init__(self) -> None:
            self.rows: list[tuple] = [("old",)]

        def get_children(self) -> tuple[str, ...]:
            return ("old",)

        def delete(self, *items: str) -> None:
            self.rows.clear()

        def insert(self, parent: str, where: str, *, values: tuple) -> None:
            self.rows.append(values)

    overview = object.__new__(CalendarTaskOverview)
    overview.tasks = tasks
    overview.filter_var = Value("Nur Aufgaben")
    overview.summary = Value()
    overview.tree = Tree()
    overview.refresh()
    assert len(overview.tree.rows) == 1
    assert overview.summary.value == "1 von 3 Einträgen"


def _verification_job(tmp_path: Path, duration: float = 10.0) -> PairJob:
    audio = tmp_path / "audio.wav"
    medium = tmp_path / "image.png"
    return PairJob(
        1,
        audio,
        medium,
        tmp_path / "out.mp4",
        MediaInfo(audio, "audio", duration=duration),
        MediaInfo(medium, "image"),
        False,
        "",
    )


def test_output_verification_contract_paths(tmp_path: Path) -> None:
    from videobatch_fast.verification import verify_output

    output = tmp_path / "out.mp4"
    job = _verification_job(tmp_path)
    assert not verify_output(output, job)[0]
    output.write_bytes(b"x" * 5_000)

    with mock.patch("videobatch_fast.verification.ffprobe_path", return_value=""):
        assert verify_output(output, job)[1] == "FFprobe fehlt."

    with (
        mock.patch("videobatch_fast.verification.ffprobe_path", return_value="ffprobe"),
        mock.patch("videobatch_fast.verification.subprocess.run", side_effect=OSError("kaputt")),
    ):
        assert "nicht geprüft" in verify_output(output, job)[1]

    def result(payload: dict) -> SimpleNamespace:
        return SimpleNamespace(stdout=__import__("json").dumps(payload))

    cases = [
        ({"streams": [{"codec_type": "video"}], "format": {"duration": "10"}}, "fehlt"),
        ({"streams": [{"codec_type": "video"}, {"codec_type": "audio"}], "format": {"duration": "bad"}}, "ungültig"),
        ({"streams": [{"codec_type": "video"}, {"codec_type": "audio"}], "format": {"duration": "5"}}, "zu kurz"),
    ]
    for payload, message in cases:
        with (
            mock.patch("videobatch_fast.verification.ffprobe_path", return_value="ffprobe"),
            mock.patch("videobatch_fast.verification.subprocess.run", return_value=result(payload)),
        ):
            assert message in verify_output(output, job)[1]

    valid = {"streams": [{"codec_type": "video"}, {"codec_type": "audio"}], "format": {"duration": "10"}}
    with (
        mock.patch("videobatch_fast.verification.ffprobe_path", return_value="ffprobe"),
        mock.patch("videobatch_fast.verification.subprocess.run", return_value=result(valid)),
    ):
        assert "ungewöhnlich klein" in verify_output(output, job, "Vollständig")[1]
        ok, message = verify_output(output, job)
    assert ok and "10.0 Sekunden" in message


def test_preview_generation_and_recovery_paths(tmp_path: Path) -> None:
    from videobatch_fast.preview_service import PreviewError, build_preview, preview_cache_path

    source = tmp_path / "source.mp4"
    source.write_bytes(b"source")
    with mock.patch("videobatch_fast.preview_service.cache_dir", return_value=tmp_path / "cache"):
        first = preview_cache_path(source, 640)
        second = preview_cache_path(source, 640)
    assert first == second
    assert first.parent.is_dir()

    with pytest.raises(PreviewError, match="nicht erreichbar"):
        build_preview(tmp_path / "missing.mp4")
    with mock.patch("videobatch_fast.preview_service.ffmpeg_path", return_value=""):
        with pytest.raises(PreviewError, match="FFmpeg"):
            build_preview(source)

    cached = tmp_path / "cached.png"
    cached.write_bytes(b"x" * 101)
    with (
        mock.patch("videobatch_fast.preview_service.ffmpeg_path", return_value="ffmpeg"),
        mock.patch("videobatch_fast.preview_service.preview_cache_path", return_value=cached),
    ):
        assert build_preview(source) == cached

    target = tmp_path / "target.png"
    with (
        mock.patch("videobatch_fast.preview_service.ffmpeg_path", return_value="ffmpeg"),
        mock.patch("videobatch_fast.preview_service.preview_cache_path", return_value=target),
        mock.patch("videobatch_fast.preview_service.probe_media", return_value=MediaInfo(source, "audio")),
    ):
        with pytest.raises(PreviewError, match="Dateityp"):
            build_preview(source)

    def successful_run(command: list[str], **_kwargs: object) -> SimpleNamespace:
        Path(command[-1]).write_bytes(b"p" * 101)
        return SimpleNamespace(returncode=0, stderr="")

    with (
        mock.patch("videobatch_fast.preview_service.ffmpeg_path", return_value="ffmpeg"),
        mock.patch("videobatch_fast.preview_service.preview_cache_path", return_value=target),
        mock.patch("videobatch_fast.preview_service.probe_media", return_value=MediaInfo(source, "video")),
        mock.patch("videobatch_fast.preview_service.subprocess.run", side_effect=successful_run) as runner,
    ):
        assert build_preview(source, 100) == target
    command = runner.call_args.args[0]
    assert "-ss" in command
    assert "min(320,iw)" in command[command.index("-vf") + 1]

    failed = tmp_path / "failed.png"
    failed.write_bytes(b"old")
    with (
        mock.patch("videobatch_fast.preview_service.ffmpeg_path", return_value="ffmpeg"),
        mock.patch("videobatch_fast.preview_service.preview_cache_path", return_value=failed),
        mock.patch("videobatch_fast.preview_service.probe_media", return_value=MediaInfo(source, "image")),
        mock.patch(
            "videobatch_fast.preview_service.subprocess.run",
            return_value=SimpleNamespace(returncode=1, stderr="erste Zeile\nletzte Ursache"),
        ),
    ):
        with pytest.raises(PreviewError, match="letzte Ursache"):
            build_preview(source)
    assert not failed.exists()
