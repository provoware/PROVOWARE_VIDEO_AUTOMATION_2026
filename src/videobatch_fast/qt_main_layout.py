from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import QApplication, QComboBox, QDoubleSpinBox, QSlider, QFrame, QHBoxLayout, QGridLayout, QLabel, QVBoxLayout, QWidget, QLineEdit, QPushButton, QTabBar, QScrollArea, QMenu

from .qt_theme import SCALE_LEVELS, scaled_style
from .qt_adaptive_settings import ResponsiveSettingsPanel
from .dashboard_settings import RESOLUTION_LABELS, QUALITY_LABELS, EFFECT_LABELS
from .effects import TRANSITIONS
from .qt_workspace_layout import build_footer, build_workflow_stack, set_workflow_route


from . import qt_layout_sections


def build_main_ui(window) -> None:
    root = QWidget()
    root.setObjectName("desktopSurface")
    window.setCentralWidget(root)
    outer = QVBoxLayout(root)
    outer.setContentsMargins(10, 8, 10, 8)
    outer.setSpacing(5)

    # Header is arranged in two rows: text no longer fights load/zoom for one line.
    header = QGridLayout()
    header.setSpacing(5)
    header.setColumnStretch(0, 1)
    brand = QVBoxLayout()
    brand.setSpacing(0)
    title = QLabel("VideoBatch 2026")
    title.setObjectName("title")
    subtitle = QLabel("Kubuntu 26.04 · KDE Plasma · Wayland · Qt 6")
    subtitle.setObjectName("subtitle")
    subtitle.setWordWrap(True)
    brand.addWidget(title)
    brand.addWidget(subtitle)
    header.addLayout(brand, 0, 0, 1, 4)

    window.status = QLabel("BEREIT")
    window.status.setObjectName("statusChip")
    window.status.setAccessibleDescription(
        "Aktueller Programmstatus. Der sichtbare Text nennt den momentanen Zustand."
    )
    header.addWidget(window.status, 1, 0, alignment=Qt.AlignmentFlag.AlignLeft)

    view_label = QLabel("Schrift")
    window.view_scale = QComboBox()
    view_label.setBuddy(window.view_scale)
    window.view_scale.setAccessibleName("Schrift- und Ansichtsgröße")
    window.view_scale.setAccessibleDescription(
        "Verändert die Schrift und Bedienelemente zwischen 80 und 200 Prozent."
    )
    window.view_scale.setToolTip(
        "Schriftgröße · Strg+Alt+Pfeil hoch/runter · Strg+Alt+0 setzt auf 110 % zurück"
    )
    for value in SCALE_LEVELS:
        window.view_scale.addItem(f"{value} %", value)
    window.view_scale.setCurrentIndex(window.view_scale.findData(110))
    header.addWidget(view_label, 1, 2)
    header.addWidget(window.view_scale, 1, 3)

    # Große Schrift: Alle Menüs bleiben über eine einzige Schaltfläche erreichbar.
    window.compact_menu = QPushButton("Menü")
    window.compact_menu.setAccessibleName("Alle Programmmenüs öffnen")
    def open_compact_menu() -> None:
        menu = QMenu(window)
        for action in window.menuBar().actions():
            menu.addAction(action)
        menu.exec(window.compact_menu.mapToGlobal(QPoint(0, window.compact_menu.height())))
        menu.deleteLater()
    window.compact_menu.clicked.connect(open_compact_menu)
    header.addWidget(window.compact_menu, 1, 1)
    window.compact_menu.hide()

    dashboard = QFrame()
    dashboard.setObjectName("compactStatusDashboard")
    window._compact_header_dashboard = dashboard
    dashboard_row = QVBoxLayout(dashboard)
    dashboard_row.setContentsMargins(4, 2, 4, 2)
    dashboard_row.setSpacing(8)
    dashboard_row.addWidget(window.load_dashboard.frame)

    # The existing two progress objects are created in build_footer().
    # Their compact dashboard container is placed here, not in the tall footer.
    window.progress_dashboard = QWidget()
    window.progress_dashboard.setObjectName("progressDashboard")
    window.progress_dashboard_layout = QGridLayout(window.progress_dashboard)
    window.progress_dashboard_layout.setContentsMargins(2, 1, 2, 1)
    window.progress_dashboard_layout.setHorizontalSpacing(5)
    window.progress_dashboard_layout.setVerticalSpacing(2)
    window.progress_dashboard_layout.setColumnStretch(1, 1)
    dashboard_row.addWidget(window.progress_dashboard)
    header.addWidget(dashboard, 2, 0, 1, 4)
    outer.addLayout(header)

    qt_layout_sections.build_settings(window)

    # Permanent, novice-readable workspace navigation.
    tabs = QTabBar()
    tabs.setObjectName("mainNavigation")
    tabs.setExpanding(True)
    tabs.setAccessibleName("Arbeitsbereiche")
    for name in ("1 · Dateien", "2 · Ausgabe", "3 · Produktion", "Hilfe / Werkzeuge"):
        tabs.addTab(name)
    window.main_tabs = tabs
    routes = ("media", "effects", "queue", "dashboard")
    def navigate(index: int) -> None:
        route = routes[index]
        handler = getattr(window, "_route_workspace", None)
        if callable(handler):
            handler(route)
        else:
            set_workflow_route(window, route)
    tabs.currentChanged.connect(navigate)
    outer.addWidget(tabs)

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

    window._responsive_control_rows = []
    outer.addWidget(build_workflow_stack(window), 1)

    window.audio.setAccessibleName("Audiodateien")
    window.media.setAccessibleName("Bilder und Videos")
    window.table.setAccessibleName("Automatische Auftragsliste")
    window.table.setAlternatingRowColors(True)
    window.output.setAccessibleName("Ausgabeordner")
    window.verification.setAccessibleName("Kontrolle nach der Erstellung")

    build_footer(window, outer)
    set_workflow_route(window, "media")

    def apply_scale() -> None:
        qt_layout_sections.apply_scale(window, title, subtitle, dashboard)

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
    reset.activated.connect(lambda: window.view_scale.setCurrentIndex(window.view_scale.findData(110)))
    window._scale_shortcuts.append(reset)
    apply_scale()

    # Bei großer Schrift müssen auch zunächst unterhalb des Fensters liegende
    # Bedienelemente per Tastatur erreichbar und sichtbar werden. Insbesondere
    # mehrere ineinander liegende QScrollAreas werden von Qt nicht immer
    # automatisch gemeinsam zum gerade fokussierten Knopf nachgeführt.
    app = QApplication.instance()
    if app is not None:
        def reveal_keyboard_focus(_previous, focused) -> None:
            if focused is None or not window.isAncestorOf(focused):
                return
            ancestor = focused.parentWidget()
            while ancestor is not None:
                if isinstance(ancestor, QScrollArea):
                    ancestor.ensureWidgetVisible(focused, 8, 8)
                if ancestor is window:
                    break
                ancestor = ancestor.parentWidget()

        app.focusChanged.connect(reveal_keyboard_focus)
        window._focus_visibility_handler = reveal_keyboard_focus

        def disconnect_focus_handler(*_ignored) -> None:
            try:
                app.focusChanged.disconnect(reveal_keyboard_focus)
            except (RuntimeError, TypeError):
                pass

        window.destroyed.connect(disconnect_focus_handler)
