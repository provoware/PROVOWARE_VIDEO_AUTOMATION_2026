from __future__ import annotations

from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
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

        steps = (
            ("1 · Dateien auswählen", "Audio und passende Bilder oder Videos hinzufügen.", "media"),
            ("2 · Ausgabe festlegen", "Zielordner und einen Schnellmodus prüfen.", "effects"),
            ("3 · Produktion öffnen", "Aufträge prüfen, starten und Fortschritt beobachten.", "queue"),
        )
        for label, description, route in steps:
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
            "Ampel: GRÜN = bereit · GELB = prüfen · ROT = Vorgang gestoppt.\n"
            "Bei ROT zuerst die Meldung lesen. Nicht mit sudo, chmod -R 777 oder "
            "rekursiven Besitzänderungen improvisieren. Originalmedien werden als Quellen gelesen."
        )
        safety.setObjectName("safeHint")
        safety.setWordWrap(True)
        layout.addWidget(safety)

        diagnose = QPushButton("Technische Diagnose öffnen")
        diagnose.setToolTip("Systemzustand lesen und vorhandene Schutzprüfungen anzeigen.")
        diagnose.setAccessibleDescription(
            "Öffnet die technische Diagnose. Es wird dadurch kein Render gestartet."
        )
        diagnose.clicked.connect(lambda _checked=False: self.routeRequested.emit("diagnostics"))
        layout.addWidget(diagnose)
        layout.addStretch()


def build_main_ui(window) -> None:
    root = QWidget()
    window.setCentralWidget(root)
    outer = QVBoxLayout(root)
    outer.setContentsMargins(18, 16, 18, 16)

    header = QHBoxLayout()
    brand = QVBoxLayout()
    title = QLabel("VideoBatch 2026")
    title.setObjectName("title")
    subtitle = QLabel("Kubuntu 26.04 · KDE Plasma · Wayland · Qt 6")
    subtitle.setObjectName("subtitle")
    brand.addWidget(title)
    brand.addWidget(subtitle)
    header.addLayout(brand)
    header.addStretch()
    header.addWidget(window.load_dashboard.frame, alignment=Qt.AlignmentFlag.AlignTop)
    window.status = QLabel("BEREIT")
    window.status.setObjectName("statusChip")
    window.status.setAccessibleName("Programmstatus")
    window.status.setAccessibleDescription("Zeigt, ob VideoBatch bereit ist, prüft oder angehalten wurde.")
    header.addWidget(window.status, alignment=Qt.AlignmentFlag.AlignTop)
    outer.addLayout(header)

    guide = QFrame()
    guide.setObjectName("workflowGuide")
    guide_row = QHBoxLayout(guide)
    guide_row.setContentsMargins(12, 8, 12, 8)
    guide_row.setSpacing(8)
    guide_title = QLabel("Einfacher Ablauf")
    guide_title.setObjectName("guideTitle")
    guide_row.addWidget(guide_title)
    window.step_files = QLabel("1 · Dateien")
    window.step_output = QLabel("2 · Ausgabe")
    window.step_start = QLabel("3 · Start")
    for step in (window.step_files, window.step_output, window.step_start):
        step.setObjectName("stepChip")
        step.setAccessibleDescription("Schritt im einfachen Drei-Schritt-Ablauf.")
        guide_row.addWidget(step)
    guide_row.addStretch()
    outer.addWidget(guide)

    kpis = QHBoxLayout()
    kpis.setSpacing(8)
    window.kpi_values = {}
    for key, label in (
        ("audio", "Audios"), ("media", "Medien"), ("jobs", "Aufträge"),
        ("done", "Fertig"), ("active", "Aktiv"),
    ):
        card, value = window._kpi(label)
        window.kpi_values[key] = value
        kpis.addWidget(card, 1)
    window.kpi_values["active"].setText("Nein")
    outer.addLayout(kpis)

    splitter = QSplitter(Qt.Orientation.Horizontal)
    splitter.setChildrenCollapsible(False)
    splitter.addWidget(window._sources_panel())
    splitter.addWidget(window._queue_panel())
    splitter.addWidget(window._settings_panel())
    splitter.setSizes([320, 700, 420])
    for index, stretch in enumerate((22, 48, 30)):
        splitter.setStretchFactor(index, stretch)
    outer.addWidget(splitter, 1)

    _build_footer(window, outer)


def _build_footer(window, outer: QVBoxLayout) -> None:
    footer = QFrame()
    footer.setObjectName("actionFooter")
    footer_layout = QVBoxLayout(footer)
    footer_layout.setContentsMargins(12, 9, 12, 9)
    footer_layout.setSpacing(7)
    window.next_step = QLabel("Nächster Schritt: 1 · Dateien auswählen")
    window.next_step.setObjectName("nextStep")
    window.next_step.setAccessibleName("Nächster Arbeitsschritt")
    window.next_step.setWordWrap(True)
    footer_layout.addWidget(window.next_step)

    window.activity_detail = QLabel("Keine Verarbeitung aktiv · bereit für neue Aufträge")
    window.activity_detail.setObjectName("subtitle")
    window.activity_detail.setAccessibleName("Aktueller Arbeitszustand")
    window.activity_detail.setWordWrap(True)
    footer_layout.addWidget(window.activity_detail)
    progress_row = QHBoxLayout()
    progress_row.addWidget(QLabel("Gesamt"))
    window.progress = QProgressBar()
    window.progress.setRange(0, 100)
    window.progress.setAccessibleName("Gesamtfortschritt")
    window.progress.setAccessibleDescription("Fortschritt aller Aufträge zusammen.")
    window.progress.setFormat("Bereit · %p %")
    progress_row.addWidget(window.progress, 1)
    footer_layout.addLayout(progress_row)

    action_row = QHBoxLayout()
    action_row.addWidget(QLabel("Auftrag"))
    window.job_progress = QProgressBar()
    window.job_progress.setObjectName("jobProgress")
    window.job_progress.setRange(0, 100)
    window.job_progress.setAccessibleName("Fortschritt des aktuellen Auftrags")
    window.job_progress.setAccessibleDescription("Fortschritt des gerade verarbeiteten Videos.")
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
    footer_layout.addLayout(action_row)

    result_row = QHBoxLayout()
    result_row.addWidget(QLabel("Nach Abschluss"))
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
    footer_layout.addLayout(result_row)
    outer.addWidget(footer)
