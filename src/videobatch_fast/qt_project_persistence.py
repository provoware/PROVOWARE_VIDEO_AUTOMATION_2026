from __future__ import annotations
import time
from pathlib import Path
from PySide6.QtWidgets import QMessageBox


def _collect_project_state(self) -> dict[str, object]:
    state = dict(self._project_state)
    state.update(
        {
            "project_name": self.project_panel.name.text().strip() or "Neues Projekt",
            "quick_note": self.project_panel.note.toPlainText()[:2000],
            "audio_paths": [str(path) for path in self.audio.production_paths()],
            "media_paths": [str(path) for path in self.media.production_paths()],
            "playlist_paths": list(state.get("playlist_paths", [])),
            "output_dir": self.output.text().strip(),
            "quick_mode": str(self.mode.currentData() or "smart_auto"),
            "resolution": str(self.resolution.currentData() or "Original"),
            "profile": str(self.quality.currentData() or "balanced"),
            "visual_effect": str(self.effect.currentData() or "none"),
            "effect_intensity": int(self.effect_intensity.value()),
            "transition": str(self.transition.currentData() or "none"),
            "transition_duration": float(self.fade_seconds.value()),
            "verification": self.verification.currentText(),
            "slideshow_transition_seconds": self.slideshow.transition_seconds,
            "assignment_mode": self.slideshow.assignment_mode,
            "slideshow_transition": self.slideshow.transition_preset,
            "slideshow_scene_sync": self.slideshow.scene_sync_enabled,
            "meta": {
                **(state.get("meta", {}) if isinstance(state.get("meta"), dict) else {}),
                "frontend": "qt-phase3",
            },
        }
    )
    return state


def _apply_project_state(self, state: dict[str, object]) -> None:
    self._loading_project = True
    try:
        self._project_state = dict(state)
        self.project_panel.set_project(self._project_file, state)

        self.audio.clear()
        self.media.clear()
        requested_audio = [Path(str(value)) for value in list(state.get("audio_paths", []))]
        requested_media = [Path(str(value)) for value in list(state.get("media_paths", []))]
        self.audio.add_paths(requested_audio)
        self.media.add_paths(requested_media)

        self.output.setText(str(state.get("output_dir", self.output.text()) or self.output.text()))
        for key, widget in (
            ("resolution", self.resolution),
            ("profile", self.quality),
            ("visual_effect", self.effect),
            ("transition", self.transition),
        ):
            if key in state:
                index = widget.findData(str(state[key]))
                if index >= 0:
                    widget.setCurrentIndex(index)
        if "effect_intensity" in state:
            try:
                strength = float(state["effect_intensity"])
                if strength.is_integer() and 0 <= strength <= 100:
                    self.effect_intensity.setValue(int(strength))
            except (TypeError, ValueError, OverflowError):
                pass
        if "transition_duration" in state:
            try:
                duration = float(state["transition_duration"])
                if 0 <= duration <= 5:
                    self.fade_seconds.setValue(duration)
            except (TypeError, ValueError, OverflowError):
                pass
        if "slideshow_transition_seconds" in state:
            try:
                seconds = float(state["slideshow_transition_seconds"])
                if 0 <= seconds <= 5:
                    self.slideshow.custom_transition_seconds.setValue(seconds)
            except (TypeError, ValueError, OverflowError):
                pass
        verification_index = self.verification.findText(str(state.get("verification", "Vollständig")))
        if verification_index >= 0:
            self.verification.setCurrentIndex(verification_index)
        mode_index = self.mode.findData(str(state.get("quick_mode", "smart_auto")))
        if mode_index >= 0:
            self.mode.setCurrentIndex(mode_index)

        assignment_index = self.slideshow.assignment.findData(str(state.get("assignment_mode", "pairwise")))
        if assignment_index >= 0:
            self.slideshow.assignment.setCurrentIndex(assignment_index)
        transition_index = self.slideshow.transition.findData(str(state.get("slideshow_transition", "auto")))
        if transition_index >= 0:
            self.slideshow.transition.setCurrentIndex(transition_index)
        self.slideshow.scene_sync.setChecked(bool(state.get("slideshow_scene_sync", False)))
        self._refresh()

        missing_audio = len(requested_audio) - len(self.audio.paths())
        missing_media = len(requested_media) - len(self.media.paths())
        if missing_audio or missing_media:
            self._write_log(
                "Projekt geladen, aber nicht alle Quelldateien sind erreichbar: "
                f"Audio fehlt {max(0, missing_audio)} · Medien fehlen {max(0, missing_media)}."
            )
    finally:
        self._loading_project = False
        self._project_dirty = False


