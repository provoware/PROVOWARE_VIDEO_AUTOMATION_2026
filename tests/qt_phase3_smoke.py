from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from unittest.mock import patch
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt, QPoint
from PySide6.QtWidgets import QApplication, QMessageBox

from videobatch_fast.config import load_config
from videobatch_fast.dashboard_settings import load_settings
from videobatch_fast.project_state import append_project_note, project_notes_file
from videobatch_fast.safe_io import SafeIoError
from videobatch_fast.qt_legacy_parity import (
    _archive_last_results,
    _plugin_scan,
    _update_package,
    _visual_approval,
)
from videobatch_fast.qt_legacy_parity_completion import (
    _apply_view_order,
    _remember_directory,
)
from videobatch_fast.qt_phase2 import VideoBatchQtPhase2Window
from videobatch_fast.qt_phase3 import VideoBatchQtPhase3Window


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="videobatch-qt-phase3-") as temporary:
        temporary_path = Path(temporary)
        os.environ["XDG_CONFIG_HOME"] = str(temporary_path / "config")
        os.environ["XDG_STATE_HOME"] = str(temporary_path / "state")
        os.environ["XDG_DATA_HOME"] = str(temporary_path / "data")
        app = QApplication.instance() or QApplication([])

        # The special-tool callbacks must already be replaced before construction,
        # otherwise Qt would retain references to the historical demo handlers.
        # Constructors and the close event must remain defined on their Qt
        # classes, not replaced at import time by legacy adapter closures.
        assert VideoBatchQtPhase2Window.__init__.__qualname__ == "VideoBatchQtPhase2Window.__init__"
        assert VideoBatchQtPhase2Window.closeEvent.__qualname__ == "VideoBatchQtPhase2Window.closeEvent"
        assert VideoBatchQtPhase3Window.__init__.__qualname__ == "VideoBatchQtPhase3Window.__init__"
        assert VideoBatchQtPhase3Window.closeEvent.__qualname__ == "VideoBatchQtPhase3Window.closeEvent"
        for direct_method in ("_options", "_refresh", "_runtime_state", "_start",
                              "_choose_audio", "_choose_media", "_browse_audio", "_browse_media"):
            member = getattr(VideoBatchQtPhase3Window, direct_method)
            assert member.__qualname__.startswith("VideoBatchQtPhase3Window."), direct_method
        assert not hasattr(VideoBatchQtPhase2Window, "_tk_parity_installed")
        assert VideoBatchQtPhase2Window._show_plugin_dialog is _plugin_scan
        assert VideoBatchQtPhase2Window._show_plugin_decision is _plugin_scan
        assert VideoBatchQtPhase2Window._show_update_dialog is _update_package
        assert VideoBatchQtPhase2Window._show_archive_dialog is _archive_last_results
        assert VideoBatchQtPhase2Window._show_visual_approval is _visual_approval

        # These widget methods must be native. No legacy installer may rewrite
        # the classes when the phase-3 module gets imported.
        from videobatch_fast.qt_media_list import DropList
        from videobatch_fast.qt_preview_panel import PreviewPanel
        from videobatch_fast.qt_legacy_parity_completion import install_parity_completion

        for name in ("paths", "production_paths", "add_paths", "remove_selected",
                     "clear", "sort_by", "render_view"):
            assert getattr(DropList, name).__qualname__.startswith("DropList."), name
        for name in ("__init__", "_render_pixmap", "set_parity_zoom",
                     "fit_parity_preview", "open_parity_fullscreen"):
            assert getattr(PreviewPanel, name).__qualname__.startswith("PreviewPanel."), name
        previous_methods = (
            DropList.add_paths, DropList.sort_by,
            PreviewPanel.__init__, PreviewPanel._render_pixmap,
        )
        install_parity_completion()
        assert previous_methods == (
            DropList.add_paths, DropList.sort_by,
            PreviewPanel.__init__, PreviewPanel._render_pixmap,
        )

        window = VideoBatchQtPhase3Window(autoload_project=False)
        window.show()
        app.processEvents()

        # Kein Dialog darf mehr als dynamischer Instanz-Monkeypatch erscheinen.
        for callback_name in (
            "_show_plugin_dialog", "_show_plugin_decision",
            "_show_update_dialog", "_show_recovery_dialog",
            "_show_archive_dialog", "_show_visual_approval",
        ):
            assert callback_name not in vars(window), callback_name
        assert VideoBatchQtPhase2Window._show_recovery_dialog.__qualname__.startswith(
            "VideoBatchQtPhase2Window."
        )

        assert len(window.workspace_navigation.buttons) == 9
        assert window.phase3_tabs.count() == 3
        assert [window.phase3_tabs.tabText(index) for index in range(3)] == [
            "Projekt",
            "Hilfe",
            "Diagnose & Assurance",
        ]

        # Tk -> Qt parity adapters must be fully attached after the first event turn.
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
        assert window.start.isEnabled(), "Start must stay clickable and explain missing preparation."

        # Real Qt widgets -> single settings model -> BatchOptions -> saved JSON.
        assert window.main_tabs.count() == 4
        assert window.main_tabs.tabText(3) == "Dashboard"
        window.main_tabs.setCurrentIndex(3)
        app.processEvents()
        notes_path = project_notes_file(window._project_file)
        assert window.dashboard_note_file.text().endswith(str(notes_path))
        window.dashboard_note_input.setText("Erste Notiz per Enter")
        window.dashboard_note_input.returnPressed.emit()
        assert window.dashboard_note_input.text() == ""
        assert "Gespeichert:" in window.dashboard_note_status.text()
        assert notes_path.exists()
        first = notes_path.read_text(encoding="utf-8").splitlines()
        assert len(first) == 1 and first[0].startswith("[20")
        assert first[0].endswith("Erste Notiz per Enter")
        window.dashboard_note_input.setText("Zweite Notiz per Knopf")
        window.dashboard_note_button.click()
        lines = notes_path.read_text(encoding="utf-8").splitlines()
        assert len(lines) == 2 and lines[0] == first[0]
        assert lines[1].endswith("Zweite Notiz per Knopf")
        # A custom project directory gets its own fixed TXT; an unfinished
        # pre-existing last line is preserved and separated from the new entry.
        custom_project = temporary_path / "eigener_projektordner" / "projekt.vbfast.json"
        custom_project.parent.mkdir()
        custom_notes = project_notes_file(custom_project)
        custom_notes.write_bytes(b"Alter Eintrag ohne Zeilenumbruch")
        appended_path, _stamp = append_project_note(custom_project, "Neue Notiz")
        assert appended_path == custom_notes
        custom_lines = custom_notes.read_text(encoding="utf-8").splitlines()
        assert len(custom_lines) == 2
        assert custom_lines[0] == "Alter Eintrag ohne Zeilenumbruch"
        assert custom_lines[1].endswith("Neue Notiz")
        # An interrupted/short write must never leave half of a dated line.
        limited_project = temporary_path / "begrenzter_speicher" / "projekt.vbfast.json"
        limited_project.parent.mkdir()
        limited_notes = project_notes_file(limited_project)
        previous_notes = b"Bestehende Notiz\n"
        limited_notes.write_bytes(previous_notes)
        limited_script = (
            "import resource, signal, sys\n"
            "from pathlib import Path\n"
            "from videobatch_fast.project_state import append_project_note\n"
            "project = Path(sys.argv[1])\n"
            "hard = resource.getrlimit(resource.RLIMIT_FSIZE)[1]\n"
            "resource.setrlimit(resource.RLIMIT_FSIZE, (int(sys.argv[2]), hard))\n"
            "signal.signal(signal.SIGXFSZ, signal.SIG_IGN)\n"
            "try:\n"
            "    append_project_note(project, 'Darf nicht unvollständig gespeichert werden')\n"
            "except OSError:\n"
            "    print('EXPECTED_CAPACITY_FAILURE')\n"
            "else:\n"
            "    raise AssertionError('Schreiben trotz Dateigrößenlimit erfolgreich')\n"
        )
        test_env = dict(os.environ)
        test_env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1] / "src")
        limited_run = subprocess.run(
            [sys.executable, "-c", limited_script, str(limited_project), str(len(previous_notes) + 18)],
            env=test_env, capture_output=True, text=True, timeout=15, check=True,
        )
        assert "EXPECTED_CAPACITY_FAILURE" in limited_run.stdout
        assert limited_notes.read_bytes() == previous_notes
        assert not list(limited_notes.parent.glob(".VideoBatch_Notizen.txt.*.tmp"))
        append_project_note(limited_project, "Nach Fehler erfolgreich wiederholt")
        recovered = limited_notes.read_text(encoding="utf-8").splitlines()
        assert recovered[0] == "Bestehende Notiz" and len(recovered) == 2
        assert recovered[1].endswith("Nach Fehler erfolgreich wiederholt")
        # A crafted notes link must not append bytes to original media.
        unsafe_project = temporary_path / "unsicherer_projektordner" / "projekt.vbfast.json"
        unsafe_project.parent.mkdir()
        original_media = unsafe_project.parent / "original.mp4"
        original_media.write_bytes(b"ORIGINAL_MEDIEN_DATEN")
        unsafe_notes = project_notes_file(unsafe_project)
        unsafe_notes.symlink_to(original_media)
        for link_type in ("symlink", "hardlink"):
            if link_type == "hardlink":
                unsafe_notes.unlink()
                os.link(original_media, unsafe_notes)
            try:
                append_project_note(unsafe_project, "Darf nicht in Medien landen")
            except OSError:
                pass
            else:
                raise AssertionError(f"Unsicheres Notizziel wurde geöffnet: {link_type}")
            assert original_media.read_bytes() == b"ORIGINAL_MEDIEN_DATEN"
        window.dashboard_note_input.setText("   ")
        window.dashboard_note_button.click()
        assert "Bitte zuerst" in window.dashboard_note_status.text()
        assert notes_path.read_text(encoding="utf-8").splitlines() == lines
        missing_project = temporary_path / "nicht_vorhanden" / "projekt.vbfast.json"
        window._project_file = missing_project
        window.dashboard_note_input.setText("Bei Fehler erhalten")
        with patch.object(QMessageBox, "warning") as warning:
            window.dashboard_note_button.click()
        warning.assert_called_once()
        assert window.dashboard_note_input.text() == "Bei Fehler erhalten"
        assert "Nicht gespeichert" in window.dashboard_note_status.text()
        window.dashboard_note_input.setText("Unsicherer Speicherstatus")
        with patch("videobatch_fast.qt_workspace_layout.append_project_note", side_effect=SafeIoError("Test")):
            with patch.object(QMessageBox, "warning") as warning:
                window.dashboard_note_button.click()
        warning.assert_called_once()
        assert window.dashboard_note_input.text() == "Unsicherer Speicherstatus"
        assert "Speicherstatus unklar" in window.dashboard_note_status.text()
        window._project_file = notes_path.parent / "aktuelles_projekt.vbfast.json"
        # Both Save As and project navigation must show the actual target directory.
        saved_as_project = temporary_path / "gespeichert_unter" / "projekt.vbfast.json"
        saved_as_project.parent.mkdir()
        assert window._persist_project_to(saved_as_project, silent=True)
        assert window.dashboard_note_file.text().endswith(str(project_notes_file(saved_as_project)))
        window._project_file = notes_path.parent / "aktuelles_projekt.vbfast.json"
        window._route_workspace("project")
        assert window.dashboard_note_file.text().endswith(str(notes_path))
        window._route_workspace("dashboard")
        window.view_scale.setCurrentIndex(window.view_scale.findData(200))
        window.resize(800, 600)
        app.processEvents()
        assert window.main_tabs.tabText(3) == "Notizen"
        assert sum(window.main_tabs.tabRect(i).width() for i in range(4)) <= window.main_tabs.width()
        assert not window.dashboard_note_hint.isVisibleTo(window)
        input_bottom = window.dashboard_note_input.mapTo(window, QPoint(0, 0)).y() + window.dashboard_note_input.height()
        footer_top = window.action_footer_scroll.mapTo(window, QPoint(0, 0)).y()
        assert input_bottom <= footer_top, (input_bottom, footer_top)
        window.view_scale.setCurrentIndex(window.view_scale.findData(110))
        window.resize(1360, 820)
        window.main_tabs.setCurrentIndex(0)
        app.processEvents()
        window.resolution.setCurrentIndex(window.resolution.findData("1920×1080"))
        window.quality.setCurrentIndex(window.quality.findData("maximum"))
        window.effect.setCurrentIndex(window.effect.findData("vivid"))
        expected_output = temporary_path / "export"
        window.output.setText(str(expected_output))
        actual = window._options()
        assert actual.resolution == "1920×1080"
        assert actual.profile == "maximum"
        assert actual.visual_effect == "vivid"
        assert actual.output_dir == expected_output
        stored = load_settings()
        assert stored.resolution == actual.resolution
        assert stored.quality == actual.profile
        assert stored.effect == actual.visual_effect
        assert stored.output_dir == actual.output_dir
        menu_titles = [action.text().replace("&", "") for action in window.menuBar().actions()]
        assert menu_titles == ["Datei", "Medien", "Ansicht", "Produktion", "Werkzeuge", "Hilfe"]

        # Preview parity: the former 25-800 % range plus fit/fullscreen controls is back.
        assert window.preview_panel.parity_zoom.minimum() == 25
        assert window.preview_panel.parity_zoom.maximum() == 800
        assert window.preview_panel._parity_fit_button.text() == "Einpassen"
        assert window.preview_panel._parity_fullscreen_button.text() == "Vollbild"
        window.preview_panel.fit_parity_preview()
        assert window.preview_panel._parity_fit is True
        # Render real pixel dimensions at fixed zoom, not merely control text.
        from PySide6.QtGui import QPixmap
        window.preview_panel._pixmap = QPixmap(40, 40)
        window.preview_panel.set_parity_zoom(175, persist=False)
        assert window.preview_panel.image.pixmap().width() == 70
        window.preview_panel.fit_parity_preview()
        assert window.preview_panel._parity_fit is True
        window.preview_panel._pixmap = None
        window.preview_panel.image.clear()
        window.preview_panel.set_parity_zoom(175, persist=False)
        assert window.preview_panel._parity_zoom == 175
        assert window.preview_panel.parity_zoom.value() == 175

        source_z = temporary_path / "z-source.wav"
        source_a = temporary_path / "a-source.wav"
        media_z = temporary_path / "z-cover.png"
        media_a = temporary_path / "a-cover.png"
        source_z.write_bytes(b"smoke-audio-z")
        source_a.write_bytes(b"smoke-audio-a")
        media_z.write_bytes(b"smoke-image-z")
        media_a.write_bytes(b"smoke-image-a")
        window.audio.add_paths([source_z, source_a])
        window.media.add_paths([media_z, media_a])

        # Multi-image slideshow is valid with 2 audios and 3 images.
        # The shared pairwise banner must not mislabel that as incomplete.
        from videobatch_fast.slideshow import (
            SLIDESHOW_MODE_ALL_IMAGES, SLIDESHOW_MODE_PAIRWISE,
        )
        slide_extra = temporary_path / "third-cover.png"
        slide_extra.write_bytes(b"smoke-image-extra")
        window.media.add_paths([slide_extra])
        window.slideshow.assignment.setCurrentIndex(
            window.slideshow.assignment.findData(SLIDESHOW_MODE_ALL_IMAGES)
        )
        app.processEvents()
        assert "Diashow" in window.pairing_summary_label.text()
        assert window.pairing_summary_label.text().startswith("✓ Diashow bereit:")
        assert "fehlen" not in window.pairing_summary_label.text()
        assert not window.probe_button.isEnabled()
        window.slideshow.assignment.setCurrentIndex(
            window.slideshow.assignment.findData(SLIDESHOW_MODE_PAIRWISE)
        )
        window.media.clear()
        window.media.add_paths([media_z, media_a])
        app.processEvents()
        assert "Bereit für 2 Video" in window.pairing_summary_label.text()

        # Sorting changes only the view until the user explicitly accepts it as
        # production order. This restores the old data-safety contract.
        window.parity_audio_sort.setCurrentIndex(window.parity_audio_sort.findData("name_asc"))
        app.processEvents()
        displayed_audio = [
            Path(str(window.audio.item(row).data(Qt.ItemDataRole.UserRole)))
            for row in range(window.audio.count())
        ]
        assert displayed_audio == [source_a.resolve(), source_z.resolve()]
        assert window.audio.paths() == [source_z.resolve(), source_a.resolve()]
        _apply_view_order(window, audio=True)
        assert window.audio.paths() == [source_a.resolve(), source_z.resolve()]

        # Last-used source folders are persisted independently for audio/media.
        _remember_directory(window, "last_audio_dir", [source_a])
        _remember_directory(window, "last_media_dir", [media_a])
        config = load_config()
        assert Path(config["last_audio_dir"]) == temporary_path
        assert Path(config["last_media_dir"]) == temporary_path

        # Independent area zoom is restored and remains separate from global font size.
        window.parity_area_zoom_area.setCurrentIndex(
            window.parity_area_zoom_area.findData("media")
        )
        window.parity_area_zoom_value.setValue(120)
        app.processEvents()
        assert window._parity_area_zoom["media"] == 120

        window.project_panel.name.setText("Phase 3 Smoke")
        window.project_panel.note.setPlainText("Projektzustand muss atomar gespeichert werden.")
        window.parity_playlist.add([source_a])
        window.slideshow._parity_order_mode = "random"
        window.slideshow._manual_seed = 17
        window._parity_calendar_notes["2026-09-11"] = {
            "note": "Parität prüfen",
            "entry_type": "task",
            "color": "active",
        }
        window._parity_calendar_marks["2026-09-11"] = "active"

        # The active Qt workspace is stored inside the project meta block.
        window._route_workspace("queue")
        app.processEvents()
        state = window._collect_project_state()
        assert state["meta"]["qt_active_workspace"] == "queue"
        assert state["audio_sort"] == "import"

        project = temporary_path / "phase3-smoke.vbfast.json"
        window._project_file = project
        assert window._save_current_project()
        payload = json.loads(project.read_text(encoding="utf-8"))
        assert payload["project_name"] == "Phase 3 Smoke"
        assert payload["audio_paths"] == [str(source_a.resolve()), str(source_z.resolve())]
        assert payload["media_paths"] == [str(media_z.resolve()), str(media_a.resolve())]
        assert payload["playlist_paths"] == [str(source_a.resolve())]
        assert payload["slideshow_order_mode"] == "random"
        assert payload["slideshow_random_seed"] == 17
        assert payload["calendar_notes"]["2026-09-11"]["note"] == "Parität prüfen"
        assert payload["meta"]["frontend"] == "qt-phase3"
        assert payload["meta"]["qt_active_workspace"] == "queue"

        # Real Qt instance: simulate a full / read-only disk and verify that
        # Save As, closing, and project switching never discard edits.
        previous = window._project_file
        destination = temporary_path / "new-name.vbfast.json"
        window.project_panel.note.setPlainText("Ungespeicherte Änderungen")
        window._project_dirty = True
        with (
            patch("videobatch_fast.qt_phase3.save_project_state",
                  side_effect=PermissionError("Disk is read-only")),
            patch("videobatch_fast.qt_phase3.QFileDialog.getSaveFileName",
                  return_value=(str(destination), "")),
            patch("videobatch_fast.qt_phase3.QMessageBox.critical"),
        ):
            window._save_project_as()
            assert window._project_file == previous
            assert window._project_dirty
            assert not destination.exists()
        with (
            patch("videobatch_fast.qt_phase3.save_project_state",
                  side_effect=OSError("Disk full")),
            patch("videobatch_fast.qt_phase3.QMessageBox.warning",
                  return_value=QMessageBox.StandardButton.Cancel),
        ):
            assert window.close() is False
            assert window.isVisible()
            assert window._project_dirty
        # Recovery: a later successful save clears the dirty state.
        assert window._save_current_project()
        assert not window._project_dirty
        assert window._project_file == previous

        # Simulate a Qt widget failure halfway through changing projects.
        # The previous project and its visible content must be restored.
        from videobatch_fast.project_state import save_project_state
        other_file = temporary_path / "unapplied.vbfast.json"
        save_project_state(other_file, {"project_name": "Unapplied"})
        old_project = window._project_file
        old_note = window.project_panel.note.toPlainText()
        old_audio = window.audio.production_paths()
        original_apply = window._apply_project_state
        calls = [0]

        def fail_first_application(state):
            calls[0] += 1
            if calls[0] == 1:
                window.audio.clear()
                raise RuntimeError("Simulated Qt widget failure")
            return original_apply(state)

        with patch.object(window, "_apply_project_state", side_effect=fail_first_application):
            try:
                window._load_project(other_file)
            except RuntimeError:
                pass
            else:
                raise AssertionError("Partial project change succeeded unexpectedly")
        assert window._project_file == old_project
        assert window.project_panel.note.toPlainText() == old_note
        assert window.audio.production_paths() == old_audio

        for route in window.workspace_navigation.buttons:
            window._route_workspace(route)
            app.processEvents()
        assert window.workspace_navigation.buttons["diagnostics"].property("active") is True

        window._route_workspace("effects")
        app.processEvents()
        assert not window.parity_dock.isVisible(), "Expertenleiste darf Schritt 2 nicht verdrängen"
        from videobatch_fast.qt_legacy_parity import _show_parity_tab
        _show_parity_tab(window, 0)
        app.processEvents()
        assert window.parity_dock.isVisible(), "Expertenwerkzeug muss auf Wunsch erreichbar bleiben"
        assert window.parity_tabs.currentIndex() == 0
        window._route_workspace("queue")
        app.processEvents()
        assert not window.parity_dock.isVisible()

        window.diagnostics_panel.run_diagnostic()
        app.processEvents()
        assert window.diagnostics_panel.table.rowCount() == 1
        assert window.diagnostics_panel.status.text() in {"✓ BESTANDEN", "✕ FEHLER · 1"}

        geometry_before_close = f"{window.width()}x{window.height()}"
        window.close()
        for _ in range(5):
            app.processEvents()
        assert not window.isVisible()
        config = load_config()
        assert config["window_geometry"] == geometry_before_close
        assert config["preview_zoom"] == 175
        assert config["area_zoom"]["media"] == 120
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
