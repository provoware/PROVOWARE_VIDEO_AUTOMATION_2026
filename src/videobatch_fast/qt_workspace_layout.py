from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QProgressBar, QPushButton, QStackedWidget,
    QVBoxLayout, QWidget,
)

from .qt_desktop_actions import open_output_folder


class HelpPanel(QFrame):
    """Beginner-oriented help that stays inside the verified Qt workspace."""

    routeRequested = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("panel")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        title = QLabel("Schnellhilfe · ohne Fachbegriffe")
        title.setObjectName("section")
        layout.addWidget(title)
        intro = QLabel(
            "Für ein normales Video brauchst du nur drei Schritte. "
            "Die Zusatzbereiche kannst du zunächst ignorieren."
        )
        intro.setObjectName("subtitle")
        intro.setWordWrap(True)
        layout.addWidget(intro)

        for label, description, route in (
            ("1 · Dateien auswählen", "Audio und passende Bilder oder Videos hinzufügen.", "media"),
            ("2 · Ausgabe festlegen", "Zielordner und einen Schnellmodus prüfen.", "effects"),
            ("3 · Produktion öffnen", "Aufträge prüfen, starten und Fortschritt beobachten.", "queue"),
        ):
            button = QPushButton(label)
            button.setObjectName("workspaceNav")
            button.setToolTip(description)
            button.setAccessibleName(label)
            button.setAccessibleDescription(description)
            button.clicked.connect(lambda _checked=False, key=route: self.routeRequested.emit(key))
            layout.addWidget(button)
            hint = QLabel(description)
            hint.setObjectName("subtitle")
            hint.setWordWrap(True)
            layout.addWidget(hint)

        safety = QLabel(
            "Status: ✓ BEREIT (grün) · ⚠ PRÜFEN (gelb) · ✕ GESTOPPT (rot).\n"
            "Bei ROT zuerst die Meldung lesen. Originalmedien werden als Quellen gelesen."
        )
        safety.setObjectName("safeHint")
        safety.setWordWrap(True)
        layout.addWidget(safety)
        diagnose = QPushButton("Technische Diagnose öffnen")
        diagnose.clicked.connect(lambda _checked=False: self.routeRequested.emit("diagnostics"))
        layout.addWidget(diagnose)
        layout.addStretch()


def _request_route(window, route: str) -> None:
    handler = getattr(window, "_route_workspace", None)
    if callable(handler):
        handler(route)
        return
    set_workflow_route(window, route)
    target = {"media": window.audio, "effects": window.output, "queue": window.table}.get(route)
    if target is not None:
        target.setFocus()


def _overview_page(window) -> QFrame:
    panel = QFrame()
    panel.setObjectName("panel")
    layout = QVBoxLayout(panel)
    layout.setContentsMargins(18, 16, 18, 16)
    layout.setSpacing(10)
    title = QLabel("Übersicht · drei klare Arbeitsschritte")
    title.setObjectName("section")
    layout.addWidget(title)
    intro = QLabel(
        "Jeder Hauptschritt besitzt eine eigene Seite. Dadurch bleiben Bedienelemente "
        "auch bei großer Schrift vollständig sichtbar."
    )
    intro.setObjectName("panelHint")
    intro.setWordWrap(True)
    layout.addWidget(intro)

    for label, description, route in (
        ("1 · Dateien", "Audio und Bilder/Videos auswählen und die Paarung prüfen.", "media"),
        ("2 · Ausgabe", "Zielordner, Verarbeitung und Kontrolle festlegen.", "effects"),
        ("3 · Produktion", "Aufträge kontrollieren, starten und Fortschritt sehen.", "queue"),
    ):
        row = QFrame()
        row.setObjectName("overviewStep")
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(10, 8, 10, 8)
        button = QPushButton(label)
        button.setObjectName("workspaceNav")
        button.setMinimumWidth(180)
        button.clicked.connect(lambda _checked=False, key=route: _request_route(window, key))
        hint = QLabel(description)
        hint.setObjectName("subtitle")
        hint.setWordWrap(True)
        row_layout.addWidget(button)
        row_layout.addWidget(hint, 1)
        layout.addWidget(row)
    layout.addStretch()
    return panel


def build_workflow_stack(window) -> QStackedWidget:
    stack = QStackedWidget()
    stack.setObjectName("workflowPages")
    pages = {
        "dashboard": _overview_page(window),
        "media": window._sources_panel(),
        "effects": window._settings_panel(),
        "queue": window._queue_panel(),
    }
    for page in pages.values():
        stack.addWidget(page)
    window.workflow_stack = stack
    window._workflow_pages = pages
    return stack


