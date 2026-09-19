from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import QApplication

from videobatch_fast.config import DEFAULT_CONFIG, load_config, save_config
from videobatch_fast.models import BatchOptions
from videobatch_fast.qt_legacy_appearance import apply_theme
from videobatch_fast.qt_legacy_calendar import load_calendar_selection
from videobatch_fast.qt_legacy_playlist import refresh_playlist_list
from videobatch_fast.qt_legacy_settings import build_settings_tab
from videobatch_fast.qt_legacy_parity import LEGACY_OPTION_KEYS, PROJECT_PARITY_KEYS, _combo
from videobatch_fast.qt_legacy_parity_completion import _apply_view_order
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

    config = dict(DEFAULT_CONFIG)
    config.update(
        {
            "window_geometry": "1100x700",
            "preview_zoom": 150,
            "audio_sort": "name_desc",
            "media_sort": "size_asc",
            "area_zoom": {
                "start": 100,
                "media": 130,
                "preview": 90,
                "modes": 100,
                "production": 110,
                "help": 100,
            },
            "last_audio_dir": str(tmp_path),
            "last_media_dir": str(tmp_path),
            "active_tab": 4,
        }
    )
    save_config(config)

    app = QApplication.instance() or QApplication([])
    window = VideoBatchQtPhase3Window(autoload_project=False)
    window.show()
    app.processEvents()

    assert window._parity_ready is True
    assert window._parity_completion_ready is True
    assert window.mode.findData("custom") >= 0
    assert window.parity_tabs.count() == 5
    assert [window.parity_tabs.tabText(index) for index in range(5)] == [
        "Einstellungen",
        "Playlist",
        "Kalender",
        "Wartung",
        "Medien & Ansicht",
    ]
    assert window.start.isEnabled(), "Start muss auch bei unvollständiger Auswahl anklickbar bleiben."
    assert "FFmpeg + FFprobe gefunden" in window.runtime.text()

    # Previously working view/session settings are restored as real Qt controls.
    assert window.preview_panel.parity_zoom.minimum() == 25
    assert window.preview_panel.parity_zoom.maximum() == 800
    assert window.preview_panel.parity_zoom.value() == 150
    assert window._parity_area_zoom["media"] == 130
    assert window.parity_audio_sort.currentData() == "name_desc"
    assert window.parity_media_sort.currentData() == "size_asc"
    assert window._parity_active_workspace == "queue"
    assert Path(load_config()["last_audio_dir"]) == tmp_path
    assert Path(load_config()["last_media_dir"]) == tmp_path

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

    audio_z = tmp_path / "z-song.wav"
    audio_a = tmp_path / "a-song.wav"
    image_z = tmp_path / "z-cover.png"
    image_a = tmp_path / "a-cover.png"
    audio_z.write_bytes(b"audio-z")
    audio_a.write_bytes(b"audio-a")
    image_z.write_bytes(b"image-z")
    image_a.write_bytes(b"image-a")
    window.audio.add_paths([audio_z, audio_a])
    window.media.add_paths([image_z, image_a])

    # Sorting is view-only until the explicit production-order action is used.
    window.parity_audio_sort.setCurrentIndex(window.parity_audio_sort.findData("name_asc"))
    app.processEvents()
    displayed = [
        Path(str(window.audio.item(row).data(Qt.ItemDataRole.UserRole)))
        for row in range(window.audio.count())
    ]
    assert displayed == [audio_a.resolve(), audio_z.resolve()]
    assert window.audio.paths() == [audio_z.resolve(), audio_a.resolve()]
    _apply_view_order(window, audio=True)
    assert window.audio.paths() == [audio_a.resolve(), audio_z.resolve()]

    window.parity_playlist.add([audio_a])
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
    window._route_workspace("preview")

    state = window._collect_project_state()
    for key in PROJECT_PARITY_KEYS:
        assert key in state
    assert state["playlist_paths"] == [str(audio_a)]
    assert state["slideshow_order_mode"] == "random"
    assert state["slideshow_random_seed"] == 42
    assert state["archive_used"] is True
    assert state["calendar_notes"]["2026-09-11"]["note"] == "Test"
    assert state["audio_sort"] == "import"
    assert state["media_sort"] == "size_asc"
    assert state["meta"]["qt_active_workspace"] == "preview"

    menu_titles = [action.text().replace("&", "") for action in window.menuBar().actions()]
    assert menu_titles == ["Datei", "Medien", "Ansicht", "Produktion", "Werkzeuge", "Hilfe"]

    window.close()
    for _ in range(4):
        app.processEvents()

    saved = load_config()
    assert saved["preview_zoom"] == 150
    assert saved["area_zoom"]["media"] == 130
    assert saved["audio_sort"] == "import"
    assert saved["media_sort"] == "size_asc"


