from __future__ import annotations

import json
import threading
from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .assurance import ScenarioResult, run_scenarios
from .fault_lab import FaultLabResult, run_fault_lab


WORKSPACE_ROUTES: tuple[tuple[str, str, str], ...] = (
    ("dashboard", "Übersicht", "Einfacher Drei-Schritt-Ablauf und aktueller Status"),
    ("media", "1 · Dateien", "Audio, Bilder und Videos auswählen"),
    ("preview", "Vorschau", "Eine ausgewählte Datei ansehen und prüfen"),
    ("slideshow", "Diashow", "Reihenfolge, Übergänge und Szenen einstellen"),
    ("effects", "2 · Ausgabe", "Zielordner, Verarbeitung und Kontrolle festlegen"),
    ("queue", "3 · Produktion", "Automatische Aufträge und Fortschritt prüfen"),
    ("project", "Projekt", "Projekt öffnen, speichern und Notiz verwalten"),
    ("diagnostics", "Hilfe & Diagnose", "System prüfen und technische Diagnose öffnen"),
)


class WorkspaceNavigationPanel(QFrame):
    routeRequested = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("panel")
        self.buttons: dict[str, QPushButton] = {}
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        title = QLabel("Bereiche")
        title.setObjectName("section")
        layout.addWidget(title)
        self.hint = QLabel("Übersicht: einfacher Drei-Schritt-Ablauf und aktueller Status")
        self.hint.setObjectName("subtitle")
        self.hint.setWordWrap(True)
        layout.addWidget(self.hint)

        for route, label, description in WORKSPACE_ROUTES:
            button = QPushButton(label)
            button.setObjectName("workspaceNav")
            button.setToolTip(description)
            button.setAccessibleName(label)
            button.setAccessibleDescription(description)
            button.clicked.connect(lambda _checked=False, key=route: self.routeRequested.emit(key))
            self.buttons[route] = button
            layout.addWidget(button)
        layout.addStretch()
        self.set_active("dashboard")

    def set_active(self, route: str) -> None:
        descriptions = {key: description for key, _label, description in WORKSPACE_ROUTES}
        self.hint.setText(descriptions.get(route, "Arbeitsbereich auswählen."))
        for key, button in self.buttons.items():
            button.setProperty("active", key == route)
            button.style().unpolish(button)
            button.style().polish(button)


class ProjectPanel(QFrame):
    newRequested = Signal()
    openRequested = Signal()
    saveRequested = Signal()
    saveAsRequested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("panel")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)

        title = QLabel("Projektverwaltung")
        title.setObjectName("section")
        layout.addWidget(title)
        intro = QLabel(
            "Projektdateien speichern Quellen, Ausgabe, Schnellmodus, Diashow-Einstellungen, "
            "Kalenderdaten und vorhandene Workspace-Profile sicher als .vbfast.json."
        )
        intro.setObjectName("subtitle")
        intro.setWordWrap(True)
        layout.addWidget(intro)

        layout.addWidget(QLabel("Projektname"))
        self.name = QLineEdit("Neues Projekt")
        layout.addWidget(self.name)

        layout.addWidget(QLabel("Kurze Projektnotiz"))
        self.note = QPlainTextEdit()
        self.note.setMaximumHeight(110)
        self.note.setPlaceholderText("Wichtige Info zum Projekt …")
        layout.addWidget(self.note)

        self.path_label = QLabel("Noch keine Projektdatei geladen.")
        self.path_label.setObjectName("subtitle")
        self.path_label.setWordWrap(True)
        layout.addWidget(self.path_label)

        self.status_label = QLabel("BEREIT")
        self.status_label.setObjectName("statusChip")
        layout.addWidget(self.status_label)

        first = QHBoxLayout()
        new_button = QPushButton("＋ Neues Projekt")
        open_button = QPushButton("Öffnen …")
        new_button.clicked.connect(self.newRequested.emit)
        open_button.clicked.connect(self.openRequested.emit)
        first.addWidget(new_button)
        first.addWidget(open_button)
        layout.addLayout(first)

        second = QHBoxLayout()
        save_button = QPushButton("Speichern")
        save_button.setObjectName("primary")
        save_as_button = QPushButton("Speichern unter …")
        save_button.clicked.connect(self.saveRequested.emit)
        save_as_button.clicked.connect(self.saveAsRequested.emit)
        second.addWidget(save_button)
        second.addWidget(save_as_button)
        layout.addLayout(second)
        layout.addStretch()

    def set_project(self, path: Path, state: dict[str, object], *, healed: bool = False) -> None:
        self.name.setText(str(state.get("project_name", "Neues Projekt") or "Neues Projekt"))
        self.note.setPlainText(str(state.get("quick_note", "") or ""))
        self.path_label.setText(str(path))
        self.status_label.setText("REPARIERT · bitte prüfen" if healed else "GELADEN")

    def set_saved(self, path: Path) -> None:
        self.path_label.setText(str(path))
        self.status_label.setText("GESPEICHERT")

    def mark_changed(self) -> None:
        if self.status_label.text() != "UNGESPEICHERT":
            self.status_label.setText("UNGESPEICHERT")


