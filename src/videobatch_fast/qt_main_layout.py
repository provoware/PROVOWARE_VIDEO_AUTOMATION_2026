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


def build_main_ui(window) -> None:
    root = QWidget()
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

    # Responsive settings follow the same 120×80 reference logic as the lists.
    # Keep every existing control object and its signal handlers unchanged.
    window.settings_grid = ResponsiveSettingsPanel()
    settings_view = QScrollArea()
    settings_view.setObjectName("adaptiveSettingScroll")
    settings_view.setWidgetResizable(True)
    settings_view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    settings_view.setMinimumHeight(92)
    settings_view.setMaximumHeight(140)
    settings_view.setWidget(window.settings_grid)
    window.settings_view = settings_view

    window.resolution = QComboBox()
    for value, label in RESOLUTION_LABELS.items():
        window.resolution.addItem(label, value)
    window.quality = QComboBox()
    for value, label in QUALITY_LABELS.items():
        window.quality.addItem(label, value)
    window.effect = QComboBox()
    for value, label in EFFECT_LABELS.items():
        window.effect.addItem(label, value)
    window.output = QLineEdit()
    window.output_button = QPushButton("Wählen …")
    window.output_button.setObjectName("secondary")
    window.output.setAccessibleName("Ordner für fertige Videos")
    window.output.setToolTip("In diesem Ordner speichert VideoBatch die fertigen Videos.")
    window.resolution.setToolTip("Bildgröße: Full HD ist für viele Videos ein guter Standard.")
    window.quality.setToolTip("Ausgewogen: guter Kompromiss zwischen Dauer und Dateigröße.")
    window.effect.setToolTip("Ändert nur den Bildeffekt. Überblendungen sind eine erweiterte Einstellung.")

    state = window.dashboard_settings
    for widget, key in ((window.resolution, state.resolution),
                        (window.quality, state.quality), (window.effect, state.effect)):
        index = widget.findData(key)
        if index >= 0:
            widget.setCurrentIndex(index)
    window.output.setText(str(state.output_dir))

    output_box = QWidget()
    output_row = QHBoxLayout(output_box)
    output_row.setContentsMargins(0, 0, 0, 0)
    output_row.setSpacing(6)
    output_row.addWidget(window.output, 1)
    output_row.addWidget(window.output_button)

    window.settings_grid.add_field("Auflösung", window.resolution)
    window.settings_grid.add_field("Qualität", window.quality)
    window.settings_grid.add_field("Bildeffekt", window.effect)
    window.settings_grid.add_field("Ausgabeordner", output_box, buddy=window.output)

    # The original compact everyday controls remain; one additional row
    # exposes real rendering values without hiding them in legacy dialogs.
    window.effect_intensity = QSlider(Qt.Orientation.Horizontal)
    window.effect_intensity.setRange(0, 100)
    window.effect_intensity.setValue(state.effect_intensity)
    window.effect_intensity.setAccessibleName("Effektstärke von 0 bis 100 Prozent")
    window.effect_intensity.setToolTip("100 % = bisheriger Effekt, 0 % = kein Effekt.")
    window.intensity_value = QLabel(f"{state.effect_intensity} %")
    strength_box = QWidget()
    strength_row = QHBoxLayout(strength_box)
    strength_row.setContentsMargins(0, 0, 0, 0)
    strength_row.addWidget(window.effect_intensity, 1)
    strength_row.addWidget(window.intensity_value)
    window.settings_grid.add_field("Effektstärke", strength_box, buddy=window.effect_intensity)

    window.transition = QComboBox()
    for key, transition in TRANSITIONS.items():
        window.transition.addItem(transition.label, key)
    idx = window.transition.findData(state.transition)
    window.transition.setCurrentIndex(max(0, idx))
    window.transition.setAccessibleName("Videoblende: Ein- und Ausblendung")
    window.fade_seconds = QDoubleSpinBox()
    window.fade_seconds.setRange(0.0, 5.0)
    window.fade_seconds.setSingleStep(0.1)
    window.fade_seconds.setDecimals(1)
    window.fade_seconds.setSuffix(" s")
    window.fade_seconds.setValue(state.transition_duration)
    window.fade_seconds.setAccessibleName("Videoblenddauer in Sekunden")
    fade_box = QWidget()
    fade_row = QHBoxLayout(fade_box)
    fade_row.setContentsMargins(0, 0, 0, 0)
    fade_row.addWidget(window.transition, 1)
    fade_row.addWidget(window.fade_seconds)
    window.settings_grid.add_field("Videoblende", fade_box, buddy=window.transition)
    # Einstellungen stehen in Schritt 2, nicht auf jeder Hauptseite.

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
        value = int(window.view_scale.currentData() or 100)
        app = QApplication.instance()
        if app is not None:
            app.setStyleSheet(scaled_style(value))
        window.table.verticalHeader().setDefaultSectionSize(round(38 * value / 100))
        compact = value >= 150
        window.menuBar().setVisible(not compact)
        window.compact_menu.setVisible(compact)
        window.main_tabs.setTabText(3, "Hilfe" if compact else "Hilfe / Werkzeuge")
        subtitle.setVisible(not compact)
        window.load_dashboard.frame.setVisible(not compact)
        route = getattr(window, "_active_workflow_route", "media")
        dashboard.setVisible(not compact or route == "queue")
        window.settings_grid.set_zoom_percent(value)
        window.source_columns.set_zoom_percent(value)
        for control_row in window._responsive_control_rows:
            control_row.set_zoom_percent(value)

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