def test_extracted_legacy_calendar_restores_selected_entry(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    monkeypatch.setenv("VIDEOBATCH_FFMPEG", str(_fake_executable(tmp_path / "private-ffmpeg")))
    monkeypatch.setenv("VIDEOBATCH_FFPROBE", str(_fake_executable(tmp_path / "private-ffprobe")))

    app = QApplication.instance() or QApplication([])
    window = VideoBatchQtPhase3Window(autoload_project=False)
    window._parity_calendar_notes["2026-09-19"] = {
        "note": "Debt-Burn-Down",
        "entry_type": "task",
        "color": "active",
    }
    window._parity_calendar_marks["2026-09-19"] = "active"
    window.parity_calendar.setSelectedDate(QDate(2026, 9, 19))

    load_calendar_selection(window)

    assert window.parity_calendar_note.text() == "Debt-Burn-Down"
    assert window.parity_calendar_type.currentData() == "task"
    assert window.parity_calendar_color.currentData() == "active"
    window.close()
    app.processEvents()


def test_extracted_legacy_playlist_refreshes_visible_items(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    monkeypatch.setenv("VIDEOBATCH_FFMPEG", str(_fake_executable(tmp_path / "private-ffmpeg")))
    monkeypatch.setenv("VIDEOBATCH_FFPROBE", str(_fake_executable(tmp_path / "private-ffprobe")))

    audio_a = tmp_path / "alpha.wav"
    audio_b = tmp_path / "beta.wav"
    audio_a.write_bytes(b"RIFF")
    audio_b.write_bytes(b"RIFF")

    app = QApplication.instance() or QApplication([])
    window = VideoBatchQtPhase3Window(autoload_project=False)
    window.parity_playlist.items = [audio_a, audio_b]
    window.parity_playlist.current = 1

    refresh_playlist_list(window)

    assert window.parity_playlist_list.count() == 2
    assert window.parity_playlist_list.item(0).text() == "01 · alpha.wav"
    assert window.parity_playlist_list.item(1).text() == "02 · beta.wav"
    assert window.parity_playlist_list.currentRow() == 1
    window.close()
    app.processEvents()


def test_extracted_legacy_appearance_applies_theme_and_font_scale(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    monkeypatch.setenv("VIDEOBATCH_FFMPEG", str(_fake_executable(tmp_path / "private-ffmpeg")))
    monkeypatch.setenv("VIDEOBATCH_FFPROBE", str(_fake_executable(tmp_path / "private-ffprobe")))

    app = QApplication.instance() or QApplication([])
    window = VideoBatchQtPhase3Window(autoload_project=False)
    original_style = app.styleSheet()
    original_font = app.font()
    try:
        window._parity_base_font_size = 10.0
        window.parity_theme.setCurrentIndex(window.parity_theme.findData("acid_paper"))
        window.parity_font_scale.setValue(120)

        apply_theme(window)

        assert "#f2f0d8" in app.styleSheet()
        assert abs(app.font().pointSizeF() - 12.0) < 0.01
    finally:
        app.setStyleSheet(original_style)
        app.setFont(original_font)
        window.close()
        app.processEvents()


def test_extracted_legacy_settings_builds_widgets_from_config(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    monkeypatch.setenv("VIDEOBATCH_FFMPEG", str(_fake_executable(tmp_path / "private-ffmpeg")))
    monkeypatch.setenv("VIDEOBATCH_FFPROBE", str(_fake_executable(tmp_path / "private-ffprobe")))

    app = QApplication.instance() or QApplication([])
    window = VideoBatchQtPhase3Window(autoload_project=False)
    tab = build_settings_tab(window, combo_factory=_combo)

    assert window.parity_output_mode.currentData() == str(
        window._parity_config.get("output_mode", "Gemeinsamer Ordner")
    )
    assert window.parity_codec.currentData() == str(
        window._parity_config.get("codec", "libx264")
    )
    assert window.parity_theme.currentData() == str(
        window._parity_config.get("theme", "neon_gravity")
    )
    assert window.parity_font_scale.value() == int(
        window._parity_config.get("font_scale", 105)
    )
    assert tab.layout() is not None
    tab.deleteLater()
    window.close()
    app.processEvents()
