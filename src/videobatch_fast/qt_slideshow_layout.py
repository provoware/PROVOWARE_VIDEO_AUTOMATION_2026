from __future__ import annotations
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)
from .slideshow import (
    SLIDESHOW_MODE_ALL_IMAGES,
    SLIDESHOW_MODE_PAIRWISE,
    TRANSITION_LABELS,
)
from .slideshow_sequence import (
    ORDER_ALPHABETICAL,
    ORDER_CAPTURE_DATE,
    ORDER_RANDOM,
)


def _build(self) -> None:
    from .qt_phase2_components import ThumbnailOrderStrip, WaveformSceneView

    layout = QVBoxLayout(self)
    layout.setContentsMargins(12, 12, 12, 12)
    layout.setSpacing(8)

    title = QLabel("Diashow & Szenen")
    title.setObjectName("section")
    layout.addWidget(title)
    intro = QLabel(
        "Die drei Grundoptionen bleiben immer sichtbar. Reihenfolge und Waveform sind Zusatzwerkzeuge darunter."
    )
    intro.setObjectName("subtitle")
    intro.setWordWrap(True)
    layout.addWidget(intro)

    mode_row = QHBoxLayout()
    mode_row.addWidget(QLabel("Zuordnung"))
    self.assignment = QComboBox()
    self.assignment.addItem("Paarweise", SLIDESHOW_MODE_PAIRWISE)
    self.assignment.addItem("Alle Bilder je Audio", SLIDESHOW_MODE_ALL_IMAGES)
    mode_row.addWidget(self.assignment, 1)
    layout.addLayout(mode_row)

    transition_row = QHBoxLayout()
    transition_row.addWidget(QLabel("Überblendung"))
    self.transition = QComboBox()
    for key, label in TRANSITION_LABELS.items():
        self.transition.addItem(label, key)
    transition_row.addWidget(self.transition, 1)
    self.custom_transition_seconds = QDoubleSpinBox()
    self.custom_transition_seconds.setRange(0.0, 5.0)
    self.custom_transition_seconds.setDecimals(1)
    self.custom_transition_seconds.setSingleStep(0.1)
    self.custom_transition_seconds.setValue(1.0)
    self.custom_transition_seconds.setSuffix(" s")
    self.custom_transition_seconds.setAccessibleName("Individuelle Diashow-Überblenddauer")
    self.custom_transition_seconds.setEnabled(False)
    transition_row.addWidget(self.custom_transition_seconds)
    layout.addLayout(transition_row)

    self.scene_sync = QCheckBox("Bildwechsel an erkannten Szenen ausrichten")
    layout.addWidget(self.scene_sync)

    self.summary = QLabel()
    self.summary.setObjectName("safeHint")
    self.summary.setWordWrap(True)
    layout.addWidget(self.summary)

    advanced_title = QLabel("Weitere Diashow-Werkzeuge")
    advanced_title.setObjectName("section")
    layout.addWidget(advanced_title)

    scroll = QScrollArea()
    scroll.setObjectName("secondaryScroll")
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QFrame.Shape.NoFrame)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    advanced_content = QWidget()
    advanced = QVBoxLayout(advanced_content)
    advanced.setContentsMargins(0, 0, 6, 0)
    advanced.setSpacing(8)

    order_hint = QLabel("Optional: Bildreihenfolge ändern")
    order_hint.setObjectName("subtitle")
    advanced.addWidget(order_hint)
    order_buttons = QHBoxLayout()
    for text, callback in (
        ("A–Z", lambda: self._apply_order(ORDER_ALPHABETICAL)),
        ("Aufnahmezeit", lambda: self._apply_order(ORDER_CAPTURE_DATE)),
        ("Zufall", lambda: self._apply_order(ORDER_RANDOM)),
        ("Umkehren", self._reverse),
    ):
        button = QPushButton(text)
        button.clicked.connect(callback)
        order_buttons.addWidget(button)
    advanced.addLayout(order_buttons)

    anchor_buttons = QHBoxLayout()
    start_button = QPushButton("Als START")
    end_button = QPushButton("Als ENDE")
    clear_button = QPushButton("Anker löschen")
    start_button.clicked.connect(lambda: self._set_anchor("start"))
    end_button.clicked.connect(lambda: self._set_anchor("end"))
    clear_button.clicked.connect(self._clear_anchors)
    anchor_buttons.addWidget(start_button)
    anchor_buttons.addWidget(end_button)
    anchor_buttons.addWidget(clear_button)
    advanced.addLayout(anchor_buttons)

    self.strip = ThumbnailOrderStrip()
    self.strip.setMinimumHeight(130)
    self.strip.orderChanged.connect(self._manual_order)
    self.strip.selectedPathChanged.connect(self._select_image)
    advanced.addWidget(self.strip)

    self.order_status = QLabel("Noch keine Bilder.")
    self.order_status.setObjectName("subtitle")
    self.order_status.setWordWrap(True)
    advanced.addWidget(self.order_status)

    audio_hint = QLabel("Optional: Audioanalyse / Waveform")
    audio_hint.setObjectName("subtitle")
    advanced.addWidget(audio_hint)
    audio_row = QHBoxLayout()
    audio_row.addWidget(QLabel("Waveform-Audio"))
    self.audio_select = QComboBox()
    audio_row.addWidget(self.audio_select, 1)
    self.analyze = QPushButton("Analysieren")
    audio_row.addWidget(self.analyze)
    advanced.addLayout(audio_row)

    self.waveform = WaveformSceneView()
    self.waveform.setMinimumHeight(190)
    advanced.addWidget(self.waveform)

    self.analysis_status = QLabel("Noch keine Audioanalyse.")
    self.analysis_status.setObjectName("subtitle")
    self.analysis_status.setWordWrap(True)
    advanced.addWidget(self.analysis_status)
    advanced.addStretch()

    scroll.setWidget(advanced_content)
    layout.addWidget(scroll, 1)

    self.assignment.currentIndexChanged.connect(self._state_changed)
    self.transition.currentIndexChanged.connect(self._transition_changed)
    self.custom_transition_seconds.valueChanged.connect(self._state_changed)
    self.scene_sync.toggled.connect(self._scene_sync_changed)
    self.audio_select.currentIndexChanged.connect(self._audio_changed)
    self.analyze.clicked.connect(lambda: self.analyze_selected(refresh=True))
