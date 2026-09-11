from __future__ import annotations

import re
from pathlib import Path

from PySide6.QtCore import QEvent, QObject, QTimer, Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QFileDialog,
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
from .qt_phase2_components import PreviewPanel
from .qt_ui import DropList, VideoBatchQtWindow

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

_DROP_PATCHED = False
_PREVIEW_PATCHED = False
_PHASE2_PATCHED = False

_DROP_PATHS = DropList.paths
_DROP_CLEAR = DropList.clear


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
    paths = getattr(widget, "_parity_production_paths", None)
    if paths is None:
        paths = [Path(path) for path in _DROP_PATHS(widget)]
        widget._parity_production_paths = list(paths)
    return list(paths)


def _visual_paths(widget: DropList) -> list[Path]:
    result: list[Path] = []
    for row in range(widget.count()):
        item = widget.item(row)
        raw = item.data(Qt.ItemDataRole.UserRole)
        if raw:
            result.append(Path(str(raw)))
    return result


def _render_drop_view(widget: DropList) -> None:
    selected = {
        Path(str(item.data(Qt.ItemDataRole.UserRole)))
        for item in widget.selectedItems()
        if item.data(Qt.ItemDataRole.UserRole)
    }
    production = _production_paths(widget)
    key = str(getattr(widget, "_parity_view_sort", "import") or "import")
    displayed = sort_paths(production, key) if key != "import" else production
    widget.blockSignals(True)
    try:
        _DROP_CLEAR(widget)
        for path in displayed:
            item = QListWidgetItem(path.name)
            item.setData(Qt.ItemDataRole.UserRole, str(path))
            item.setToolTip(str(path))
            widget.addItem(item)
            if path in selected:
                item.setSelected(True)
    finally:
        widget.blockSignals(False)


def _patch_drop_list() -> None:
    global _DROP_PATCHED
    if _DROP_PATCHED:
        return

    def paths(self: DropList) -> list[Path]:
        return _production_paths(self)

    def add_paths(self: DropList, paths_to_add: list[Path]) -> None:
        production = _production_paths(self)
        known = {str(path) for path in production}
        added = False
        for candidate in paths_to_add:
            path = Path(candidate).expanduser()
            if not path.is_file() or path.suffix.lower() not in self.extensions:
                continue
            resolved = Path(path.resolve())
            if str(resolved) in known:
                continue
            production.append(resolved)
            known.add(str(resolved))
            added = True
        self._parity_production_paths = production
        if added:
            _render_drop_view(self)
            self.changed.emit()

    def remove_selected(self: DropList) -> None:
        selected = {
            Path(str(item.data(Qt.ItemDataRole.UserRole)))
            for item in self.selectedItems()
            if item.data(Qt.ItemDataRole.UserRole)
        }
        if not selected:
            return
        self._parity_production_paths = [
            path for path in _production_paths(self) if path not in selected
        ]
        _render_drop_view(self)
        self.changed.emit()

    def clear(self: DropList) -> None:
        self._parity_production_paths = []
        _DROP_CLEAR(self)

    DropList.paths = paths
    DropList.add_paths = add_paths
    DropList.remove_selected = remove_selected
    DropList.clear = clear
    _DROP_PATCHED = True


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


