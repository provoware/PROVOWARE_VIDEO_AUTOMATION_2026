from __future__ import annotations

import threading
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QProgressBar,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from .incremental_directory import DirectoryRecord, scan_directory_batches
from .media_dialog_support import human_size, safe_media_directory, sort_directory_records
from .probe import AUDIO_EXTENSIONS, IMAGE_EXTENSIONS, VIDEO_EXTENSIONS
from .qt_phase2_components import PreviewPanel


class MediaImportDialog(QDialog):
    """Native Qt media browser with incremental scan, filter, sorting and live preview."""

    KEEP_OPEN_LABEL = "Auswahl übernehmen + im Ordner bleiben"

    _scanBatch = Signal(int, object)
    _scanDone = Signal(int, str)

    def __init__(
        self,
        parent: QWidget | None,
        *,
        audio: bool,
        initial_dir: Path,
        modal: bool = True,
    ) -> None:
        super().__init__(parent)
        self.audio = bool(audio)
        self.allowed = AUDIO_EXTENSIONS if self.audio else IMAGE_EXTENSIONS | VIDEO_EXTENSIONS
        self.current_dir = safe_media_directory(initial_dir)
        self.result: tuple[Path, ...] = ()
        self.collected: list[Path] = []
        self._records: list[DirectoryRecord] = []
        self._scan_generation = 0
        self._scan_cancel = threading.Event()
        self._scan_complete = False
        self.sort_key = "name"
        self.sort_reverse = False

        self.setWindowTitle("Audio auswählen" if self.audio else "Bilder und Videos auswählen")
        self.resize(1220, 760)
        self.setMinimumSize(1000, 650)
        self.setModal(modal)
        self._build()
        self._scanBatch.connect(self._apply_scan_batch)
        self._scanDone.connect(self._finish_scan)
        self._load_directory()

    def _build(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(14, 14, 14, 14)

        header = QHBoxLayout()
        title = QLabel("Audiodateien auswählen" if self.audio else "Bilder und Videos auswählen")
        title.setObjectName("dialogTitle")
        header.addWidget(title)
        header.addStretch()
        self.list_mode = QPushButton("☷ Liste")
        self.icon_mode = QPushButton("▦ Symbole")
        self.list_mode.clicked.connect(lambda: self._set_view_mode("list"))
        self.icon_mode.clicked.connect(lambda: self._set_view_mode("icons"))
        header.addWidget(self.list_mode)
        header.addWidget(self.icon_mode)
        outer.addLayout(header)

        nav = QHBoxLayout()
        up = QPushButton("← Hoch")
        home = QPushButton("Home")
        downloads = QPushButton("Downloads")
        self.path_edit = QLineEdit(str(self.current_dir))
        load = QPushButton("Ordner laden")
        load.setObjectName("primary")
        up.clicked.connect(lambda: self._navigate(self.current_dir.parent))
        home.clicked.connect(lambda: self._navigate(Path.home()))
        downloads.clicked.connect(lambda: self._navigate(Path.home() / "Downloads"))
        self.path_edit.returnPressed.connect(lambda: self._navigate(Path(self.path_edit.text())))
        load.clicked.connect(lambda: self._navigate(Path(self.path_edit.text())))
        nav.addWidget(up)
        nav.addWidget(home)
        nav.addWidget(downloads)
        nav.addWidget(self.path_edit, 1)
        nav.addWidget(load)
        outer.addLayout(nav)

        tools = QHBoxLayout()
        tools.addWidget(QLabel("Filter"))
        self.filter_edit = QLineEdit()
        self.filter_edit.setPlaceholderText("Name oder Dateiendung")
        self.filter_edit.textChanged.connect(self._render_records)
        tools.addWidget(self.filter_edit, 1)
        tools.addWidget(QLabel("Sortieren"))
        self.sort_combo = QComboBox()
        for label, key in (
            ("Name", "name"),
            ("Größe", "size"),
            ("Geändert", "modified"),
            ("Art", "kind"),
        ):
            self.sort_combo.addItem(label, key)
        self.sort_combo.currentIndexChanged.connect(self._sort_changed)
        tools.addWidget(self.sort_combo)
        self.sort_direction = QPushButton("↑")
        self.sort_direction.setFixedWidth(44)
        self.sort_direction.clicked.connect(self._toggle_sort)
        tools.addWidget(self.sort_direction)
        self.scan_progress = QProgressBar()
        self.scan_progress.setRange(0, 0)
        self.scan_progress.setMaximumWidth(160)
        tools.addWidget(self.scan_progress)
        self.scan_stop = QPushButton("Scan stoppen")
        self.scan_stop.clicked.connect(self._stop_scan)
        tools.addWidget(self.scan_stop)
        outer.addLayout(tools)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)

        left = QFrame()
        left.setObjectName("panel")
        left_layout = QVBoxLayout(left)
        self.files = QListWidget()
        self.files.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.files.setIconSize(QSize(126, 84))
        self.files.itemSelectionChanged.connect(self._selection_changed)
        self.files.itemDoubleClicked.connect(self._activate_item)
        left_layout.addWidget(self.files, 1)
        self.status = QLabel("Ordner wird geladen …")
        self.status.setObjectName("subtitle")
        self.status.setWordWrap(True)
        left_layout.addWidget(self.status)
        self.collection_status = QLabel("Noch keine Dateien übernommen")
        self.collection_status.setObjectName("subtitle")
        left_layout.addWidget(self.collection_status)
        splitter.addWidget(left)

        self.preview = PreviewPanel()
        splitter.addWidget(self.preview)
        splitter.setSizes([720, 480])
        outer.addWidget(splitter, 1)

        actions = QHBoxLayout()
        self.keep_open = QPushButton(self.KEEP_OPEN_LABEL)
        self.accept_button = QPushButton("Auswahl übernehmen")
        self.accept_button.setObjectName("primary")
        cancel = QPushButton("Abbrechen")
        self.keep_open.clicked.connect(self._collect_selection)
        self.accept_button.clicked.connect(self._accept_selection)
        cancel.clicked.connect(self.reject)
        actions.addWidget(self.keep_open)
        actions.addStretch()
        actions.addWidget(cancel)
        actions.addWidget(self.accept_button)
        outer.addLayout(actions)

        self._set_view_mode("list" if self.audio else "icons")

    def _navigate(self, path: Path) -> None:
        candidate = safe_media_directory(path)
        self.current_dir = candidate
        self.path_edit.setText(str(candidate))
        self._load_directory()

    def _load_directory(self) -> None:
        self._scan_cancel.set()
        self._scan_generation += 1
        generation = self._scan_generation
        self._scan_cancel = threading.Event()
        cancel = self._scan_cancel
        directory = self.current_dir
        self._records = []
        self._scan_complete = False
        self.files.clear()
        self.preview.set_source(None, include_image=False)
        self.status.setText("Erste Dateien werden geladen …")
        self.scan_progress.setRange(0, 0)
        self.scan_stop.setEnabled(True)

        def worker() -> None:
            error = ""
            try:
                for batch in scan_directory_batches(
                    directory,
                    self.allowed,
                    cancel=cancel,
                    batch_size=128,
                ):
                    if cancel.is_set():
                        break
                    self._scanBatch.emit(generation, batch)
            except OSError as exc:
                error = str(exc)
            self._scanDone.emit(generation, error)

        threading.Thread(
            target=worker,
            daemon=True,
            name=f"VideoBatch-Qt-MediaScan-{generation}",
        ).start()

    def _apply_scan_batch(self, generation: int, records_object: object) -> None:
        if generation != self._scan_generation:
            return
        records = list(records_object)
        self._records.extend(records)
        self.status.setText(f"{len(self._records)} Einträge gefunden · Scan läuft …")
        self._render_records()

    def _finish_scan(self, generation: int, error: str) -> None:
        if generation != self._scan_generation:
            return
        self._scan_complete = True
        self.scan_progress.setRange(0, 100)
        self.scan_progress.setValue(100)
        self.scan_stop.setEnabled(False)
        self._render_records()
        if error:
            self.status.setText(f"Scan mit Einschränkung beendet: {error}")
        elif self._scan_cancel.is_set():
            self.status.setText(f"Scan angehalten · {len(self._records)} Einträge gefunden")
        else:
            self.status.setText(f"Scan fertig · {len(self._records)} Einträge gefunden")

    def _stop_scan(self) -> None:
        self._scan_cancel.set()
        self.scan_stop.setEnabled(False)
        self.scan_progress.setRange(0, 100)
        self.scan_progress.setValue(0)
        self.status.setText(f"Scan angehalten · {len(self._records)} Einträge bleiben auswählbar")

    def _sort_changed(self) -> None:
        self.sort_key = str(self.sort_combo.currentData() or "name")
        self._render_records()

    def _toggle_sort(self) -> None:
        self.sort_reverse = not self.sort_reverse
        self.sort_direction.setText("↓" if self.sort_reverse else "↑")
        self._render_records()

    def _render_records(self) -> None:
        selected = {Path(str(item.data(Qt.ItemDataRole.UserRole))) for item in self.files.selectedItems()}
        query = self.filter_edit.text().strip().casefold()
        records = sort_directory_records(self._records, self.sort_key, self.sort_reverse)
        if query:
            records = [record for record in records if query in record.path.name.casefold()]

        self.files.blockSignals(True)
        self.files.clear()
        for record in records:
            if record.is_dir:
                text = f"📁 {record.path.name}"
            else:
                changed = datetime.fromtimestamp(record.modified).strftime("%Y-%m-%d %H:%M")
                text = f"{record.path.name}\n{human_size(record.size)} · {changed}"
            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, str(record.path))
            item.setData(Qt.ItemDataRole.UserRole + 1, record.is_dir)
            item.setToolTip(str(record.path))
            self.files.addItem(item)
            if record.path in selected:
                item.setSelected(True)
        self.files.blockSignals(False)
        self._selection_changed()

    def _set_view_mode(self, mode: str) -> None:
        if mode == "icons":
            self.files.setViewMode(QListWidget.ViewMode.IconMode)
            self.files.setFlow(QListWidget.Flow.LeftToRight)
            self.files.setWrapping(True)
            self.files.setResizeMode(QListWidget.ResizeMode.Adjust)
            self.files.setGridSize(QSize(190, 124))
        else:
            self.files.setViewMode(QListWidget.ViewMode.ListMode)
            self.files.setWrapping(False)
            self.files.setGridSize(QSize())
        self.list_mode.setProperty("selectedMode", mode == "list")
        self.icon_mode.setProperty("selectedMode", mode == "icons")
        self.list_mode.style().unpolish(self.list_mode)
        self.list_mode.style().polish(self.list_mode)
        self.icon_mode.style().unpolish(self.icon_mode)
        self.icon_mode.style().polish(self.icon_mode)

    def _selected_file_paths(self) -> list[Path]:
        paths: list[Path] = []
        for item in self.files.selectedItems():
            if bool(item.data(Qt.ItemDataRole.UserRole + 1)):
                continue
            raw = item.data(Qt.ItemDataRole.UserRole)
            if raw:
                paths.append(Path(str(raw)))
        return paths

    def _selection_changed(self) -> None:
        current = self.files.currentItem()
        if current is None:
            self.preview.set_source(None, include_image=False)
            return
        raw = current.data(Qt.ItemDataRole.UserRole)
        is_dir = bool(current.data(Qt.ItemDataRole.UserRole + 1))
        if not raw or is_dir:
            self.preview.set_source(None, include_image=False)
            return
        path = Path(str(raw))
        self.preview.set_source(path, include_image=not self.audio)

    def _activate_item(self, item: QListWidgetItem) -> None:
        raw = item.data(Qt.ItemDataRole.UserRole)
        if not raw:
            return
        path = Path(str(raw))
        if bool(item.data(Qt.ItemDataRole.UserRole + 1)):
            self._navigate(path)
            return
        self._collect_paths([path])

    def _collect_paths(self, paths: list[Path]) -> None:
        known = set(self.collected)
        for path in paths:
            if path not in known:
                self.collected.append(path)
                known.add(path)
        self.collection_status.setText(f"{len(self.collected)} Datei(en) gesammelt")

    def _collect_selection(self) -> None:
        self._collect_paths(self._selected_file_paths())

    def _accept_selection(self) -> None:
        selected = self._selected_file_paths()
        self._collect_paths(selected)
        self.result = tuple(self.collected)
        if not self.result:
            self.status.setText("Noch keine Datei ausgewählt.")
            return
        self.accept()

    def wait(self) -> tuple[Path, ...]:
        if not self.isVisible():
            self.exec()
        return self.result

    def reject(self) -> None:
        self.result = ()
        super().reject()

    def closeEvent(self, event) -> None:
        self._scan_cancel.set()
        self.preview.shutdown()
        super().closeEvent(event)
