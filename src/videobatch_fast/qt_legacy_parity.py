from __future__ import annotations

import os
import threading
import time
from collections import Counter
from dataclasses import replace
from pathlib import Path

from PySide6.QtCore import QObject, QDate, QTimer, QUrl, Signal, Qt
from PySide6.QtGui import QAction, QDesktopServices, QFont, QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QCalendarWidget,
    QCheckBox,
    QComboBox,
    QDockWidget,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from .archive_service import append_manifest, archive_file, recover_archive_transactions
from .command_builder import PROFILES
from .config import DEFAULT_CONFIG, load_config, save_config
from .effects import TRANSITIONS, VISUAL_EFFECTS
from .job_journal import (
    acknowledge_recovery,
    recoverable_batches,
    recovery_input_paths,
    recovery_options,
)
from .models import BatchOptions
from .playlist import AudioPlayer, Playlist
from .plugin_approvals import build_identity, grant_approval, revoke_approval, validate_approval
from .plugin_permissions import permission_summary
from .plugin_runtime import run_plugin_in_sandbox
from .plugins import scan_plugins
from .probe import ffmpeg_path, ffprobe_path, probe_media
from .quick_modes import QUICK_MODES
from .qt_theme import APP_STYLE
from .qt_workflow_dialogs import (
    PluginPermissionDecisionDialog,
    VisualApprovalSignDialog,
    archive_preview_dialog,
    update_assistant_dialog,
)
from .slideshow import SLIDESHOW_MODE_ALL_IMAGES
from .updates import apply_update_package, validate_update_package
from .validation import validate_pairs
from .versioning import build_label
from .visual_approval import sign_visual_approval, verify_visual_approval
from .visual_inspection import write_inspection_html

PARITY_VERSION = 1
LEGACY_OPTION_KEYS = (
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
)
PROJECT_PARITY_KEYS = (
    "playlist_paths",
    "slideshow_order_mode",
    "slideshow_random_seed",
    "slideshow_start_image",
    "slideshow_end_image",
    "archive_used",
    "archive_project_dir",
    "archive_suffix",
    "calendar_year",
    "calendar_month",
    "calendar_marks",
    "calendar_notes",
)

_THEME_OVERRIDES = {
    "neon_gravity": """
        QMainWindow, QWidget { background-color: #10141b; color: #eef4ff; }
        QFrame#panel, QFrame#card { background-color: #171d27; }
    """,
    "acid_paper": """
        QMainWindow, QWidget { background-color: #f2f0d8; color: #1b2415; }
        QFrame#panel, QFrame#card { background-color: #fffde8; }
        QLineEdit, QListWidget, QComboBox { background-color: #ffffff; color: #172012; }
    """,
    "toxic_candy": """
        QMainWindow, QWidget { background-color: #1b1020; color: #fff0fb; }
        QFrame#panel, QFrame#card { background-color: #28152f; }
    """,
    "ultraviolet": """
        QMainWindow, QWidget { background-color: #151126; color: #f2edff; }
        QFrame#panel, QFrame#card { background-color: #201936; }
    """,
}


class _ParityBridge(QObject):
    taskFinished = Signal(str, object, str)
    batchFinished = Signal(object)


def _combo(parent: QWidget, values: list[tuple[str, str]], current: str) -> QComboBox:
    box = QComboBox(parent)
    for label, value in values:
        box.addItem(label, value)
    index = box.findData(current)
    if index >= 0:
        box.setCurrentIndex(index)
    return box


def _blocking_text(issues: list[object]) -> str:
    lines: list[str] = []
    for issue in issues[:8]:
        title = str(getattr(issue, "title", "Prüfung"))
        message = str(getattr(issue, "message", ""))
        solution = str(getattr(issue, "solution", ""))
        lines.append(f"• {title}: {message}\n  Lösung: {solution}")
    if len(issues) > 8:
        lines.append(f"… und {len(issues) - 8} weitere Hinweise.")
    return "\n\n".join(lines)


def _install_validated_runner(window: object) -> None:
    original_start = window.runner.start
    if getattr(window, "_parity_runner_wrapped", False):
        return

    def validated_start(jobs, options) -> None:
        issues = [item for item in validate_pairs(list(jobs), options) if item.blocking]
        if issues:
            window._status("PRÜFEN")
            window.next_step.setText(
                f"Start noch nicht möglich: {len(issues)} Punkt(e) müssen zuerst gelöst werden."
            )
            QMessageBox.warning(
                window,
                "Vorbereitung noch nicht vollständig",
                _blocking_text(issues),
            )
            raise RuntimeError(f"Validierung blockiert: {len(issues)} Punkt(e).")
        original_start(jobs, options)

    window.runner.start = validated_start
    window._parity_runner_wrapped = True


def _parity_runtime_state(self) -> None:
    missing = []
    if not ffmpeg_path():
        missing.append("FFmpeg")
    if not ffprobe_path():
        missing.append("FFprobe")
    self.runtime.setText(
        "🔴 Fehlt: " + ", ".join(missing)
        if missing
        else "🟢 FFmpeg + FFprobe gefunden"
    )


