from __future__ import annotations
from pathlib import Path
from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QProgressBar,
    QPushButton,
    QSplitter,
    QVBoxLayout,
)
from .media_index import media_roots
from .qt_phase2_components import PreviewPanel


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
    videos = QPushButton("Videos")
    pictures = QPushButton("Bilder")
    self.path_edit = QLineEdit(str(self.current_dir))
    load = QPushButton("Ordner laden")
    load.setObjectName("primary")
    up.clicked.connect(lambda: self._navigate(self.current_dir.parent))
    home.clicked.connect(lambda: self._navigate(Path.home()))
    downloads.clicked.connect(lambda: self._navigate(media_roots()["downloads"]))
    videos.clicked.connect(lambda: self._navigate(media_roots()["videos"]))
    pictures.clicked.connect(lambda: self._navigate(media_roots()["pictures"]))
    self.path_edit.returnPressed.connect(lambda: self._navigate(Path(self.path_edit.text())))
    load.clicked.connect(lambda: self._navigate(Path(self.path_edit.text())))
    nav.addWidget(up)
    nav.addWidget(home)
    nav.addWidget(downloads)
    nav.addWidget(videos)
    nav.addWidget(pictures)
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
    self.more_button = QPushButton("Weitere Dateien anzeigen")
    self.more_button.setVisible(False)
    self.more_button.clicked.connect(self._show_more_records)
    left_layout.addWidget(self.more_button)
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
