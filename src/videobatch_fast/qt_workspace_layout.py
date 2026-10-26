from __future__ import annotations

from PySide6.QtCore import Qt, QTimer, Signal
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
            ("2 · Videoeinstellungen", "Auflösung, Qualität, Bildeffekt und Zielordner in Schritt 2 ändern.", "effects"),
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
    from .qt_workflow_footer import _overview_page as build

    return build(window)


def build_workflow_stack(window) -> QStackedWidget:
    stack = QStackedWidget()
    stack.setObjectName("workflowPages")
    pages = {
        "dashboard": _overview_page(window),
        "media": window._sources_panel(),
        "effects": window._settings_panel(),
        "queue": window._queue_panel(),
    }
    overview_scroll = QScrollArea()
    overview_scroll.setObjectName("overviewPageScroll")
    overview_scroll.setWidgetResizable(True)
    overview_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    overview_scroll.setWidget(pages["dashboard"])
    pages["dashboard"] = overview_scroll
    # Die Alltags-Einstellungen gehören in die Ausgabe-Seite.
    # Eine äußere vertikale Rollebene schützt alle erweiterten Bedienelemente
    # bei 800×600 und 200 % vor dem Abschneiden.
    effects_page = pages["effects"]
    effects_page.layout().insertWidget(0, window.settings_view)
    output_scroll = QScrollArea()
    output_scroll.setObjectName("outputPageScroll")
    output_scroll.setWidgetResizable(True)
    output_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    output_scroll.setWidget(effects_page)
    pages["effects"] = output_scroll
    queue_page = pages["queue"]
    queue_scroll = QScrollArea()
    queue_scroll.setObjectName("productionPageScroll")
    queue_scroll.setWidgetResizable(True)
    queue_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    queue_scroll.setWidget(queue_page)
    pages["queue"] = queue_scroll
    for page in pages.values():
        stack.addWidget(page)
    window.workflow_stack = stack
    window._workflow_pages = pages
    return stack


def set_workflow_route(window, route: str) -> None:
    pages = getattr(window, "_workflow_pages", {})
    previous = getattr(window, "_active_workflow_route", None)
    page_key = route if route in pages else "dashboard"
    if page_key in pages:
        window.workflow_stack.setCurrentWidget(pages[page_key])
    window._active_workflow_route = route
    # New pages always open at their explanatory heading. A previous focus or
    # scroll position must not hide the first line at 175/200 % zoom.
    if route != previous:
        current_page = pages.get(page_key)
        if isinstance(current_page, QScrollArea):
            current_page.verticalScrollBar().setValue(0)
            QTimer.singleShot(
                0,
                lambda page=current_page: page.verticalScrollBar().setValue(0),
            )
        footer_scroll = getattr(window, "action_footer_scroll", None)
        if footer_scroll is not None:
            footer_scroll.verticalScrollBar().setValue(0)
    tabs = getattr(window, "main_tabs", None)
    positions = {"media": 0, "effects": 1, "queue": 2, "dashboard": 3}
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
    dashboard = getattr(window, "_compact_header_dashboard", None)
    zoom = getattr(window, "view_scale", None)
    if dashboard is not None and zoom is not None:
        dashboard.setVisible(int(zoom.currentData() or 110) < 150 or production)
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


def build_footer(window, outer) -> None:
    from .qt_workflow_footer import build_footer as build

    build(window, outer)