def _parity_start(self) -> None:
    if self.runner.running or self.preparing:
        return

    missing = []
    if not ffmpeg_path():
        missing.append("FFmpeg")
    if not ffprobe_path():
        missing.append("FFprobe")
    if missing:
        QMessageBox.critical(
            self,
            "Medienwerkzeug fehlt",
            "Nicht verfügbar: "
            + ", ".join(missing)
            + "\n\nVideoBatch verwendet auch konfigurierte/bündelbare FFmpeg-Pfade; "
              "die Diagnose zeigt den tatsächlich erkannten Zustand.",
        )
        return

    audios = self.audio.paths()
    media = self.media.paths()
    slideshow = getattr(self, "slideshow", None)
    all_images = bool(
        slideshow is not None
        and slideshow.assignment_mode == SLIDESHOW_MODE_ALL_IMAGES
    )

    if all_images:
        images = slideshow.image_paths()
        if not audios:
            QMessageBox.warning(
                self, "Audio fehlt", "Für eine Diashow wird mindestens eine Audiodatei benötigt."
            )
            return
        if not images:
            QMessageBox.warning(
                self, "Bilder fehlen", "Für eine Diashow wird mindestens ein Bild benötigt."
            )
            return
        if slideshow.scene_sync_enabled:
            slideshow.ensure_scene_analyses()
            if slideshow.pending_analysis or slideshow.missing_scene_analyses():
                QMessageBox.information(
                    self,
                    "Szenenanalyse läuft",
                    "Die Audios werden zuerst analysiert. Danach kann derselbe Startknopf erneut verwendet werden.",
                )
                self._refresh()
                return
    elif not audios or len(audios) != len(media):
        QMessageBox.warning(
            self,
            "Paarung unvollständig",
            "Zu jedem Audio muss genau ein Bild oder Video gehören.\n\n"
            "Alternative: Im Bereich „Diashow“ die Zuordnung „Alle Bilder je Audio“ wählen.",
        )
        return

    try:
        options = self._options()
    except ValueError as exc:
        QMessageBox.warning(self, "Einstellung fehlt", str(exc))
        return

    analyses = slideshow.scene_analyses() if all_images else None
    self.preparing = True
    self.prepare_generation += 1
    generation = self.prepare_generation
    self.start.setEnabled(False)
    self.cancel.setEnabled(True)
    self.progress.setRange(0, 0)
    self.progress.setFormat("Quellen werden vollständig geprüft …")
    self._status("PRÜFT")
    self.step_start.setText("3 · Start …")
    self.next_step.setText(
        "Dateien und Einstellungen werden geprüft. Danach startet die Verarbeitung automatisch."
    )
    self._write_log(
        f"Vollständige Startprüfung: {len(audios)} Audio(s) · "
        f"{len(media)} Medien · Modus {options.quick_mode}."
    )

    from .jobs import build_jobs

    def prepare() -> None:
        try:
            kwargs = {"scene_analyses": analyses} if all_images else {}
            jobs = build_jobs(audios, media, options, **kwargs)
            if not jobs:
                raise RuntimeError("Es konnten keine Produktionsaufträge erzeugt werden.")
            self.prepare_queue.put(("ok", (generation, jobs, options)))
        except Exception as exc:
            self.prepare_queue.put(
                ("error", (generation, f"{type(exc).__name__}: {exc}"))
            )

    self.prepare_thread = threading.Thread(
        target=prepare,
        daemon=True,
        name="VideoBatch-Qt-Parity-Prepare",
    )
    self.prepare_thread.start()


def _parity_options(self) -> BatchOptions:
    original = getattr(type(self), "_parity_original_options", None)
    if not hasattr(self, "parity_output_mode") or original is None:
        return original(self) if original is not None else BatchOptions(Path(self.output.text()))

    base = original(self)
    common = replace(
        base,
        output_mode=str(self.parity_output_mode.currentData() or "Gemeinsamer Ordner"),
        keep_lists=self.parity_keep_lists.isChecked(),
    )
    if str(self.mode.currentData() or "") != "custom":
        return common
    return replace(
        common,
        quick_mode="custom",
        resolution=str(self.parity_resolution.currentData() or "Original"),
        codec=str(self.parity_codec.currentData() or "libx264"),
        profile=str(self.parity_profile.currentData() or "fast"),
        verification=str(self.verification.currentText()),
        visual_effect=str(self.parity_effect.currentData() or "none"),
        transition=str(self.parity_transition.currentData() or "none"),
    )


def _patch_phase2_class() -> None:
    from .qt_phase2 import VideoBatchQtPhase2Window
    if getattr(VideoBatchQtPhase2Window, "_tk_parity_installed", False):
        return

    VideoBatchQtPhase2Window._parity_original_options = VideoBatchQtPhase2Window._options
    VideoBatchQtPhase2Window._options = _parity_options

    original_refresh = VideoBatchQtPhase2Window._refresh

    def refresh(self) -> None:
        original_refresh(self)
        if not self.runner.running and not self.preparing:
            self.start.setEnabled(True)
            self.start.setText("▶ 3 · Prüfen & Videos erstellen")

    VideoBatchQtPhase2Window._refresh = refresh
    VideoBatchQtPhase2Window._start = _parity_start
    VideoBatchQtPhase2Window._runtime_state = _parity_runtime_state

    slideshow_cls = __import__(
        "videobatch_fast.qt_phase2_components",
        fromlist=["SlideshowPanel"],
    ).SlideshowPanel
    original_commit_order = slideshow_cls._commit_order
    if not getattr(slideshow_cls, "_tk_parity_installed", False):
        def commit_order(self, ordered, message, *, mode="manual"):
            self._parity_order_mode = mode
            return original_commit_order(self, ordered, message, mode=mode)

        slideshow_cls._commit_order = commit_order
        slideshow_cls._tk_parity_installed = True

    VideoBatchQtPhase2Window._tk_parity_installed = True


def _apply_theme(window: object) -> None:
    app = QApplication.instance()
    if app is None:
        return
    theme = str(window.parity_theme.currentData() or "neon_gravity")
    scale = int(window.parity_font_scale.value())
    app.setStyleSheet(APP_STYLE + "\n" + _THEME_OVERRIDES.get(theme, ""))
    font = QFont(app.font())
    base = float(getattr(window, "_parity_base_font_size", 10.0) or 10.0)
    font.setPointSizeF(max(7.0, base * scale / 100.0))
    app.setFont(font)


def _save_settings(window: object) -> None:
    if not getattr(window, "_parity_ready", False):
        return
    config = dict(getattr(window, "_parity_config", DEFAULT_CONFIG))
    config.update(
        {
            "output_dir": window.output.text().strip(),
            "output_mode": str(window.parity_output_mode.currentData() or "Gemeinsamer Ordner"),
            "resolution": str(window.parity_resolution.currentData() or "Original"),
            "codec": str(window.parity_codec.currentData() or "libx264"),
            "profile": str(window.parity_profile.currentData() or "fast"),
            "verification": window.verification.currentText(),
            "keep_lists": window.parity_keep_lists.isChecked(),
            "visual_effect": str(window.parity_effect.currentData() or "none"),
            "transition": str(window.parity_transition.currentData() or "none"),
            "quick_mode": str(window.mode.currentData() or "smart_auto"),
            "assignment_mode": getattr(window.slideshow, "assignment_mode", "pairwise"),
            "slideshow_transition": getattr(window.slideshow, "transition_preset", "auto"),
            "slideshow_scene_sync": bool(getattr(window.slideshow, "scene_sync_enabled", False)),
            "archive_used": window.parity_archive_used.isChecked(),
            "archive_project_dir": window.parity_archive_dir.text().strip(),
            "archive_suffix": window.parity_archive_suffix.text().strip() or "__verwendet",
            "playlist_repeat": str(window.parity_repeat.currentData() or "off"),
            "playlist_shuffle": window.parity_shuffle.isChecked(),
            "theme": str(window.parity_theme.currentData() or "neon_gravity"),
            "font_scale": window.parity_font_scale.value(),
            "auto_open_output": window.parity_auto_open.isChecked(),
            "window_geometry": f"{window.width()}x{window.height()}",
            "current_project_file": str(getattr(window, "_project_file", "")),
        }
    )
    save_config(config)
    window._parity_config = config


