from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QMessageBox, QProgressBar, QPushButton,
    QScrollArea, QStackedWidget, QVBoxLayout, QWidget,
)

from .qt_desktop_actions import open_output_folder
from .qt_responsive_controls import ResponsiveControlRow


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
            ("2 · Videoeinstellungen", "Auflösung, Qualität, Bildeffekt und Zielordner oben ändern.", "effects"),
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
            "Bei ROT zuerst die Meldung lesen. Nicht mit sudo, chmod -R 777 oder "
            "rekursiven Besitzänderungen improvisieren. Originalmedien werden als Quellen gelesen."
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
    title = QLabel("Hilfe und Werkzeuge")
    title.setObjectName("section")
    layout.addWidget(title)
    intro = QLabel(
        "Musik und Bilder auf der Seite Dateien wählen. Auflösung, Qualität, Effekt "
        "und Zielordner sind immer oben erreichbar. Zum Starten Produktion öffnen."
    )
    intro.setObjectName("panelHint")
    intro.setWordWrap(True)
    layout.addWidget(intro)

    for label, description, route in (
        ("1 · Dateien", "Audio und Bilder/Videos auswählen und die Paarung prüfen.", "media"),
        ("Erweiterte Einstellungen", "Selten benötigte Prüf- und Sicherheitsoptionen.", "effects"),
        ("2 · Produktion", "Aufträge kontrollieren, starten und Fortschritt sehen.", "queue"),
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
    tools_hint = QLabel("Zusätzliche Werkzeuge")
    tools_hint.setObjectName("section")
    layout.addWidget(tools_hint)
    hash_help = QPushButton("Hilfe: SHA-256 und Prüfstatus verstehen")
    hash_help.setObjectName("workspaceNav")
    hash_help.setAccessibleDescription(
        "Erklärt Dateifingerabdruck, Medienindex und Entwicklungsprüfungen."
    )
    hash_help.clicked.connect(
        lambda _checked=False: QMessageBox.information(
            panel,
            "SHA-256 und Prüfstatus",
            "SHA-256 ist ein digitaler Fingerabdruck des Dateiinhalts. "
            "Er hilft, Veränderungen an Dateien zu erkennen.\n\n"
            "Dein Medienindex zeigt Musik, Fotos und Videos. "
            "Der getrennte Projekt-Dateiindex ist ein Werkzeug für Entwickler "
            "und verändert keine Originalmedien.\n\n"
            "Ein bereits bestandener Entwicklungstest darf nur bei nachweislich "
            "gleichen Voraussetzungen erneut verwendet werden. "
            "Sicherheits- und Releaseprüfungen bleiben weiterhin Pflicht.\n\n"
            "Mehr: docs/BENUTZERHANDBUCH.md, Abschnitt SHA-256."
        )
    )
    layout.addWidget(hash_help)
    for text, route in (
        ("Bildvorschau öffnen", "preview"),
        ("Diashow öffnen", "slideshow"),
        ("Projektverwaltung", "project"),
        ("Hilfe öffnen", "help"),
        ("Diagnose öffnen", "diagnostics"),
    ):
        button = QPushButton(text)
        button.setObjectName("workspaceNav")
        button.clicked.connect(lambda _checked=False, key=route: _request_route(window, key))
        layout.addWidget(button)
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
    tabs = getattr(window, "main_tabs", None)
    positions = {"media": 0, "queue": 1, "effects": 2, "dashboard": 3}
    if tabs is not None and page_key in positions and tabs.currentIndex() != positions[page_key]:
        tabs.blockSignals(True)
        try:
            tabs.setCurrentIndex(positions[page_key])
        finally:
            tabs.blockSignals(False)

    guide = getattr(window, "workflow_guide", None)
    if guide is not None:
        guide.setVisible(False)
    for card in getattr(window, "_kpi_cards", []):
        card.setVisible(False)

    footer = getattr(window, "action_footer", None)
    if footer is not None:
        footer.setVisible(route in {"dashboard", "media", "effects", "queue"})
    footer_scroll = getattr(window, "action_footer_scroll", None)
    if footer_scroll is not None:
        footer_scroll.setVisible(route in {"dashboard", "media", "effects", "queue"})
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
    layout.setContentsMargins(8, 4, 8, 4)
    layout.setSpacing(3)

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

    # Small, always-visible production meters share the upper status dashboard.
    total_label = QLabel("Gesamt")
    window.progress = QProgressBar()
    window.progress.setRange(0, 100)
    window.progress.setAccessibleName("Gesamtfortschritt")
    window.progress.setFormat("Bereit · %p %")

    job_label = QLabel("Auftrag")
    window.job_progress = QProgressBar()
    window.job_progress.setObjectName("jobProgress")
    window.job_progress.setRange(0, 100)
    window.job_progress.setAccessibleName("Fortschritt des aktuellen Auftrags")
    window.job_progress.setFormat("Kein Auftrag aktiv · %p %")
    meters = window.progress_dashboard_layout
    meters.addWidget(total_label, 0, 0)
    meters.addWidget(window.progress, 0, 1)
    meters.addWidget(job_label, 1, 0)
    meters.addWidget(window.job_progress, 1, 1)

    window.cancel = QPushButton("Abbrechen")
    window.cancel.setObjectName("danger")
    window.cancel.setAccessibleDescription("Bricht die laufende Verarbeitung kontrolliert ab.")
    window.cancel.setEnabled(False)
    window.start = QPushButton("▶ Videos erstellen")
    window.start.setObjectName("primary")
    window.start.setAccessibleDescription("Startet die geprüften Video-Aufträge.")
    window.start.setMinimumWidth(155)
    window.probe_button = QPushButton("▶ Probevideo · max. 10 Sekunden")
    window.probe_button.setObjectName("secondary")
    window.probe_button.setToolTip(
        "Erstellt ein kurzes Video nur aus dem ersten normalen Audio-/Medienpaar. "
        "Die Ausgabe landet getrennt im Probevideo-Ordner."
    )
    window.probe_button.setAccessibleName("Kurzes Probevideo aus dem ersten Dateipaar")
    action_row = ResponsiveControlRow((window.cancel, window.probe_button, window.start))
    window._responsive_control_rows.append(action_row)
    layout.addWidget(action_row)

    result_label = QLabel("Nach Abschluss")

    window.open_output = QPushButton("Ausgabeordner öffnen")
    window.open_output.setAccessibleDescription("Öffnet den Ordner mit den fertigen Videos.")
    window.open_output.setEnabled(False)
    window.open_output.clicked.connect(lambda: open_output_folder(window))
    window.show_result_log = QPushButton("Ergebnisprotokoll anzeigen")
    window.show_result_log.setAccessibleDescription("Öffnet die technischen Meldungen zum letzten Durchlauf.")
    window.show_result_log.setEnabled(False)
    window.show_result_log.clicked.connect(lambda: window.log_toggle.setChecked(True))
    window.open_probe_button = QPushButton("Probevideo öffnen")
    window.open_probe_button.setVisible(False)
    window.open_probe_button.setEnabled(False)
    result_row = ResponsiveControlRow((result_label, window.open_output, window.open_probe_button, window.show_result_log))
    window._responsive_control_rows.append(result_row)
    layout.addWidget(result_row)

    window._production_footer_widgets = [
        window.activity_detail,
        window.cancel, window.probe_button, window.start, result_label,
        window.open_output, window.open_probe_button, window.show_result_log,
    ]
    # At 800x600 and 200% zoom, production actions stay keyboard- and scroll-reachable.
    footer_scroll = QScrollArea()
    footer_scroll.setObjectName("actionFooterScroll")
    footer_scroll.setWidgetResizable(True)
    footer_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    footer_scroll.setMinimumHeight(70)
    footer_scroll.setMaximumHeight(210)
    footer_scroll.setWidget(footer)
    window.action_footer_scroll = footer_scroll
    outer.addWidget(footer_scroll)
