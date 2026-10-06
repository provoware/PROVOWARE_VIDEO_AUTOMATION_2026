from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import QApplication, QComboBox, QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from .qt_theme import SCALE_LEVELS, scaled_style
from .qt_workspace_layout import build_footer, build_workflow_stack, set_workflow_route


def build_main_ui(window) -> None:
    root = QWidget()
    window.setCentralWidget(root)
    outer = QVBoxLayout(root)
    outer.setContentsMargins(18, 16, 18, 16)
    outer.setSpacing(8)

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
    window.workflow_guide = guide
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
    window._kpi_cards = []
    for key, label in (
        ("audio", "Audios"), ("media", "Medien"), ("jobs", "Aufträge"),
        ("done", "Fertig"), ("active", "Aktiv"),
    ):
        card, value = window._kpi(label)
        window.kpi_values[key] = value
        window._kpi_cards.append(card)
        kpis.addWidget(card, 1)
    window.kpi_values["active"].setText("Nein")
    outer.addLayout(kpis)

    outer.addWidget(build_workflow_stack(window), 1)

    window.audio.setAccessibleName("Audiodateien")
    window.media.setAccessibleName("Bilder und Videos")
    window.table.setAccessibleName("Automatische Auftragsliste")
    window.table.setAlternatingRowColors(True)
    window.output.setAccessibleName("Ausgabeordner")
    window.mode.setAccessibleName("Verarbeitungsmodus")
    window.verification.setAccessibleName("Kontrolle nach der Erstellung")

    build_footer(window, outer)
    set_workflow_route(window, "dashboard")

    def apply_scale() -> None:
        value = int(window.view_scale.currentData() or 100)
        app = QApplication.instance()
        if app is not None:
            app.setStyleSheet(scaled_style(value))
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