def _sync_manual_controls_from_mode(window: object) -> None:
    key = str(window.mode.currentData() or "smart_auto")
    custom = key == "custom"
    for widget in (
        window.parity_resolution,
        window.parity_codec,
        window.parity_profile,
        window.parity_effect,
        window.parity_transition,
    ):
        widget.setEnabled(custom)
    if not custom:
        spec = QUICK_MODES.get(key, QUICK_MODES["smart_auto"])
        mappings = (
            (window.parity_resolution, spec.resolution),
            (window.parity_codec, spec.codec),
            (window.parity_profile, spec.profile),
            (window.parity_effect, spec.visual_effect),
            (window.parity_transition, spec.transition),
        )
        for combo, value in mappings:
            index = combo.findData(value)
            if index >= 0:
                combo.setCurrentIndex(index)
        verification_index = window.verification.findText(spec.verification)
        if verification_index >= 0:
            window.verification.setCurrentIndex(verification_index)


def _build_settings_tab(window: object) -> QWidget:
    tab = QWidget()
    layout = QVBoxLayout(tab)
    intro = QLabel(
        "Übernommene Einstellungen der früheren Tk-Version. "
        "Automatik bleibt der Standard; „Eigene Feineinstellung“ schaltet die Expertenfelder frei."
    )
    intro.setWordWrap(True)
    intro.setObjectName("subtitle")
    layout.addWidget(intro)

    form = QFormLayout()
    cfg = window._parity_config
    window.parity_output_mode = _combo(
        tab,
        [("Gemeinsamer Ordner", "Gemeinsamer Ordner"), ("Neben Mediendatei", "Neben Mediendatei")],
        str(cfg.get("output_mode", "Gemeinsamer Ordner")),
    )
    window.parity_resolution = _combo(
        tab,
        [(v, v) for v in ("Original", "1280×720", "1920×1080")],
        str(cfg.get("resolution", "Original")),
    )
    window.parity_codec = _combo(
        tab,
        [("H.264 / libx264", "libx264"), ("H.265 / libx265", "libx265")],
        str(cfg.get("codec", "libx264")),
    )
    window.parity_profile = _combo(
        tab,
        [(spec.label, key) for key, spec in PROFILES.items()],
        str(cfg.get("profile", "fast")),
    )
    window.parity_effect = _combo(
        tab,
        [(spec.label, key) for key, spec in VISUAL_EFFECTS.items()],
        str(cfg.get("visual_effect", "none")),
    )
    window.parity_transition = _combo(
        tab,
        [(spec.label, key) for key, spec in TRANSITIONS.items()],
        str(cfg.get("transition", "none")),
    )
    form.addRow("Ausgabeart", window.parity_output_mode)
    form.addRow("Auflösung", window.parity_resolution)
    form.addRow("Video-Codec", window.parity_codec)
    form.addRow("Renderprofil", window.parity_profile)
    form.addRow("Bildeffekt", window.parity_effect)
    form.addRow("Ein-/Ausblendung", window.parity_transition)
    layout.addLayout(form)

    window.parity_keep_lists = QCheckBox("Dateilisten nach erfolgreicher Produktion behalten")
    window.parity_keep_lists.setChecked(bool(cfg.get("keep_lists", True)))
    window.parity_auto_open = QCheckBox("Ausgabeordner nach erfolgreicher Produktion automatisch öffnen")
    window.parity_auto_open.setChecked(bool(cfg.get("auto_open_output", True)))
    layout.addWidget(window.parity_keep_lists)
    layout.addWidget(window.parity_auto_open)

    archive = QFrame()
    archive.setObjectName("card")
    archive_layout = QFormLayout(archive)
    window.parity_archive_used = QCheckBox("Verwendete Quelldateien nach erfolgreicher Produktion sicher ablegen")
    window.parity_archive_used.setChecked(bool(cfg.get("archive_used", False)))
    window.parity_archive_dir = QLineEdit(str(cfg.get("archive_project_dir", "") or ""))
    window.parity_archive_dir.setPlaceholderText("Projekt-/Archivordner")
    window.parity_archive_suffix = QLineEdit(str(cfg.get("archive_suffix", "__verwendet") or "__verwendet"))
    archive_layout.addRow(window.parity_archive_used)
    archive_layout.addRow("Ablageordner", window.parity_archive_dir)
    archive_layout.addRow("Namenszusatz", window.parity_archive_suffix)
    layout.addWidget(archive)

    appearance = QFrame()
    appearance.setObjectName("card")
    appearance_layout = QFormLayout(appearance)
    window.parity_theme = _combo(
        appearance,
        [
            ("Neon Gravity", "neon_gravity"),
            ("Acid Paper", "acid_paper"),
            ("Toxic Candy", "toxic_candy"),
            ("Ultraviolet", "ultraviolet"),
        ],
        str(cfg.get("theme", "neon_gravity")),
    )
    window.parity_font_scale = QSpinBox()
    window.parity_font_scale.setRange(80, 160)
    window.parity_font_scale.setSuffix(" %")
    window.parity_font_scale.setSingleStep(10)
    window.parity_font_scale.setValue(int(cfg.get("font_scale", 105)))
    appearance_layout.addRow("Farbtheme", window.parity_theme)
    appearance_layout.addRow("Schriftgröße", window.parity_font_scale)
    layout.addWidget(appearance)

    layout.addStretch()
    return tab


def _build_playlist_tab(window: object) -> QWidget:
    tab = QWidget()
    layout = QVBoxLayout(tab)
    intro = QLabel(
        "Audio direkt vorhören. Die Wiedergabe nutzt weiterhin den vorhandenen FFplay-basierten Player."
    )
    intro.setWordWrap(True)
    layout.addWidget(intro)
    window.parity_playlist_list = QListWidget()
    layout.addWidget(window.parity_playlist_list, 1)

    row = QHBoxLayout()
    add = QPushButton("Audios übernehmen")
    remove = QPushButton("Aus Liste entfernen")
    play = QPushButton("▶ Abspielen")
    pause = QPushButton("⏯ Pause/Fortsetzen")
    stop = QPushButton("■ Stop")
    for button in (add, remove, play, pause, stop):
        row.addWidget(button)
    layout.addLayout(row)

    options = QHBoxLayout()
    options.addWidget(QLabel("Wiederholen"))
    window.parity_repeat = _combo(
        tab,
        [("Aus", "off"), ("Aktuelles Audio", "one"), ("Alle", "all")],
        str(window._parity_config.get("playlist_repeat", "off")),
    )
    window.parity_shuffle = QCheckBox("Zufällige Reihenfolge")
    window.parity_shuffle.setChecked(bool(window._parity_config.get("playlist_shuffle", False)))
    options.addWidget(window.parity_repeat)
    options.addWidget(window.parity_shuffle)
    options.addStretch()
    layout.addLayout(options)
    window.parity_playlist_status = QLabel("Noch keine Wiedergabe.")
    window.parity_playlist_status.setWordWrap(True)
    layout.addWidget(window.parity_playlist_status)

    add.clicked.connect(lambda: _playlist_add_from_sources(window))
    remove.clicked.connect(lambda: _playlist_remove(window))
    play.clicked.connect(lambda: _playlist_play(window))
    pause.clicked.connect(lambda: _playlist_pause(window))
    stop.clicked.connect(lambda: _playlist_stop(window))
    window.parity_repeat.currentIndexChanged.connect(lambda *_: _playlist_options(window))
    window.parity_shuffle.toggled.connect(lambda *_: _playlist_options(window))
    return tab