def _new_project(self) -> None:
    from .qt_phase3 import projects_dir, save_project_state

    if self.runner.running or self.preparing:
        QMessageBox.warning(self, "Produktion läuft", "Während einer laufenden Produktion wird kein neues Projekt angelegt.")
        return
    if self._project_dirty and not self._save_current_project():
        # Do not discard changes on a failed autosave.
        return
    stamp = time.strftime("%Y%m%d_%H%M%S")
    candidate = projects_dir() / f"projekt_{stamp}.vbfast.json"
    counter = 1
    while candidate.exists():
        candidate = projects_dir() / f"projekt_{stamp}_{counter}.vbfast.json"
        counter += 1
    # Reserve the new project safely BEFORE clearing the old workspace.
    try:
        save_project_state(candidate, {"project_name": "Neues Projekt"})
    except (OSError, ValueError, TypeError) as exc:
        QMessageBox.warning(
            self, "Neues Projekt nicht erstellt",
            "Das neue Projekt konnte nicht gespeichert werden. "
            f"Das bisherige Projekt bleibt erhalten.\n\nGrund: {exc}"
        )
        return
    self._project_file = candidate
    self._project_state = {"project_name": "Neues Projekt"}
    self._loading_project = True
    try:
        self.project_panel.name.setText("Neues Projekt")
        self.project_panel.note.clear()
        self.audio.clear()
        self.media.clear()
        # Keep the user-selected global destination when creating a project.
        mode_index = self.mode.findData("smart_auto")
        if mode_index >= 0:
            self.mode.setCurrentIndex(mode_index)
        self.slideshow.assignment.setCurrentIndex(0)
        transition_index = self.slideshow.transition.findData("auto")
        if transition_index >= 0:
            self.slideshow.transition.setCurrentIndex(transition_index)
        self.slideshow.scene_sync.setChecked(False)
        self._refresh()
    finally:
        self._loading_project = False
    self._project_dirty = True
    saved = self._save_current_project(silent=True)
    self._route_workspace("project")
    if saved:
        self._write_log(f"Neues Projekt sicher angelegt: {candidate.name}.")
    else:
        QMessageBox.warning(
            self, "Neues Projekt noch nicht vollständig gespeichert",
            "Das neue Projekt wurde angelegt, aber seine aktuellen Angaben "
            "konnten nicht gespeichert werden. Das Projekt bleibt geöffnet "
            "und als ungespeichert markiert. Bitte erneut speichern."
        )


def _persist_project_to(self, target: Path, *, silent: bool = False) -> bool:
    """Write first and update the active project only after successful I/O."""
    from .qt_phase3 import save_project_state
    if self.runner.running or self.preparing:
        if not silent:
            QMessageBox.information(
                self, "Speichern verschoben",
                "Während einer laufenden Produktion wird die Projektdatei nicht verändert."
            )
        return False
    try:
        state = self._collect_project_state()
        saved = save_project_state(target, state)
    except Exception as exc:
        self._write_log(
            f"Projekt konnte nicht gespeichert werden: {type(exc).__name__}: {exc}"
        )
        if not silent:
            QMessageBox.critical(
                self, "Projekt nicht gespeichert",
                "Der Speicherort ist möglicherweise nicht erreichbar oder voll. "
                "Das aktuelle Projekt bleibt geöffnet.\n\n"
                f"Technische Einzelheiten: {type(exc).__name__}: {exc}"
            )
        return False
    self._project_file = saved
    self._project_state = state
    self._project_dirty = False
    self.project_panel.set_saved(saved)
    self._write_log(f"Projekt gespeichert: {saved.name}.")
    return True