class DiagnosticsPanel(QFrame):
    resultsReady = Signal(str, object)
    runFailed = Signal(str, str)

    def __init__(
        self,
        diagnostic_provider: Callable[[], dict[str, object]],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("panel")
        self._diagnostic_provider = diagnostic_provider
        self._running = False
        self._buttons: list[QPushButton] = []
        self.resultsReady.connect(self._show_results)
        self.runFailed.connect(self._show_failure)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        title = QLabel("Diagnose · Assurance · Fehlerlabor")
        title.setObjectName("section")
        layout.addWidget(title)
        hint = QLabel(
            "Diagnose liest den aktuellen Zustand. Assurance prüft Schutzverträge. "
            "Das Fehlerlabor simuliert kontrollierte Fehler nur in temporären Testordnern."
        )
        hint.setObjectName("subtitle")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        actions = QHBoxLayout()
        for text, callback in (
            ("Schnelldiagnose", self.run_diagnostic),
            ("Assurance starten", lambda: self._run_async("assurance")),
            ("Fehlerlabor starten", lambda: self._run_async("fault_lab")),
        ):
            button = QPushButton(text)
            button.clicked.connect(callback)
            self._buttons.append(button)
            actions.addWidget(button)
        layout.addLayout(actions)

        self.status = QLabel("BEREIT")
        self.status.setObjectName("statusChip")
        layout.addWidget(self.status)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Prüfung", "Status", "Meldung", "Lösung / Nachweis"])
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table, 1)

        self.detail = QPlainTextEdit()
        self.detail.setReadOnly(True)
        self.detail.setMaximumHeight(180)
        self.detail.setPlaceholderText("Technische Kurzdetails …")
        layout.addWidget(self.detail)

    @property
    def running(self) -> bool:
        return self._running

    def run_diagnostic(self) -> None:
        try:
            payload = self._diagnostic_provider()
        except Exception as exc:
            self._show_failure("diagnostic", f"{type(exc).__name__}: {exc}")
            return
        registry_errors = list(payload.get("registry_errors", []))
        status = "pass" if not registry_errors else "warning"
        rows = [
            {
                "scenario_id": "system_diagnostic",
                "status": status,
                "message": "System- und Projektzustand gelesen.",
                "solution": "Registryfehler prüfen." if registry_errors else "Keine Aktion nötig.",
            }
        ]
        self._show_rows("diagnostic", rows)
        self.detail.setPlainText(json.dumps(payload, ensure_ascii=False, indent=2, default=str))

    def _run_async(self, kind: str) -> None:
        if self._running:
            return
        self._running = True
        self.status.setText("PRÜFT …")
        for button in self._buttons:
            button.setEnabled(False)

        def worker() -> None:
            try:
                results = run_scenarios() if kind == "assurance" else run_fault_lab()
                self.resultsReady.emit(kind, results)
            except Exception as exc:
                self.runFailed.emit(kind, f"{type(exc).__name__}: {exc}")

        threading.Thread(target=worker, daemon=True, name=f"VideoBatch-Qt-{kind}").start()

    def _show_results(self, kind: str, results_object: object) -> None:
        results = list(results_object)
        rows: list[dict[str, object]] = []
        for result in results:
            if isinstance(result, ScenarioResult):
                rows.append(
                    {
                        "scenario_id": result.scenario_id,
                        "status": result.status,
                        "message": result.message,
                        "solution": result.solution,
                    }
                )
            elif isinstance(result, FaultLabResult):
                rows.append(
                    {
                        "scenario_id": result.scenario_id,
                        "status": result.status,
                        "message": result.message,
                        "solution": result.evidence or f"{result.duration_seconds:.3f} s",
                    }
                )
        self._show_rows(kind, rows)
        self._finish_run()

    def _show_rows(self, kind: str, rows: list[dict[str, object]]) -> None:
        self.table.setRowCount(len(rows))
        failed = 0
        for row_index, row in enumerate(rows):
            status = str(row.get("status", ""))
            if status in {"failed", "fail"}:
                failed += 1
            values = (
                str(row.get("scenario_id", "")),
                status,
                str(row.get("message", "")),
                str(row.get("solution", "")),
            )
            for column, value in enumerate(values):
                self.table.setItem(row_index, column, QTableWidgetItem(value))
        self.status.setText("GRÜN" if not failed else f"ROT · {failed} Fehler")
        self.detail.setPlainText(f"{kind}: {len(rows)} Prüfungen · {failed} Fehler")

    def _show_failure(self, kind: str, message: str) -> None:
        self.status.setText("FEHLER")
        self.detail.setPlainText(f"{kind}: {message}")
        self._finish_run()

    def _finish_run(self) -> None:
        self._running = False
        for button in self._buttons:
            button.setEnabled(True)