def _refresh_playlist_list(window: object) -> None:
    selected = window.parity_playlist.current
    window.parity_playlist_list.clear()
    for index, path in enumerate(window.parity_playlist.items):
        window.parity_playlist_list.addItem(f"{index + 1:02d} · {path.name}")
    if 0 <= selected < window.parity_playlist_list.count():
        window.parity_playlist_list.setCurrentRow(selected)


def _playlist_add_from_sources(window: object) -> None:
    window.parity_playlist.add(window.audio.paths())
    _refresh_playlist_list(window)
    _save_project_silent(window)


def _playlist_remove(window: object) -> None:
    rows = [window.parity_playlist_list.row(item) for item in window.parity_playlist_list.selectedItems()]
    window.parity_playlist.remove(rows)
    _refresh_playlist_list(window)
    _save_project_silent(window)


def _playlist_options(window: object) -> None:
    window.parity_playlist.repeat = str(window.parity_repeat.currentData() or "off")
    window.parity_playlist.shuffle = window.parity_shuffle.isChecked()
    _save_settings(window)


def _playlist_play(window: object) -> None:
    row = window.parity_playlist_list.currentRow()
    if row >= 0:
        window.parity_playlist.current = row
    if window.parity_playlist.current < 0 and window.parity_playlist.items:
        window.parity_playlist.current = 0
    if window.parity_playlist.current < 0:
        window.parity_playlist_status.setText("Noch kein Audio in der Playlist.")
        return
    path = window.parity_playlist.items[window.parity_playlist.current]
    try:
        window.parity_audio_player.play(path)
    except Exception as exc:
        QMessageBox.warning(window, "Audio konnte nicht gestartet werden", str(exc))
        return
    window.parity_playlist_status.setText(f"Spielt: {path.name}")
    _refresh_playlist_list(window)


def _playlist_pause(window: object) -> None:
    try:
        paused = window.parity_audio_player.toggle_pause()
    except OSError as exc:
        QMessageBox.warning(window, "Pause fehlgeschlagen", str(exc))
        return
    window.parity_playlist_status.setText("Pausiert" if paused else "Wiedergabe läuft")


def _playlist_stop(window: object) -> None:
    window.parity_audio_player.stop()
    window.parity_playlist_status.setText("Wiedergabe gestoppt.")


def _poll_playlist(window: object) -> None:
    player = getattr(window, "parity_audio_player", None)
    playlist = getattr(window, "parity_playlist", None)
    if player is None or playlist is None:
        return
    process = player.process
    if process is not None and process.poll() is not None:
        player.process = None
        next_index = playlist.next_index()
        if next_index is None:
            window.parity_playlist_status.setText("Wiedergabe beendet.")
        else:
            playlist.current = next_index
            _playlist_play(window)


def _build_calendar_tab(window: object) -> QWidget:
    tab = QWidget()
    layout = QVBoxLayout(tab)
    window.parity_calendar = QCalendarWidget()
    layout.addWidget(window.parity_calendar, 1)

    form = QFormLayout()
    window.parity_calendar_type = _combo(
        tab,
        [("Notiz", "note"), ("Aufgabe", "task"), ("Erinnerung", "reminder"), ("Termin", "deadline")],
        "note",
    )
    window.parity_calendar_color = _combo(
        tab,
        [
            ("Neutral", "none"),
            ("Erledigt / Erfolg", "success"),
            ("Beachten", "warning"),
            ("Blockiert", "error"),
            ("Information", "info"),
            ("Aktiv", "active"),
        ],
        "none",
    )
    window.parity_calendar_note = QLineEdit()
    window.parity_calendar_note.setPlaceholderText("Kurze Notiz zum ausgewählten Tag")
    form.addRow("Art", window.parity_calendar_type)
    form.addRow("Markierung", window.parity_calendar_color)
    form.addRow("Notiz", window.parity_calendar_note)
    layout.addLayout(form)

    actions = QHBoxLayout()
    save = QPushButton("Kalendereintrag speichern")
    save.setObjectName("primary")
    remove = QPushButton("Eintrag löschen")
    actions.addWidget(remove)
    actions.addStretch()
    actions.addWidget(save)
    layout.addLayout(actions)
    window.parity_calendar.selectionChanged.connect(lambda: _calendar_load_selected(window))
    save.clicked.connect(lambda: _calendar_save(window))
    remove.clicked.connect(lambda: _calendar_remove(window))
    return tab


def _calendar_key(window: object) -> str:
    return window.parity_calendar.selectedDate().toString("yyyy-MM-dd")


def _calendar_load_selected(window: object) -> None:
    key = _calendar_key(window)
    entry = window._parity_calendar_notes.get(key, {})
    type_index = window.parity_calendar_type.findData(str(entry.get("entry_type", "note")))
    color_index = window.parity_calendar_color.findData(
        str(entry.get("color", window._parity_calendar_marks.get(key, "none")))
    )
    window.parity_calendar_type.setCurrentIndex(max(0, type_index))
    window.parity_calendar_color.setCurrentIndex(max(0, color_index))
    window.parity_calendar_note.setText(str(entry.get("note", "")))


def _calendar_save(window: object) -> None:
    key = _calendar_key(window)
    note = window.parity_calendar_note.text().strip()[:500]
    entry_type = str(window.parity_calendar_type.currentData() or "note")
    color = str(window.parity_calendar_color.currentData() or "none")
    if note or color != "none":
        window._parity_calendar_notes[key] = {
            "note": note,
            "entry_type": entry_type,
            "color": color,
        }
    else:
        window._parity_calendar_notes.pop(key, None)
    if color == "none":
        window._parity_calendar_marks.pop(key, None)
    else:
        window._parity_calendar_marks[key] = color
    _save_project_silent(window)


def _calendar_remove(window: object) -> None:
    key = _calendar_key(window)
    window._parity_calendar_notes.pop(key, None)
    window._parity_calendar_marks.pop(key, None)
    _calendar_load_selected(window)
    _save_project_silent(window)


