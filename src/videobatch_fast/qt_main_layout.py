from __future__ import annotations

from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication, QComboBox, QFrame, QHBoxLayout, QLabel, QProgressBar, QPushButton,
    QScrollArea, QSplitter, QVBoxLayout, QWidget,
)

from .qt_desktop_actions import open_output_folder
from .qt_theme import SCALE_LEVELS, scaled_style


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
            "Status: ✓ BEREIT (grün) · ⚠ PRÜFEN (gelb) · ✕ GESTOPPT (rot).\n"
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
    window.status.setAccessibleDescription(
        "Aktueller Programmstatus. Der sichtbare Text nennt den momentanen Zustand."
    )
    header.addWidget(window.status, alignment=Qt.AlignmentFlag.AlignTop)
    view_label = QLabel("Ansicht")
    window.view_scale = QComboBox()
    view_label.setBuddy(window.view_scale)
    window.view_scale.setAccessibleName("Ansichtsgröße")
    window.view_scale.setAccessibleDescription("Vergrößert die gesamte Oberfläche von 100 bis 200 Prozent.")
    window.view_scale.setToolTip(
        "Ansichtsgröße · Strg+Alt+Pfeil hoch/runter · Strg+Alt+0 setzt auf 100 % zurück"
    )
    for value in SCALE_LEVELS:
        window.view_scale.addItem(f"{value} %", value)
    header.addWidget(view_label, alignment=Qt.AlignmentFlag.AlignTop)
    header.addWidget(window.view_scale, alignment=Qt.AlignmentFlag.AlignTop)
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
    workspace_scroll = QScrollArea()
    workspace_scroll.setObjectName("mainWorkspaceScroll")
    workspace_scroll.setWidgetResizable(True)
    workspace_scroll.setFrameShape(QFrame.Shape.NoFrame)
    workspace_scroll.setWidget(splitter)
    outer.addWidget(workspace_scroll, 1)

    window.audio.setAccessibleName("Audiodateien")
    window.media.setAccessibleName("Bilder und Videos")
    window.table.setAccessibleName("Automatische Auftragsliste")
    window.table.setAlternatingRowColors(True)
    window.output.setAccessibleName("Ausgabeordner")
    window.mode.setAccessibleName("Verarbeitungsmodus")
    window.verification.setAccessibleName("Kontrolle nach der Erstellung")

    def apply_scale() -> None:
        value = int(window.view_scale.currentData() or 100)
        app = QApplication.instance()
        if app is not None:
            app.setStyleSheet(scaled_style(value))
        splitter.setMinimumSize(round(930 * value / 100), round(360 * value / 100))
        window.table.verticalHeader().setDefaultSectionSize(round(38 * value / 100))

    window.view_scale.currentIndexChanged.connect(apply_scale)
    window._scale_shortcuts = []
    for key, step in (("Ctrl+Alt+Up", 1), ("Ctrl+Alt+Down", -1)):
        shortcut = QShortcut(QKeySequence(key), window)
        shortcut.activated.connect(
            lambda delta=step: window.view_scale.setCurrentIndex(
                max(0, min(window.view_scale.count() - 1, window.view_scale.currentIndex() + delta))
            )
        )
        window._scale_shortcuts.append(shortcut)
    reset = QShortcut(QKeySequence("Ctrl+Alt+0"), window)
    reset.activated.connect(lambda: window.view_scale.setCurrentIndex(0))
    window._scale_shortcuts.append(reset)
    apply_scale()

    _build_footer(window, outer)


def _build_footer(window, outer: QVBoxLayout) -> None:
    footer = QFrame()
    footer.setObjectName("actionFooter")
    footer_layout = QVBoxLayout(footer)
    footer_layout.setContentsMargins(12, 9, 12, 9)
    footer_layout.setSpacing(7)
    window.next_step = QLabel("Nächster Schritt: 1 · Dateien auswählen")
    window.next_step.setObjectName("nextStep")
    window.next_step.setAccessibleDescription(
        "Der sichtbare Text nennt den aktuell empfohlenen nächsten Arbeitsschritt."
    )
    window.next_step.setWordWrap(True)
    footer_layout.addWidget(window.next_step)

    window.activity_detail = QLabel("Keine Verarbeitung aktiv · bereit für neue Aufträge")
    window.activity_detail.setObjectName("subtitle")
    window.activity_detail.setAccessibleDescription(
        "Der sichtbare Text beschreibt den aktuellen Arbeitszustand."
    )
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