def _patch_preview_panel() -> None:
    global _PREVIEW_PATCHED
    if _PREVIEW_PATCHED:
        return
    original_init = PreviewPanel.__init__
    original_render = PreviewPanel._render_pixmap

    def render(self: PreviewPanel) -> None:
        pixmap = self._pixmap
        scroll = getattr(self, "_parity_scroll", None)
        if pixmap is None or pixmap.isNull() or scroll is None:
            original_render(self)
            return
        if getattr(self, "_parity_fit", True):
            viewport = scroll.viewport().size()
            target = pixmap.scaled(
                max(64, viewport.width() - 12),
                max(64, viewport.height() - 12),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        else:
            factor = max(0.25, min(8.0, int(self._parity_zoom) / 100.0))
            target = pixmap.scaled(
                max(1, round(pixmap.width() * factor)),
                max(1, round(pixmap.height() * factor)),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        self.image.setPixmap(target)
        self.image.resize(target.size())

    def set_zoom(self: PreviewPanel, value: int, *, persist: bool = True) -> None:
        self._parity_zoom = max(25, min(800, int(value)))
        self._parity_fit = False
        if hasattr(self, "parity_zoom"):
            self.parity_zoom.blockSignals(True)
            self.parity_zoom.setValue(self._parity_zoom)
            self.parity_zoom.blockSignals(False)
        render(self)
        if persist:
            _preview_save_zoom(self)

    def fit(self: PreviewPanel) -> None:
        self._parity_fit = True
        render(self)

    def fullscreen(self: PreviewPanel) -> None:
        if self._pixmap is None or self._pixmap.isNull():
            return
        _PreviewFullscreenDialog(self).exec()

    def init(self: PreviewPanel, parent: QWidget | None = None) -> None:
        original_init(self, parent)
        self._parity_zoom = 100
        self._parity_fit = True
        layout = self.layout()
        index = layout.indexOf(self.image)
        layout.removeWidget(self.image)
        self.image.setMinimumSize(64, 64)
        self.image.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        scroll = QScrollArea(self)
        scroll.setObjectName("previewScroll")
        scroll.setWidgetResizable(False)
        scroll.setAlignment(Qt.AlignmentFlag.AlignCenter)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(self.image)
        layout.insertWidget(max(1, index), scroll, 1)
        self._parity_scroll = scroll

        controls = QHBoxLayout()
        controls.addWidget(QLabel("Zoom"))
        self.parity_zoom = QSpinBox()
        self.parity_zoom.setRange(25, 800)
        self.parity_zoom.setSingleStep(25)
        self.parity_zoom.setSuffix(" %")
        self.parity_zoom.setValue(100)
        minus = QPushButton("−")
        plus = QPushButton("+")
        fit_button = QPushButton("Einpassen")
        fullscreen_button = QPushButton("Vollbild")
        controls.addWidget(minus)
        controls.addWidget(self.parity_zoom)
        controls.addWidget(plus)
        controls.addWidget(fit_button)
        controls.addWidget(fullscreen_button)
        controls.addStretch()
        layout.addLayout(controls)

        self.parity_zoom.valueChanged.connect(lambda value: set_zoom(self, value))
        minus.clicked.connect(lambda: set_zoom(self, self.parity_zoom.value() - 25))
        plus.clicked.connect(lambda: set_zoom(self, self.parity_zoom.value() + 25))
        fit_button.clicked.connect(lambda: fit(self))
        fullscreen_button.clicked.connect(lambda: fullscreen(self))
        self._parity_fit_button = fit_button
        self._parity_fullscreen_button = fullscreen_button

    PreviewPanel.__init__ = init
    PreviewPanel._render_pixmap = render
    PreviewPanel.set_parity_zoom = set_zoom
    PreviewPanel.fit_parity_preview = fit
    PreviewPanel.open_parity_fullscreen = fullscreen
    _PREVIEW_PATCHED = True


def _remember_directory(window: object, key: str, selected: list[Path]) -> None:
    if not selected:
        return
    _save_config(window, **{key: str(Path(selected[0]).expanduser().parent)})


def _initial_directory(window: object, key: str, fallback: Path) -> Path:
    cfg = _config(window)
    candidate = Path(str(cfg.get(key, fallback) or fallback)).expanduser()
    return candidate if candidate.is_dir() else fallback


def _choose_audio(window: object) -> None:
    initial = _initial_directory(window, "last_audio_dir", Path.home() / "Downloads")
    files, _ = QFileDialog.getOpenFileNames(
        window,
        "Audiodateien",
        str(initial),
        "Audio (*.mp3 *.wav *.flac *.m4a *.aac *.ogg *.opus *.wma);;Alle Dateien (*)",
    )
    paths = [Path(value) for value in files]
    if paths:
        window.audio.add_paths(paths)
        _remember_directory(window, "last_audio_dir", paths)


def _choose_media(window: object) -> None:
    initial = _initial_directory(window, "last_media_dir", Path.home() / "Downloads")
    files, _ = QFileDialog.getOpenFileNames(
        window,
        "Bilder oder Videos",
        str(initial),
        "Medien (*.png *.jpg *.jpeg *.webp *.avif *.mp4 *.mkv *.mov *.webm *.mpeg *.mpg);;Alle Dateien (*)",
    )
    paths = [Path(value) for value in files]
    if paths:
        window.media.add_paths(paths)
        _remember_directory(window, "last_media_dir", paths)


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


def _patch_media_browsers() -> None:
    from .qt_phase2 import VideoBatchQtPhase2Window

    VideoBatchQtWindow._choose_audio = _choose_audio
    VideoBatchQtWindow._choose_media = _choose_media
    VideoBatchQtPhase2Window._browse_audio = lambda self: _browse(self, audio=True)
    VideoBatchQtPhase2Window._browse_media = lambda self: _browse(self, audio=False)


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


def _patch_close_event() -> None:
    global _PHASE2_PATCHED
    if _PHASE2_PATCHED:
        return
    from .qt_phase2 import VideoBatchQtPhase2Window

    original_close = VideoBatchQtPhase2Window.closeEvent

    def close_event(self, event) -> None:
        if getattr(self, "_parity_completion_ready", False):
            _save_config(
                self,
                window_geometry=f"{self.width()}x{self.height()}",
                preview_zoom=int(getattr(self.preview_panel, "_parity_zoom", 100)),
                area_zoom=dict(getattr(self, "_parity_area_zoom", DEFAULT_CONFIG["area_zoom"])),
                audio_sort=str(getattr(self.audio, "_parity_view_sort", "import")),
                media_sort=str(getattr(self.media, "_parity_view_sort", "import")),
                active_tab=ROUTE_TO_ACTIVE_TAB.get(
                    getattr(self, "_parity_active_workspace", "dashboard"), 0
                ),
            )
        original_close(self, event)

    VideoBatchQtPhase2Window.closeEvent = close_event
    _PHASE2_PATCHED = True


def install_parity_completion() -> None:
    """Finish the remaining proven Tk -> Qt parity gaps without reintroducing Tk."""
    _patch_drop_list()
    _patch_preview_panel()
    _patch_media_browsers()
    _patch_close_event()

    from .qt_phase2 import VideoBatchQtPhase2Window

    original_init = VideoBatchQtPhase2Window.__init__
    if getattr(original_init, "_parity_completion_wrapped", False):
        return

    def init(self) -> None:
        boot = load_config()
        self._parity_boot_window_geometry = str(
            boot.get("window_geometry", DEFAULT_CONFIG["window_geometry"])
        )
        original_init(self)
        QTimer.singleShot(0, lambda: _finish_completion(self))

    init._parity_completion_wrapped = True
    VideoBatchQtPhase2Window.__init__ = init