def _build_maintenance_tab(window: object) -> QWidget:
    tab = QWidget()
    layout = QVBoxLayout(tab)
    intro = QLabel(
        "Diese Schaltflächen sind wieder mit den echten Core-Services verbunden – "
        "keine Demonstrationsdialoge."
    )
    intro.setWordWrap(True)
    layout.addWidget(intro)

    for label, callback in (
        ("Plugins prüfen & Freigaben verwalten", lambda: _plugin_scan(window)),
        ("Update-Paket prüfen & installieren", lambda: _update_package(window)),
        ("Unterbrochene Produktion / Recovery prüfen", lambda: _offer_recovery(window, manual=True)),
        ("Verwendete Dateien sicher ablegen", lambda: _archive_last_results(window)),
        ("Visuelle Freigabe signieren", lambda: _visual_approval(window)),
        ("Ausgabeordner öffnen", lambda: _open_output(window)),
        ("Protokollordner öffnen", lambda: _open_logs(window)),
        ("Handbuch öffnen", lambda: _open_manual(window)),
    ):
        button = QPushButton(label)
        button.clicked.connect(callback)
        layout.addWidget(button)
    layout.addStretch()
    return tab


def _build_parity_dock(window: object) -> None:
    window.parity_dock = QDockWidget("Einstellungen & Werkzeuge", window)
    window.parity_dock.setObjectName("legacyParityDock")
    window.parity_dock.setAllowedAreas(
        Qt.DockWidgetArea.RightDockWidgetArea | Qt.DockWidgetArea.BottomDockWidgetArea
    )
    tabs = QTabWidget()
    window.parity_tabs = tabs
    tabs.addTab(_build_settings_tab(window), "Einstellungen")
    tabs.addTab(_build_playlist_tab(window), "Playlist")
    tabs.addTab(_build_calendar_tab(window), "Kalender")
    tabs.addTab(_build_maintenance_tab(window), "Wartung")
    window.parity_dock.setWidget(tabs)
    window.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, window.parity_dock)
    if hasattr(window, "phase3_dock"):
        window.tabifyDockWidget(window.phase3_dock, window.parity_dock)
    window.parity_dock.hide()


def _select_combo_data(combo: QComboBox, value: object) -> None:
    index = combo.findData(str(value))
    if index >= 0:
        combo.setCurrentIndex(index)


def _apply_project_extras(window: object, state: dict[str, object]) -> None:
    if not getattr(window, "_parity_ready", False):
        return

    playlist_paths = [Path(str(value)) for value in list(state.get("playlist_paths", []))]
    window.parity_playlist.items = [path for path in playlist_paths if path.is_file()]
    window.parity_playlist.current = 0 if window.parity_playlist.items else -1
    _refresh_playlist_list(window)

    slideshow = window.slideshow
    slideshow._parity_order_mode = str(state.get("slideshow_order_mode", "manual"))
    try:
        slideshow._manual_seed = int(state.get("slideshow_random_seed", 0) or 0)
    except (TypeError, ValueError):
        slideshow._manual_seed = 0
    images = slideshow.image_paths()
    start_raw = str(state.get("slideshow_start_image", "") or "")
    end_raw = str(state.get("slideshow_end_image", "") or "")
    start = Path(start_raw) if start_raw else None
    end = Path(end_raw) if end_raw else None
    slideshow._start_image = start if start in images else None
    slideshow._end_image = end if end in images else None
    slideshow._refresh_strip()

    window.parity_archive_used.setChecked(bool(state.get("archive_used", False)))
    window.parity_archive_dir.setText(str(state.get("archive_project_dir", "") or ""))
    window.parity_archive_suffix.setText(
        str(state.get("archive_suffix", "__verwendet") or "__verwendet")
    )

    window._parity_calendar_marks = dict(state.get("calendar_marks", {}) or {})
    window._parity_calendar_notes = dict(state.get("calendar_notes", {}) or {})
    try:
        year = int(state.get("calendar_year", QDate.currentDate().year()))
        month = int(state.get("calendar_month", QDate.currentDate().month()))
        window.parity_calendar.setCurrentPage(year, month)
    except (TypeError, ValueError):
        pass
    _calendar_load_selected(window)


def _collect_project_extras(window: object, state: dict[str, object]) -> dict[str, object]:
    result = dict(state)
    slideshow = window.slideshow
    result.update(
        {
            "playlist_paths": [str(path) for path in window.parity_playlist.items],
            "slideshow_order_mode": str(
                getattr(slideshow, "_parity_order_mode", "manual")
            ),
            "slideshow_random_seed": int(getattr(slideshow, "_manual_seed", 0) or 0),
            "slideshow_start_image": str(getattr(slideshow, "_start_image", "") or ""),
            "slideshow_end_image": str(getattr(slideshow, "_end_image", "") or ""),
            "archive_used": window.parity_archive_used.isChecked(),
            "archive_project_dir": window.parity_archive_dir.text().strip(),
            "archive_suffix": window.parity_archive_suffix.text().strip() or "__verwendet",
            "calendar_year": window.parity_calendar.yearShown(),
            "calendar_month": window.parity_calendar.monthShown(),
            "calendar_marks": dict(window._parity_calendar_marks),
            "calendar_notes": dict(window._parity_calendar_notes),
        }
    )
    return result


def _wrap_project_methods(window: object) -> None:
    if not hasattr(window, "_collect_project_state"):
        return
    original_collect = window._collect_project_state
    original_apply = window._apply_project_state
    original_route = window._route_workspace

    def collect():
        return _collect_project_extras(window, original_collect())

    def apply(state):
        original_apply(state)
        _apply_project_extras(window, state)

    def route(route_name: str):
        original_route(route_name)
        if route_name == "effects":
            window.parity_dock.show()
            window.parity_dock.raise_()
            window.parity_tabs.setCurrentIndex(0)
        elif route_name in {"dashboard", "media", "queue"}:
            window.parity_dock.hide()

    window._collect_project_state = collect
    window._apply_project_state = apply
    window._route_workspace = route


def _save_project_silent(window: object) -> None:
    if hasattr(window, "_save_current_project") and not window.runner.running and not window.preparing:
        window._project_dirty = True
        window._save_current_project(silent=True)