def set_workflow_route(window, route: str) -> None:
    pages = getattr(window, "_workflow_pages", {})
    page_key = route if route in pages else "dashboard"
    if page_key in pages:
        window.workflow_stack.setCurrentWidget(pages[page_key])
    window._active_workflow_route = route

    guide = getattr(window, "workflow_guide", None)
    if guide is not None:
        guide.setVisible(route == "dashboard")
    for card in getattr(window, "_kpi_cards", []):
        card.setVisible(route == "dashboard")

    footer = getattr(window, "action_footer", None)
    if footer is not None:
        footer.setVisible(route in {"dashboard", "media", "effects", "queue"})
    production = route == "queue"
    for widget in getattr(window, "_production_footer_widgets", []):
        widget.setVisible(production)

    active_step = {"media": "files", "effects": "output", "queue": "start"}.get(route, "")
    for name, label in (
        ("files", getattr(window, "step_files", None)),
        ("output", getattr(window, "step_output", None)),
        ("start", getattr(window, "step_start", None)),
    ):
        if label is not None:
            label.setProperty("active", name == active_step)
            label.style().unpolish(label)
            label.style().polish(label)


def build_footer(window, outer: QVBoxLayout) -> None:
    footer = QFrame()
    footer.setObjectName("actionFooter")
    window.action_footer = footer
    layout = QVBoxLayout(footer)
    layout.setContentsMargins(12, 9, 12, 9)
    layout.setSpacing(7)

    window.next_step = QLabel("Nächster Schritt: 1 · Dateien auswählen")
    window.next_step.setObjectName("nextStep")
    window.next_step.setAccessibleDescription("Der sichtbare Text nennt den aktuell empfohlenen nächsten Arbeitsschritt.")
    window.next_step.setWordWrap(True)
    layout.addWidget(window.next_step)

    window.activity_detail = QLabel("Keine Verarbeitung aktiv · bereit für neue Aufträge")
    window.activity_detail.setObjectName("subtitle")
    window.activity_detail.setAccessibleDescription("Der sichtbare Text beschreibt den aktuellen Arbeitszustand.")
    window.activity_detail.setWordWrap(True)
    layout.addWidget(window.activity_detail)

    total_label = QLabel("Gesamt")
    total_row = QHBoxLayout()
    total_row.addWidget(total_label)
    window.progress = QProgressBar()
    window.progress.setRange(0, 100)
    window.progress.setAccessibleName("Gesamtfortschritt")
    window.progress.setFormat("Bereit · %p %")
    total_row.addWidget(window.progress, 1)
    layout.addLayout(total_row)

    job_label = QLabel("Auftrag")
    action_row = QHBoxLayout()
    action_row.addWidget(job_label)
    window.job_progress = QProgressBar()
    window.job_progress.setObjectName("jobProgress")
    window.job_progress.setRange(0, 100)
    window.job_progress.setAccessibleName("Fortschritt des aktuellen Auftrags")
    window.job_progress.setFormat("Kein Auftrag aktiv · %p %")
    action_row.addWidget(window.job_progress, 1)
    window.cancel = QPushButton("Abbrechen")
    window.cancel.setObjectName("danger")
    window.cancel.setAccessibleDescription("Bricht die laufende Verarbeitung kontrolliert ab.")
    window.cancel.setEnabled(False)
    window.start = QPushButton("▶ 3 · Videos erstellen")
    window.start.setObjectName("primary")
    window.start.setAccessibleDescription("Startet die geprüften Video-Aufträge.")
    window.start.setMinimumWidth(220)
    action_row.addWidget(window.cancel)
    action_row.addWidget(window.start)
    layout.addLayout(action_row)

    result_label = QLabel("Nach Abschluss")
    result_row = QHBoxLayout()
    result_row.addWidget(result_label)
    window.open_output = QPushButton("Ausgabeordner öffnen")
    window.open_output.setAccessibleDescription("Öffnet den Ordner mit den fertigen Videos.")
    window.open_output.setEnabled(False)
    window.open_output.clicked.connect(lambda: open_output_folder(window))
    window.show_result_log = QPushButton("Ergebnisprotokoll anzeigen")
    window.show_result_log.setAccessibleDescription("Öffnet die technischen Meldungen zum letzten Durchlauf.")
    window.show_result_log.setEnabled(False)
    window.show_result_log.clicked.connect(lambda: window.log_toggle.setChecked(True))
    result_row.addWidget(window.open_output)
    result_row.addWidget(window.show_result_log)
    result_row.addStretch()
    layout.addLayout(result_row)

    window._production_footer_widgets = [
        window.activity_detail, total_label, window.progress, job_label, window.job_progress,
        window.cancel, window.start, result_label, window.open_output, window.show_result_log,
    ]
    outer.addWidget(footer)
