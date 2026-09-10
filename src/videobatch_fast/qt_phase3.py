from __future__ import annotations

import os
import sys
import time
from pathlib import Path

from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import (
    QApplication,
    QDockWidget,
    QFileDialog,
    QMessageBox,
    QTabWidget,
)

from .diagnostics_service import build_diagnostic_payload
from .paths import state_dir
from .project_state import (
    default_project_file,
    load_project_state,
    projects_dir,
    save_project_state,
)
from .qt_phase2 import VideoBatchQtPhase2Window
from .qt_phase3_components import DiagnosticsPanel, ProjectPanel, WorkspaceNavigationPanel
from .qt_theme import APP_STYLE


class VideoBatchQtPhase3Window(VideoBatchQtPhase2Window):
    """Qt Phase 3: project persistence, complete workspace routing and diagnostic labs."""

    AUTOSAVE_INTERVAL_MS = 300_000

    def __init__(self, *, autoload_project: bool = True) -> None:
        self._project_file = default_project_file()
        self._project_state: dict[str, object] = {}
        self._project_dirty = False
        self._loading_project = False
        self._session_id = f"qt-phase3-{os.getpid()}-{int(time.time())}"
        super().__init__()
        self.setWindowTitle("PROVOWARE VideoBatch 2026 · Qt 6 · Phase 3")
        self._build_phase3_workspace()
        self._connect_phase3()
        self._autosave_timer = QTimer(self)
        self._autosave_timer.setInterval(self.AUTOSAVE_INTERVAL_MS)
        self._autosave_timer.timeout.connect(self._autosave_project)
        self._autosave_timer.start()
        if autoload_project:
            self._load_project(self._project_file)
        else:
            self.project_panel.set_project(self._project_file, {"project_name": "Neues Projekt"})
        self._write_log(
            "Qt Phase 3 aktiv: Projektverwaltung · Workspace-Navigation · Diagnose · Assurance · Fehlerlabor."
        )

    def _build_phase3_workspace(self) -> None:
        self.navigation_dock = QDockWidget("Workspace", self)
        self.navigation_dock.setObjectName("phase3NavigationDock")
        self.navigation_dock.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea)
        self.workspace_navigation = WorkspaceNavigationPanel()
        self.navigation_dock.setWidget(self.workspace_navigation)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.navigation_dock)
        self.resizeDocks([self.navigation_dock], [245], Qt.Orientation.Horizontal)

        self.phase3_dock = QDockWidget("Werkzeuge · Phase 3", self)
        self.phase3_dock.setObjectName("phase3Dock")
        self.phase3_dock.setAllowedAreas(
            Qt.DockWidgetArea.RightDockWidgetArea | Qt.DockWidgetArea.BottomDockWidgetArea
        )
        self.phase3_tabs = QTabWidget()
        self.phase3_tabs.setDocumentMode(True)

        self.project_panel = ProjectPanel()
        self.phase3_tabs.addTab(self.project_panel, "Projekt")

        self.diagnostics_panel = DiagnosticsPanel(self._diagnostic_payload)
        self.phase3_tabs.addTab(self.diagnostics_panel, "Diagnose & Assurance")

        self.phase3_dock.setWidget(self.phase3_tabs)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.phase3_dock)
        self.tabifyDockWidget(self.phase2_dock, self.phase3_dock)
        self.phase2_dock.raise_()

    def _connect_phase3(self) -> None:
        self.workspace_navigation.routeRequested.connect(self._route_workspace)
        self.project_panel.newRequested.connect(self._new_project)
        self.project_panel.openRequested.connect(self._open_project)
        self.project_panel.saveRequested.connect(self._save_current_project)
        self.project_panel.saveAsRequested.connect(self._save_project_as)

        self.project_panel.name.textChanged.connect(self._mark_project_dirty)
        self.project_panel.note.textChanged.connect(self._mark_project_dirty)
        self.audio.changed.connect(self._mark_project_dirty)
        self.media.changed.connect(self._mark_project_dirty)
        self.output.textChanged.connect(self._mark_project_dirty)
        self.mode.currentIndexChanged.connect(self._mark_project_dirty)
        self.verification.currentIndexChanged.connect(self._mark_project_dirty)
        self.slideshow.stateChanged.connect(self._mark_project_dirty)
        self.slideshow.orderChanged.connect(self._mark_project_dirty)

    def _route_workspace(self, route: str) -> None:
        self.workspace_navigation.set_active(route)
        if route == "dashboard":
            self.centralWidget().setFocus()
        elif route == "media":
            self.audio.setFocus()
        elif route == "preview":
            self.phase2_dock.show()
            self.phase2_dock.raise_()
            self.phase2_tabs.setCurrentWidget(self.preview_panel)
            self.preview_panel.setFocus()
        elif route == "slideshow":
            self.phase2_dock.show()
            self.phase2_dock.raise_()
            self.phase2_tabs.setCurrentWidget(self.slideshow)
            self.slideshow.setFocus()
        elif route == "effects":
            self.mode.setFocus()
        elif route == "queue":
            self.table.setFocus()
        elif route == "project":
            self.phase3_dock.show()
            self.phase3_dock.raise_()
            self.phase3_tabs.setCurrentWidget(self.project_panel)
            self.project_panel.name.setFocus()
        elif route == "diagnostics":
            self.phase3_dock.show()
            self.phase3_dock.raise_()
            self.phase3_tabs.setCurrentWidget(self.diagnostics_panel)
            self.diagnostics_panel.setFocus()
        self._write_log(f"Workspace: {route} geöffnet.")

    def _collect_project_state(self) -> dict[str, object]:
        state = dict(self._project_state)
        state.update(
            {
                "project_name": self.project_panel.name.text().strip() or "Neues Projekt",
                "quick_note": self.project_panel.note.toPlainText()[:2000],
                "audio_paths": [str(path) for path in self.audio.paths()],
                "media_paths": [str(path) for path in self.media.paths()],
                "playlist_paths": list(state.get("playlist_paths", [])),
                "output_dir": self.output.text().strip(),
                "quick_mode": str(self.mode.currentData() or "smart_auto"),
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

    def _load_project(self, path: Path) -> None:
        project_path, state, healed = load_project_state(path)
        self._project_file = project_path
        self._apply_project_state(state)
        self.project_panel.set_project(project_path, state, healed=healed)
        self._write_log(
            f"Projekt {'repariert und ' if healed else ''}geladen: {project_path.name}."
        )

    def _open_project(self) -> None:
        selected, _ = QFileDialog.getOpenFileName(
            self,
            "VideoBatch-Projekt öffnen",
            str(projects_dir()),
            "VideoBatch-Projekt (*.vbfast.json);;JSON (*.json)",
        )
        if selected:
            self._load_project(Path(selected).expanduser())
            self._route_workspace("project")

    def _new_project(self) -> None:
        if self.runner.running or self.preparing:
            QMessageBox.warning(self, "Produktion läuft", "Während einer laufenden Produktion wird kein neues Projekt angelegt.")
            return
        stamp = time.strftime("%Y%m%d_%H%M%S")
        candidate = projects_dir() / f"projekt_{stamp}.vbfast.json"
        counter = 1
        while candidate.exists():
            candidate = projects_dir() / f"projekt_{stamp}_{counter}.vbfast.json"
            counter += 1
        self._project_file = candidate
        self._project_state = {"project_name": "Neues Projekt"}
        self._loading_project = True
        try:
            self.project_panel.name.setText("Neues Projekt")
            self.project_panel.note.clear()
            self.audio.clear()
            self.media.clear()
            self.output.setText(str(Path.home() / "Videos" / "VideoBatch"))
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
        self._save_current_project()
        self._route_workspace("project")
        self._write_log(f"Neues Projekt sicher angelegt: {candidate.name}.")

    def _save_current_project(self, *_args, silent: bool = False) -> bool:
        if self.runner.running or self.preparing:
            if not silent:
                QMessageBox.information(
                    self,
                    "Speichern verschoben",
                    "Während der laufenden Produktion wird die Projektdatei nicht verändert.",
                )
            return False
        try:
            state = self._collect_project_state()
            saved = save_project_state(self._project_file, state)
        except Exception as exc:
            self._write_log(f"Projekt konnte nicht gespeichert werden: {type(exc).__name__}: {exc}")
            if not silent:
                QMessageBox.critical(self, "Speichern fehlgeschlagen", f"{type(exc).__name__}: {exc}")
            return False
        self._project_state = state
        self._project_dirty = False
        self.project_panel.set_saved(saved)
        self._write_log(f"Projekt gespeichert: {saved.name}.")
        return True

    def _save_project_as(self) -> None:
        selected, _ = QFileDialog.getSaveFileName(
            self,
            "VideoBatch-Projekt speichern unter",
            str(self._project_file),
            "VideoBatch-Projekt (*.vbfast.json);;JSON (*.json)",
        )
        if not selected:
            return
        target = Path(selected).expanduser()
        if target.suffix.lower() != ".json":
            target = target.with_name(target.name + ".vbfast.json")
        self._project_file = target
        self._project_dirty = True
        self._save_current_project()

    def _mark_project_dirty(self, *_args) -> None:
        if self._loading_project:
            return
        self._project_dirty = True
        if hasattr(self, "project_panel"):
            self.project_panel.mark_changed()

    def _autosave_project(self) -> None:
        if self._project_dirty and not self.runner.running and not self.preparing:
            self._save_current_project(silent=True)

    def _diagnostic_payload(self) -> dict[str, object]:
        logs = state_dir() / "logs"
        return build_diagnostic_payload(
            session_id=self._session_id,
            project_file=self._project_file,
            human_log=logs / "qt_phase3_human.log",
            machine_log=logs / "qt_phase3_machine.jsonl",
        )

    def closeEvent(self, event) -> None:
        if self._project_dirty and not self.runner.running and not self.preparing:
            self._save_current_project(silent=True)
        super().closeEvent(event)


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("PROVOWARE VideoBatch 2026 Qt Phase 3")
    app.setStyle("Fusion")
    app.setStyleSheet(APP_STYLE)
    window = VideoBatchQtPhase3Window()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
