from __future__ import annotations

import re
from pathlib import Path

from PySide6.QtCore import QEvent, QObject, QTimer, Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from .config import DEFAULT_CONFIG, load_config, save_config
from .media_library import SORT_KEYS, sort_paths
from .qt_media_import_dialog import MediaImportDialog
from .qt_media_list import DropList
from .qt_phase2_components import PreviewPanel
from .qt_ui import VideoBatchQtWindow
AREA_KEYS = ("start", "media", "preview", "modes", "production", "help")
AREA_LABELS = {
    "start": "Übersicht",
    "media": "Dateien",
    "preview": "Vorschau / Diashow",
    "modes": "Ausgabe / Modi",
    "production": "Produktion",
    "help": "Projekt / Hilfe",
}
ROUTE_TO_AREA = {
    "dashboard": "start",
    "media": "media",
    "preview": "preview",
    "slideshow": "preview",
    "effects": "modes",
    "queue": "production",
    "project": "help",
    "diagnostics": "help",
}
ACTIVE_TAB_TO_ROUTE = {
    0: "dashboard",
    1: "media",
    2: "preview",
    3: "effects",
    4: "queue",
    5: "diagnostics",
}
ROUTE_TO_ACTIVE_TAB = {route: tab for tab, route in ACTIVE_TAB_TO_ROUTE.items()}
ROUTE_TO_ACTIVE_TAB.update({"slideshow": 2, "project": 0})

# Native DropList and PreviewPanel methods now own their UI lifecycle.
# Retain the selection/sorting services below for existing project contracts.

_QUICK_SORT_KEYS = {
    "name": "name_asc",
    "modified": "modified_new",
    "size": "size_desc",
}


def _config(window: object | None = None) -> dict[str, object]:
    current = getattr(window, "_parity_config", None) if window is not None else None
    return dict(current) if isinstance(current, dict) else load_config()


def _save_config(window: object | None, **changes: object) -> None:
    cfg = _config(window)
    cfg.update(changes)
    save_config(cfg)
    if window is not None:
        window._parity_config = cfg


def _production_paths(widget: DropList) -> list[Path]:
    return widget.production_paths()


def _visual_paths(widget: DropList) -> list[Path]:
    result: list[Path] = []
    for row in range(widget.count()):
        item = widget.item(row)
        raw = item.data(Qt.ItemDataRole.UserRole)
        if raw:
            result.append(Path(str(raw)))
    return result


def _render_drop_view(widget: DropList) -> None:
    # Service entry point kept for existing project and view callbacks.
    widget.render_view()