def _build_menu(window: object) -> None:
    bar = window.menuBar()
    bar.clear()

    file_menu = bar.addMenu("&Datei")
    actions = [
        ("Neues Projekt", "Ctrl+N", lambda: window._new_project()),
        ("Projekt öffnen …", "Ctrl+O", lambda: window._open_project()),
        ("Projekt speichern", "Ctrl+S", lambda: window._save_current_project()),
        ("Projekt speichern unter …", "", lambda: window._save_project_as()),
    ]
    for text, shortcut, callback in actions:
        action = QAction(text, window)
        if shortcut:
            action.setShortcut(QKeySequence(shortcut))
        action.triggered.connect(callback)
        file_menu.addAction(action)
    file_menu.addSeparator()
    quit_action = QAction("Beenden", window)
    quit_action.setShortcut(QKeySequence("Ctrl+Q"))
    quit_action.triggered.connect(window.close)
    file_menu.addAction(quit_action)

    media_menu = bar.addMenu("&Medien")
    audio_action = QAction("Audio auswählen …", window)
    audio_action.setShortcut(QKeySequence("Ctrl+Shift+A"))
    audio_action.triggered.connect(window._browse_audio)
    media_action = QAction("Bilder/Videos auswählen …", window)
    media_action.setShortcut(QKeySequence("Ctrl+Shift+M"))
    media_action.triggered.connect(window._browse_media)
    media_menu.addAction(audio_action)
    media_menu.addAction(media_action)
    clear_action = QAction("Dateilisten leeren", window)
    clear_action.triggered.connect(window._clear_lists)
    media_menu.addAction(clear_action)

    view_menu = bar.addMenu("&Ansicht")
    settings_action = QAction("Einstellungen & Werkzeuge", window)
    settings_action.setShortcut(QKeySequence("Ctrl+,"))
    settings_action.triggered.connect(lambda: _show_parity_tab(window, 0))
    view_menu.addAction(settings_action)
    for label, delta, shortcut in (
        ("Schrift größer", 10, "Ctrl++"),
        ("Schrift kleiner", -10, "Ctrl+-"),
    ):
        action = QAction(label, window)
        action.setShortcut(QKeySequence(shortcut))
        action.triggered.connect(
            lambda _checked=False, step=delta: window.parity_font_scale.setValue(
                max(80, min(160, window.parity_font_scale.value() + step))
            )
        )
        view_menu.addAction(action)

    production_menu = bar.addMenu("&Produktion")
    start_action = QAction("Prüfen & Videos erstellen", window)
    start_action.setShortcut(QKeySequence("F9"))
    start_action.triggered.connect(window._start)
    cancel_action = QAction("Sicher abbrechen", window)
    cancel_action.setShortcut(QKeySequence("Esc"))
    cancel_action.triggered.connect(window._cancel)
    open_output = QAction("Ausgabeordner öffnen", window)
    open_output.triggered.connect(lambda: _open_output(window))
    production_menu.addAction(start_action)
    production_menu.addAction(cancel_action)
    production_menu.addAction(open_output)

    tools_menu = bar.addMenu("&Werkzeuge")
    for label, tab_index in (
        ("Playlist", 1),
        ("Kalender", 2),
        ("Wartung", 3),
    ):
        action = QAction(label, window)
        action.triggered.connect(
            lambda _checked=False, index=tab_index: _show_parity_tab(window, index)
        )
        tools_menu.addAction(action)
    diag = QAction("Hilfe & Diagnose", window)
    diag.triggered.connect(lambda: window._route_workspace("diagnostics"))
    tools_menu.addAction(diag)

    help_menu = bar.addMenu("&Hilfe")
    manual = QAction("Handbuch öffnen", window)
    manual.setShortcut(QKeySequence("F1"))
    manual.triggered.connect(lambda: _open_manual(window))
    logs = QAction("Protokollordner öffnen", window)
    logs.triggered.connect(lambda: _open_logs(window))
    about = QAction("Über VideoBatch", window)
    about.triggered.connect(
        lambda: QMessageBox.information(
            window,
            "PROVOWARE VideoBatch 2026",
            f"Version {build_label()}\nQt 6 / Wayland\n\n"
            "Die Qt-Oberfläche verwendet die bestehenden geprüften Core-Services.",
        )
    )
    help_menu.addAction(manual)
    help_menu.addAction(logs)
    help_menu.addAction(about)


def _show_parity_tab(window: object, index: int) -> None:
    window.parity_dock.show()
    window.parity_dock.raise_()
    window.parity_tabs.setCurrentIndex(index)


def _open_path(path: Path) -> None:
    path = Path(path).expanduser()
    QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))


def _open_output(window: object) -> None:
    path = Path(window.output.text().strip()).expanduser()
    try:
        path.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        QMessageBox.warning(window, "Ausgabeordner nicht verfügbar", str(exc))
        return
    _open_path(path)


def _open_logs(window: object) -> None:
    from .paths import state_dir
    path = state_dir() / "logs"
    path.mkdir(parents=True, exist_ok=True)
    _open_path(path)


def _open_manual(window: object) -> None:
    root = Path(__file__).resolve().parents[2]
    target = root / "START_HIER_save_.md"
    if not target.is_file():
        target = root / "README.md"
    _open_path(target)


def _plugin_scan(window: object) -> None:
    checks = scan_plugins(quarantine_invalid=True)
    if not checks:
        QMessageBox.information(
            window,
            "Plugins",
            "Keine Plugins installiert. Die Kernfunktionen sind vollständig verfügbar.",
        )
        return
    report: list[str] = []
    for item in checks:
        if not item.valid:
            report.append(f"✕ {item.plugin_id}: {item.message}")
            continue
        permissions = permission_summary(item.capability, item.key_id)
        identity = build_identity(
            plugin_id=item.plugin_id,
            version=item.version,
            payload_sha256=item.payload_sha256,
            key_id=item.key_id,
            capability=item.capability,
            permissions=permissions,
        )
        approval = validate_approval(identity)
        summary = (
            permissions.plain_text(item.plugin_id, item.key_id)
            + f"\nVersion: {item.version}\nInhalts-Hash: {item.payload_sha256}"
        )
        decision = PluginPermissionDecisionDialog(
            window, summary, approval.status
        ).wait()
        if decision == "revoke":
            status = revoke_approval(item.plugin_id)
            report.append(f"• {item.plugin_id}: {status.message}")
            continue
        if decision != "approve":
            report.append(f"• {item.plugin_id}: unverändert/inaktiv")
            continue
        if item.capability == "validator":
            sandbox = run_plugin_in_sandbox(item.path, "validator", {"probe": True})
            if not sandbox.success:
                report.append(f"✕ {item.plugin_id}: Sandbox fehlgeschlagen – {sandbox.message}")
                continue
        record = grant_approval(identity, permissions)
        report.append(f"✓ {item.plugin_id}: Freigabe gespeichert {record['approved_at']}")
    QMessageBox.information(window, "Plugin-Prüfung abgeschlossen", "\n".join(report))


