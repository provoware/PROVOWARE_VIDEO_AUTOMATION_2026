from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from videobatch_fast.models import BatchOptions
from videobatch_fast.qt_legacy_parity import LEGACY_OPTION_KEYS, PROJECT_PARITY_KEYS
from videobatch_fast.qt_phase3 import VideoBatchQtPhase3Window


def _fake_executable(path: Path) -> Path:
    path.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    path.chmod(0o755)
    return path


def test_qt_phase3_restores_legacy_options_and_uses_configured_media_tools(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    monkeypatch.setenv("VIDEOBATCH_FFMPEG", str(_fake_executable(tmp_path / "private-ffmpeg")))
    monkeypatch.setenv("VIDEOBATCH_FFPROBE", str(_fake_executable(tmp_path / "private-ffprobe")))

    app = QApplication.instance() or QApplication([])
    window = VideoBatchQtPhase3Window(autoload_project=False)
    window.show()
    app.processEvents()

    assert window._parity_ready is True
    assert window.mode.findData("custom") >= 0
    assert window.parity_tabs.count() == 4
    assert [window.parity_tabs.tabText(index) for index in range(4)] == [
        "Einstellungen",
        "Playlist",
        "Kalender",
        "Wartung",
    ]
    assert window.start.isEnabled(), "Start muss auch bei unvollständiger Auswahl anklickbar bleiben."
    assert "FFmpeg + FFprobe gefunden" in window.runtime.text()

    expected_batch_fields = {
        "output_dir",
        "output_mode",
        "resolution",
        "codec",
        "profile",
        "verification",
        "keep_lists",
        "visual_effect",
        "transition",
        "quick_mode",
        "assignment_mode",
        "slideshow_transition",
        "slideshow_scene_sync",
    }
    assert expected_batch_fields == set(LEGACY_OPTION_KEYS)
    assert expected_batch_fields <= set(BatchOptions.__dataclass_fields__)

    window.mode.setCurrentIndex(window.mode.findData("custom"))
    window.parity_output_mode.setCurrentIndex(
        window.parity_output_mode.findData("Neben Mediendatei")
    )
    window.parity_resolution.setCurrentIndex(window.parity_resolution.findData("1920×1080"))
    window.parity_codec.setCurrentIndex(window.parity_codec.findData("libx265"))
    window.parity_profile.setCurrentIndex(window.parity_profile.findData("quality"))
    window.parity_effect.setCurrentIndex(window.parity_effect.findData("hardtechno"))
    window.parity_transition.setCurrentIndex(window.parity_transition.findData("soft"))
    window.parity_keep_lists.setChecked(False)

    options = window._options()
    assert options.quick_mode == "custom"
    assert options.output_mode == "Neben Mediendatei"
    assert options.resolution == "1920×1080"
    assert options.codec == "libx265"
    assert options.profile == "quality"
    assert options.visual_effect == "hardtechno"
    assert options.transition == "soft"
    assert options.keep_lists is False

    audio = tmp_path / "song.wav"
    image = tmp_path / "cover.png"
    audio.write_bytes(b"audio")
    image.write_bytes(b"image")
    window.audio.add_paths([audio])
    window.media.add_paths([image])
    window.parity_playlist.add([audio])
    window.slideshow._parity_order_mode = "random"
    window.slideshow._manual_seed = 42
    window.parity_archive_used.setChecked(True)
    window.parity_archive_dir.setText(str(tmp_path / "archive"))
    window._parity_calendar_notes["2026-09-11"] = {
        "note": "Test",
        "entry_type": "task",
        "color": "active",
    }
    window._parity_calendar_marks["2026-09-11"] = "active"

    state = window._collect_project_state()
    for key in PROJECT_PARITY_KEYS:
        assert key in state
    assert state["playlist_paths"] == [str(audio)]
    assert state["slideshow_order_mode"] == "random"
    assert state["slideshow_random_seed"] == 42
    assert state["archive_used"] is True
    assert state["calendar_notes"]["2026-09-11"]["note"] == "Test"

    menu_titles = [action.text().replace("&", "") for action in window.menuBar().actions()]
    assert menu_titles == ["Datei", "Medien", "Ansicht", "Produktion", "Werkzeuge", "Hilfe"]

    window.close()
    for _ in range(4):
        app.processEvents()