class _PreviewFullscreenDialog(QDialog):
    def __init__(self, source: PreviewPanel) -> None:
        super().__init__(source)
        self.setWindowTitle("VideoBatch · Vollbildvorschau")
        self.setModal(True)
        self._pixmap = source._pixmap
        self.resize(1200, 800)

        layout = QVBoxLayout(self)
        controls = QHBoxLayout()
        controls.addWidget(QLabel("Zoom"))
        self.zoom = QSpinBox()
        self.zoom.setRange(25, 800)
        self.zoom.setSuffix(" %")
        self.zoom.setSingleStep(25)
        self.zoom.setValue(int(getattr(source, "_parity_zoom", 100)))
        controls.addWidget(self.zoom)
        fit = QPushButton("Einpassen")
        close = QPushButton("Schließen")
        controls.addWidget(fit)
        controls.addStretch()
        controls.addWidget(close)
        layout.addLayout(controls)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(False)
        self.scroll.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image = QLabel()
        self.image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.scroll.setWidget(self.image)
        layout.addWidget(self.scroll, 1)

        self.zoom.valueChanged.connect(self._render)
        fit.clicked.connect(self._fit)
        close.clicked.connect(self.accept)
        self._fit()

    def _fit(self) -> None:
        if self._pixmap is None or self._pixmap.isNull():
            self.image.setText("Keine Bildvorschau verfügbar.")
            return
        viewport = self.scroll.viewport().size()
        target = self._pixmap.scaled(
            max(64, viewport.width() - 12),
            max(64, viewport.height() - 12),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.image.setPixmap(target)
        self.image.resize(target.size())

    def _render(self) -> None:
        if self._pixmap is None or self._pixmap.isNull():
            return
        factor = max(0.25, min(8.0, self.zoom.value() / 100.0))
        target = self._pixmap.scaled(
            max(1, round(self._pixmap.width() * factor)),
            max(1, round(self._pixmap.height() * factor)),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.image.setPixmap(target)
        self.image.resize(target.size())


def _preview_save_zoom(panel: PreviewPanel) -> None:
    window = panel.window()
    if window is not None and hasattr(window, "_parity_config"):
        _save_config(window, preview_zoom=int(panel._parity_zoom))


# Zoom/fit/fullscreen are native PreviewPanel methods, not class patches.


def _remember_directory(window: object, key: str, selected: list[Path]) -> None:
    if not selected:
        return
    _save_config(window, **{key: str(Path(selected[0]).expanduser().parent)})


def _initial_directory(window: object, key: str, fallback: Path) -> Path:
    cfg = _config(window)
    candidate = Path(str(cfg.get(key, fallback) or fallback)).expanduser()
    return candidate if candidate.is_dir() else fallback


def _browse(window: object, *, audio: bool) -> None:
    key = "last_audio_dir" if audio else "last_media_dir"
    fallback = Path.home() / ("Music" if audio else "Pictures")
    dialog = MediaImportDialog(
        window,
        audio=audio,
        initial_dir=_initial_directory(window, key, fallback),
        modal=True,
    )
    paths = list(dialog.wait())
    if not paths:
        return
    (window.audio if audio else window.media).add_paths(paths)
    _remember_directory(window, key, paths)


def _select_combo_data(combo: QComboBox, value: object) -> None:
    index = combo.findData(str(value))
    if index >= 0:
        combo.setCurrentIndex(index)


def _sort_changed(window: object, *, audio: bool) -> None:
    combo = window.parity_audio_sort if audio else window.parity_media_sort
    widget = window.audio if audio else window.media
    key = str(combo.currentData() or "import")
    widget._parity_view_sort = key
    _render_drop_view(widget)
    _save_config(window, **{("audio_sort" if audio else "media_sort"): key})
    if hasattr(window, "_project_dirty"):
        window._project_dirty = True


def _apply_view_order(window: object, *, audio: bool) -> None:
    widget = window.audio if audio else window.media
    displayed = _visual_paths(widget)
    if not displayed:
        return
    widget._parity_production_paths = displayed
    widget._parity_view_sort = "import"
    combo = window.parity_audio_sort if audio else window.parity_media_sort
    _select_combo_data(combo, "import")
    _render_drop_view(widget)
    _save_config(window, **{("audio_sort" if audio else "media_sort"): "import"})
    if hasattr(window, "_project_dirty"):
        window._project_dirty = True
    window._refresh()
    window.next_step.setText(
        ("Audio-" if audio else "Medien-")
        + "Ansicht wurde ausdrücklich als neue Produktionsreihenfolge übernommen."
    )


def _area_roots(window: object) -> dict[str, list[QWidget]]:
    roots: dict[str, list[QWidget]] = {
        "start": [window.centralWidget()],
        "media": [window.audio, window.media],
        "preview": [window.preview_panel, window.slideshow],
        "modes": [window.mode, window.parity_tabs.widget(0)],
        "production": [window.table],
        "help": [window.project_panel, window.diagnostics_panel, window.parity_tabs.widget(3)],
    }
    return roots


def _apply_area_zooms(window: object) -> None:
    base = float(
        getattr(window, "_parity_completion_global_font_size", QApplication.instance().font().pointSizeF())
        or 10.0
    )
    roots = _area_roots(window)
    window._parity_area_roots = roots
    for area in AREA_KEYS:
        percent = int(window._parity_area_zoom.get(area, 100))
        point = max(7.0, min(28.0, base * percent / 100.0))
        font = QFont(QApplication.instance().font())
        font.setPointSizeF(point)
        for root in roots.get(area, []):
            if root is not None:
                root.setFont(font)


def _refresh_area_zoom_base(window: object) -> None:
    app = QApplication.instance()
    if app is None:
        return
    window._parity_completion_global_font_size = max(7.0, app.font().pointSizeF())
    _apply_area_zooms(window)


def _set_area_zoom(window: object, area: str, value: int) -> None:
    if area not in AREA_KEYS:
        return
    window._parity_area_zoom[area] = max(70, min(180, int(value)))
    if hasattr(window, "parity_area_zoom_value"):
        window.parity_area_zoom_value.blockSignals(True)
        window.parity_area_zoom_value.setValue(window._parity_area_zoom[area])
        window.parity_area_zoom_value.blockSignals(False)
    _apply_area_zooms(window)
    _save_config(window, area_zoom=dict(window._parity_area_zoom))


def _selected_area_changed(window: object) -> None:
    area = str(window.parity_area_zoom_area.currentData() or "start")
    window.parity_area_zoom_value.blockSignals(True)
    window.parity_area_zoom_value.setValue(int(window._parity_area_zoom.get(area, 100)))
    window.parity_area_zoom_value.blockSignals(False)


class _AreaZoomFilter(QObject):
    def __init__(self, window: object) -> None:
        super().__init__(window)
        self.window = window

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if event.type() != QEvent.Type.Wheel:
            return False
        if not (event.modifiers() & Qt.KeyboardModifier.ControlModifier):
            return False
        area = self._area_for(watched)
        if area is None:
            return False
        delta = 10 if event.angleDelta().y() > 0 else -10
        _set_area_zoom(
            self.window,
            area,
            int(self.window._parity_area_zoom.get(area, 100)) + delta,
        )
        return True

    def _area_for(self, watched: QObject) -> str | None:
        roots = getattr(self.window, "_parity_area_roots", {})
        current: QObject | None = watched
        while current is not None:
            for area in ("media", "preview", "modes", "production", "help", "start"):
                if current in roots.get(area, []):
                    return area
            current = current.parent()
        return ROUTE_TO_AREA.get(getattr(self.window, "_parity_active_workspace", "dashboard"))


def _build_view_tab(window: object) -> QWidget:
    tab = QWidget()
    layout = QVBoxLayout(tab)

    intro = QLabel(
        "Sortieren verändert nur die Ansicht. Erst „als Produktionsreihenfolge übernehmen“ "
        "ändert die Reihenfolge der späteren Aufträge."
    )
    intro.setWordWrap(True)
    intro.setObjectName("subtitle")
    layout.addWidget(intro)

    cfg = _config(window)
    choices = [(label, key) for key, label in SORT_KEYS.items()]
    for audio, title in ((True, "Audio"), (False, "Bilder / Videos")):
        card = QFrame()
        card.setObjectName("card")
        row = QHBoxLayout(card)
        row.addWidget(QLabel(title + " · Ansicht"))
        combo = QComboBox()
        for label, key in choices:
            combo.addItem(label, key)
        key = "audio_sort" if audio else "media_sort"
        _select_combo_data(combo, cfg.get(key, "import"))
        apply_button = QPushButton("Ansicht als Produktionsreihenfolge übernehmen")
        row.addWidget(combo, 1)
        row.addWidget(apply_button)
        layout.addWidget(card)
        if audio:
            window.parity_audio_sort = combo
        else:
            window.parity_media_sort = combo
        combo.currentIndexChanged.connect(
            lambda _index, selected_audio=audio: _sort_changed(window, audio=selected_audio)
        )
        apply_button.clicked.connect(
            lambda _checked=False, selected_audio=audio: _apply_view_order(window, audio=selected_audio)
        )

    view = QFrame()
    view.setObjectName("card")
    view_layout = QHBoxLayout(view)
    view_layout.addWidget(QLabel("Bereichszoom"))
    window.parity_area_zoom_area = QComboBox()
    for key in AREA_KEYS:
        window.parity_area_zoom_area.addItem(AREA_LABELS[key], key)
    window.parity_area_zoom_value = QSpinBox()
    window.parity_area_zoom_value.setRange(70, 180)
    window.parity_area_zoom_value.setSingleStep(10)
    window.parity_area_zoom_value.setSuffix(" %")
    reset = QPushButton("Alle Bereiche 100 %")
    view_layout.addWidget(window.parity_area_zoom_area)
    view_layout.addWidget(window.parity_area_zoom_value)
    view_layout.addWidget(reset)
    view_layout.addStretch()
    layout.addWidget(view)

    hint = QLabel(
        "Tipp: Strg + Mausrad über einem Bereich ändert nur dessen Zoom. "
        "Die globale Schriftgröße in „Einstellungen“ bleibt davon getrennt."
    )
    hint.setObjectName("subtitle")
    hint.setWordWrap(True)
    layout.addWidget(hint)
    layout.addStretch()

    window.parity_area_zoom_area.currentIndexChanged.connect(
        lambda *_: _selected_area_changed(window)
    )
    window.parity_area_zoom_value.valueChanged.connect(
        lambda value: _set_area_zoom(
            window,
            str(window.parity_area_zoom_area.currentData() or "start"),
            value,
        )
    )
    reset.clicked.connect(
        lambda: [_set_area_zoom(window, area, 100) for area in AREA_KEYS]
    )
    _selected_area_changed(window)
    return tab


def _restore_window_geometry(window: object) -> None:
    cfg = _config(window)
    geometry = getattr(window, "_parity_boot_window_geometry", cfg.get("window_geometry", ""))
    match = re.fullmatch(r"\s*(\d{3,5})x(\d{3,5})\s*", str(geometry))
    if not match:
        return
    width, height = int(match.group(1)), int(match.group(2))
    screen = QApplication.primaryScreen()
    if screen is not None:
        available = screen.availableGeometry()
        width = min(width, max(window.minimumWidth(), available.width()))
        height = min(height, max(window.minimumHeight(), available.height()))
    window.resize(max(window.minimumWidth(), width), max(window.minimumHeight(), height))


def _active_workspace_from_state(window: object, state: dict[str, object]) -> str:
    meta = state.get("meta", {}) if isinstance(state, dict) else {}
    if isinstance(meta, dict):
        route = str(meta.get("qt_active_workspace", "") or "")
        if route in getattr(window.workspace_navigation, "buttons", {}):
            return route
    try:
        tab = int(_config(window).get("active_tab", 0) or 0)
    except (TypeError, ValueError):
        tab = 0
    return ACTIVE_TAB_TO_ROUTE.get(tab, "dashboard")


def _wrap_project_and_route(window: object) -> None:
    if getattr(window, "_parity_completion_wrapped", False):
        return
    original_collect = window._collect_project_state
    original_apply = window._apply_project_state
    original_route = window._route_workspace

    def collect() -> dict[str, object]:
        state = dict(original_collect())
        state["audio_sort"] = str(getattr(window.audio, "_parity_view_sort", "import"))
        state["media_sort"] = str(getattr(window.media, "_parity_view_sort", "import"))
        meta = dict(state.get("meta", {}) if isinstance(state.get("meta"), dict) else {})
        meta["qt_active_workspace"] = str(
            getattr(window, "_parity_active_workspace", "dashboard")
        )
        state["meta"] = meta
        return state

    def apply(state: dict[str, object]) -> None:
        original_apply(state)
        audio_sort = str(state.get("audio_sort", _config(window).get("audio_sort", "import")))
        media_sort = str(state.get("media_sort", _config(window).get("media_sort", "import")))
        window.audio._parity_view_sort = audio_sort
        window.media._parity_view_sort = media_sort
        _select_combo_data(window.parity_audio_sort, audio_sort)
        _select_combo_data(window.parity_media_sort, media_sort)
        _render_drop_view(window.audio)
        _render_drop_view(window.media)
        route = _active_workspace_from_state(window, state)
        window._parity_active_workspace = route
        QTimer.singleShot(
            0,
            lambda selected=route: (
                window._route_workspace(selected)
                if selected in window.workspace_navigation.buttons
                else None
            ),
        )

    def route(route_name: str) -> None:
        original_route(route_name)
        window._parity_active_workspace = route_name
        _save_config(window, active_tab=ROUTE_TO_ACTIVE_TAB.get(route_name, 0))
        if hasattr(window, "_project_state"):
            meta = dict(
                window._project_state.get("meta", {})
                if isinstance(window._project_state.get("meta"), dict)
                else {}
            )
            meta["qt_active_workspace"] = route_name
            window._project_state["meta"] = meta
            window._project_dirty = True

    window._collect_project_state = collect
    window._apply_project_state = apply
    window._route_workspace = route
    window._parity_completion_wrapped = True


def _finish_completion(window: object) -> None:
    if getattr(window, "_parity_completion_ready", False):
        return
    if not getattr(window, "_parity_ready", False):
        QTimer.singleShot(10, lambda: _finish_completion(window))
        return

    cfg = _config(window)
    window._parity_area_zoom = dict(cfg.get("area_zoom", DEFAULT_CONFIG["area_zoom"]))
    for key in AREA_KEYS:
        try:
            window._parity_area_zoom[key] = max(
                70, min(180, int(window._parity_area_zoom.get(key, 100)))
            )
        except (TypeError, ValueError):
            window._parity_area_zoom[key] = 100

    view_tab = _build_view_tab(window)
    window.parity_tabs.addTab(view_tab, "Medien & Ansicht")
    window.parity_view_tab = view_tab

    window.audio._parity_view_sort = str(cfg.get("audio_sort", "import"))
    window.media._parity_view_sort = str(cfg.get("media_sort", "import"))
    if hasattr(window, "sort_hint"):
        window.sort_hint.setText(
            "Sortieren ändert nur die Ansicht. "
            "Die Produktionsreihenfolge wird erst nach ausdrücklicher Übernahme geändert."
        )
    _render_drop_view(window.audio)
    _render_drop_view(window.media)

    if hasattr(window, "preview_panel"):
        window.preview_panel.set_parity_zoom(int(cfg.get("preview_zoom", 100)), persist=False)

    _restore_window_geometry(window)
    _save_config(window, window_geometry=f"{window.width()}x{window.height()}")
    _wrap_project_and_route(window)
    _refresh_area_zoom_base(window)
    window.parity_font_scale.valueChanged.connect(
        lambda *_: _refresh_area_zoom_base(window)
    )

    window._parity_zoom_filter = _AreaZoomFilter(window)
    QApplication.instance().installEventFilter(window._parity_zoom_filter)

    route = _active_workspace_from_state(window, dict(getattr(window, "_project_state", {})))
    window._parity_active_workspace = route
    if route in window.workspace_navigation.buttons:
        window._route_workspace(route)

    window._parity_completion_ready = True
    window._write_log(
        "Tk-Parität abgeschlossen: Sortierung mit expliziter Produktionsreihenfolge · "
        "letzte Medienordner · Vorschau-Zoom/Vollbild · Fenstergröße · Bereichszoom · "
        "letzter Arbeitsbereich."
    )


def persist_parity_on_close(window: object) -> None:
    """Persist Qt parity view preferences through the explicit Phase-3 close path."""
    if not getattr(window, "_parity_completion_ready", False):
        return
    _save_config(
        window,
        window_geometry=f"{window.width()}x{window.height()}",
        preview_zoom=int(getattr(window.preview_panel, "_parity_zoom", 100)),
        area_zoom=dict(getattr(window, "_parity_area_zoom", DEFAULT_CONFIG["area_zoom"])),
        audio_sort=str(getattr(window.audio, "_parity_view_sort", "import")),
        media_sort=str(getattr(window.media, "_parity_view_sort", "import")),
        active_tab=ROUTE_TO_ACTIVE_TAB.get(
            getattr(window, "_parity_active_workspace", "dashboard"), 0
        ),
    )


def install_parity_completion() -> None:
    """Keep still-needed widget compatibility adapters; never patch Qt lifecycle."""