def _update_package(window: object) -> None:
    package, _ = QFileDialog.getOpenFileName(
        window, "Geprüftes Update-Paket wählen", str(Path.home()), "ZIP-Update (*.zip)"
    )
    if not package:
        return
    package_path = Path(package)
    check = validate_update_package(package_path, build_label())
    if not check.valid:
        QMessageBox.critical(window, "Update nicht gültig", check.message)
        return
    if not update_assistant_dialog(window, check.version, len(check.files)).wait():
        return
    window.next_step.setText("Update-Kandidat wird erstellt und vollständig geprüft …")

    def worker() -> None:
        root = Path(__file__).resolve().parents[2]
        result = apply_update_package(package_path, root, build_label())
        window._parity_bridge.taskFinished.emit("update", result, "")

    threading.Thread(target=worker, daemon=True, name="VideoBatch-Qt-Update").start()


def _offer_recovery(window: object, *, manual: bool = False) -> None:
    payloads = recoverable_batches()
    if not payloads:
        if manual:
            QMessageBox.information(window, "Recovery", "Keine unterbrochene Produktion gefunden.")
        return
    count = sum(int(item.get("recoverable_jobs", 0) or 0) for item in payloads)
    box = QMessageBox(window)
    box.setWindowTitle("Unterbrochene Verarbeitung erkannt")
    box.setText(
        f"{len(payloads)} unterbrochene Stapel mit {count} wiederherstellbaren Aufträgen wurden gefunden."
    )
    restore = box.addButton("Wiederherstellen", QMessageBox.ButtonRole.AcceptRole)
    later = box.addButton("Später", QMessageBox.ButtonRole.RejectRole)
    clear = box.addButton("Liste archivieren", QMessageBox.ButtonRole.DestructiveRole)
    box.exec()
    clicked = box.clickedButton()
    if clicked is later:
        return
    if clicked is clear:
        for payload in payloads:
            journal = payload.get("journal_path")
            if journal:
                acknowledge_recovery(Path(str(journal)), action="dismissed_by_user")
        return
    if clicked is not restore:
        return

    audio, media = recovery_input_paths(payloads)
    if not audio or not media:
        QMessageBox.warning(
            window,
            "Recovery nicht möglich",
            "Die Quelldateien der unterbrochenen Verarbeitung sind nicht mehr vollständig erreichbar.",
        )
        return
    _apply_recovery_options(window, recovery_options(payloads))
    window.audio.add_paths(list(audio))
    window.media.add_paths(list(media))
    for payload in payloads:
        journal = payload.get("journal_path")
        if journal:
            acknowledge_recovery(Path(str(journal)), action="controlled_requeue")
    window._refresh()
    _save_project_silent(window)
    QMessageBox.information(
        window,
        "Recovery vorbereitet",
        "Die unterbrochenen Aufträge wurden wieder in die Oberfläche geladen. "
        "Sie starten erst nach deiner erneuten Prüfung mit F9 oder dem Startknopf.",
    )


def _apply_recovery_options(window: object, options: dict[str, object]) -> None:
    if "output_dir" in options:
        window.output.setText(str(options["output_dir"]))
    if "quick_mode" in options:
        _select_combo_data(window.mode, options["quick_mode"])
    mappings = (
        ("output_mode", window.parity_output_mode),
        ("resolution", window.parity_resolution),
        ("codec", window.parity_codec),
        ("profile", window.parity_profile),
        ("visual_effect", window.parity_effect),
        ("transition", window.parity_transition),
    )
    for key, combo in mappings:
        if key in options:
            _select_combo_data(combo, options[key])
    if "verification" in options:
        index = window.verification.findText(str(options["verification"]))
        if index >= 0:
            window.verification.setCurrentIndex(index)
    if "keep_lists" in options:
        window.parity_keep_lists.setChecked(bool(options["keep_lists"]))
    if "assignment_mode" in options:
        _select_combo_data(window.slideshow.assignment, options["assignment_mode"])
    if "slideshow_transition" in options:
        _select_combo_data(window.slideshow.transition, options["slideshow_transition"])
    if "slideshow_scene_sync" in options:
        window.slideshow.scene_sync.setChecked(bool(options["slideshow_scene_sync"]))


def _archive_results(window: object, results: list[object]) -> None:
    project_text = window.parity_archive_dir.text().strip()
    if not project_text:
        QMessageBox.warning(
            window,
            "Ablageziel fehlt",
            "Für die sichere Ablage zuerst einen Projektordner in den Einstellungen wählen.",
        )
        return
    project = Path(project_text).expanduser()
    suffix = window.parity_archive_suffix.text().strip() or "__verwendet"
    successful = [result for result in results if getattr(result, "success", False)]
    candidate_count = len(
        {
            path
            for result in successful
            for path in (result.job.audio, *result.job.source_media)
        }
    )
    if not candidate_count:
        QMessageBox.information(window, "Dateiablage", "Keine erfolgreich verwendeten Quellen vorhanden.")
        return
    if not archive_preview_dialog(
        window, candidate_count, str(project), suffix
    ).wait():
        return

    def worker() -> None:
        failures: list[str] = []
        records = []
        try:
            recover_archive_transactions(project)
            all_jobs = [result.job for result in results]
            success_jobs = [result.job for result in successful]
            references = Counter(
                path for job in all_jobs for path in (job.audio, *job.source_media)
            )
            successes = Counter(
                path for job in success_jobs for path in (job.audio, *job.source_media)
            )
            for path, count in references.items():
                if successes[path] != count:
                    continue
                try:
                    info = probe_media(path)
                    records.append(archive_file(path, project, info.kind, suffix))
                except Exception as exc:
                    failures.append(f"{path.name}: {exc}")
            manifest = append_manifest(project, records) if records else None
            payload = {
                "records": len(records),
                "failures": failures,
                "manifest": str(manifest or ""),
            }
            window._parity_bridge.taskFinished.emit("archive", payload, "")
        except Exception as exc:
            window._parity_bridge.taskFinished.emit(
                "archive", {}, f"{type(exc).__name__}: {exc}"
            )

    threading.Thread(target=worker, daemon=True, name="VideoBatch-Qt-Archive").start()


def _archive_last_results(window: object) -> None:
    results = list(getattr(window, "_parity_last_results", []))
    _archive_results(window, results)


def _visual_approval(window: object) -> None:
    manifest_path = Path(__file__).resolve().parents[2] / "VISUAL_INSPECTION_MANIFEST.json"
    if not manifest_path.is_file():
        QMessageBox.warning(
            window,
            "Visuelle Freigabe",
            "Das visuelle Prüfmanifest fehlt. Zuerst die vollständige reale Sichtprüfung durchführen.",
        )
        return
    reviewer = VisualApprovalSignDialog(
        window, build_label(), default_reviewer=os.environ.get("USER", "")
    ).wait()
    if not reviewer:
        return
    try:
        sign_visual_approval(
            manifest_path,
            reviewer=reviewer,
            build_id=build_label(),
            project_root=manifest_path.parent,
        )
        import json
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        check = verify_visual_approval(manifest, manifest_path.parent)
        write_inspection_html(
            manifest_path.parent / "visual_inspection" / "index.html", manifest
        )
    except Exception as exc:
        QMessageBox.critical(window, "Freigabe nicht möglich", str(exc))
        return
    QMessageBox.information(window, "Visuelle Freigabe", check.message)


def _task_finished(window: object, kind: str, payload: object, error: str) -> None:
    if error:
        QMessageBox.critical(window, "Vorgang fehlgeschlagen", error)
        return
    if kind == "update":
        result = payload
        QMessageBox.information(
            window,
            "Update abgeschlossen" if result.success else "Update fehlgeschlagen",
            result.message
            + (f"\n\nBericht: {result.report}" if getattr(result, "report", "") else ""),
        )
    elif kind == "archive":
        data = dict(payload)
        message = f"{data.get('records', 0)} Datei(en) sicher abgelegt."
        failures = list(data.get("failures", []))
        if failures:
            message += f"\n{len(failures)} Datei(en) blieben am Ursprungsort."
        if data.get("manifest"):
            message += f"\nManifest: {data['manifest']}"
        QMessageBox.information(window, "Dateiablage abgeschlossen", message)
        window._refresh()


def _batch_finished(window: object, payload_object: object) -> None:
    payload = dict(payload_object)
    results = list(payload.get("results", []))
    window._parity_last_results = results
    cancelled = bool(payload.get("cancelled", False))
    successes = int(payload.get("successes", 0) or 0)
    if cancelled or not successes:
        return
    if window.parity_archive_used.isChecked():
        _archive_results(window, results)
    elif not window.parity_keep_lists.isChecked():
        window._clear_lists()
    if window.parity_auto_open.isChecked():
        QTimer.singleShot(300, lambda: _open_output(window))


def _connect_settings(window: object) -> None:
    widgets = [
        window.parity_output_mode,
        window.parity_resolution,
        window.parity_codec,
        window.parity_profile,
        window.parity_effect,
        window.parity_transition,
        window.parity_keep_lists,
        window.parity_auto_open,
        window.parity_archive_used,
        window.parity_archive_dir,
        window.parity_archive_suffix,
        window.parity_repeat,
        window.parity_shuffle,
    ]
    for widget in widgets:
        if isinstance(widget, QComboBox):
            widget.currentIndexChanged.connect(lambda *_: _save_settings(window))
        elif isinstance(widget, QCheckBox):
            widget.toggled.connect(lambda *_: _save_settings(window))
        elif isinstance(widget, QLineEdit):
            widget.editingFinished.connect(lambda: _save_settings(window))

    window.parity_theme.currentIndexChanged.connect(
        lambda *_: (_apply_theme(window), _save_settings(window))
    )
    window.parity_font_scale.valueChanged.connect(
        lambda *_: (_apply_theme(window), _save_settings(window))
    )
    window.output.editingFinished.connect(lambda: _save_settings(window))
    window.verification.currentIndexChanged.connect(lambda *_: _save_settings(window))
    window.mode.currentIndexChanged.connect(
        lambda *_: (_sync_manual_controls_from_mode(window), _save_settings(window))
    )


def _patch_special_callbacks(window: object) -> None:
    window._show_plugin_dialog = lambda: _plugin_scan(window)
    window._show_plugin_decision = lambda: _plugin_scan(window)
    window._show_update_dialog = lambda: _update_package(window)
    window._show_recovery_dialog = lambda: _offer_recovery(window, manual=True)
    window._show_archive_dialog = lambda: _archive_last_results(window)
    window._show_visual_approval = lambda: _visual_approval(window)


def _finish_parity_init(window: object) -> None:
    if getattr(window, "_parity_ready", False):
        return
    app = QApplication.instance()
    window._parity_base_font_size = app.font().pointSizeF() if app else 10.0
    window._parity_config = load_config()
    window._parity_calendar_marks = {}
    window._parity_calendar_notes = {}
    window._parity_last_results = []
    window._parity_bridge = _ParityBridge(window)

    if window.mode.findData("custom") < 0:
        spec = QUICK_MODES["custom"]
        window.mode.addItem(spec.label, "custom")

    cfg = window._parity_config
    if not getattr(window, "_project_state", {}):
        window.output.setText(str(cfg.get("output_dir", window.output.text())))
        _select_combo_data(window.mode, cfg.get("quick_mode", "smart_auto"))
    verification = str(cfg.get("verification", "Vollständig"))
    index = window.verification.findText(verification)
    if index >= 0:
        window.verification.setCurrentIndex(index)

    window.parity_playlist = Playlist(
        repeat=str(cfg.get("playlist_repeat", "off")),
        shuffle=bool(cfg.get("playlist_shuffle", False)),
    )
    window.parity_audio_player = AudioPlayer()
    _build_parity_dock(window)
    _wrap_project_methods(window)
    _build_menu(window)
    _patch_special_callbacks(window)
    _install_validated_runner(window)

    window._parity_bridge.taskFinished.connect(
        lambda kind, payload, error: _task_finished(window, kind, payload, error)
    )
    window._parity_bridge.batchFinished.connect(
        lambda payload: _batch_finished(window, payload)
    )
    original_callback = window.runner.callback

    def callback(event) -> None:
        original_callback(event)
        if getattr(event, "name", "") == "batch_finished":
            window._parity_bridge.batchFinished.emit(getattr(event, "payload", {}))

    window.runner.callback = callback

    window._parity_ready = True
    _connect_settings(window)
    _sync_manual_controls_from_mode(window)
    _apply_theme(window)

    try:
        _apply_project_extras(window, dict(window._project_state))
    except Exception as exc:
        window._write_log(f"Paritätsdaten konnten nicht vollständig geladen werden: {exc}")

    _save_settings(window)
    window._refresh()
    window._write_log(
        "Qt/Tk-Parität aktiv: Startvalidierung · Expertenoptionen · Einstellungen · "
        "Playlist · Kalender · Recovery · Plugins · Update · Archiv · visuelle Freigabe."
    )

    playlist_timer = QTimer(window)
    playlist_timer.setInterval(500)
    playlist_timer.timeout.connect(lambda: _poll_playlist(window))
    playlist_timer.start()
    window._parity_playlist_timer = playlist_timer

    QTimer.singleShot(450, lambda: _offer_recovery(window, manual=False))


def install_legacy_parity() -> None:
    """Install a temporary migration adapter until Qt has full native parity."""
    _patch_phase2_class()

    from .qt_phase2 import VideoBatchQtPhase2Window
    original_init = VideoBatchQtPhase2Window.__init__
    if getattr(original_init, "_tk_parity_wrapped", False):
        return

    def init(self) -> None:
        original_init(self)
        QTimer.singleShot(0, lambda: _finish_parity_init(self))

    init._tk_parity_wrapped = True
    VideoBatchQtPhase2Window.__init__ = init
