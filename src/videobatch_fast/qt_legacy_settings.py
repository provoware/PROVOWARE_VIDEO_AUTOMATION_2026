from __future__ import annotations

from collections.abc import Callable
from typing import Any

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QFrame,
    QLabel,
    QLineEdit,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from .command_builder import PROFILES
from .effects import TRANSITIONS, VISUAL_EFFECTS

ComboFactory = Callable[[QWidget, list[tuple[str, str]], str], QComboBox]


def build_settings_tab(window: Any, *, combo_factory: ComboFactory) -> QWidget:
    tab = QWidget()
    layout = QVBoxLayout(tab)
    intro = QLabel(
        "Übernommene Einstellungen der früheren Tk-Version. "
        "Automatik bleibt der Standard; „Eigene Feineinstellung“ schaltet die Expertenfelder frei."
    )
    intro.setWordWrap(True)
    intro.setObjectName("subtitle")
    layout.addWidget(intro)

    form = QFormLayout()
    cfg = window._parity_config
    window.parity_output_mode = combo_factory(
        tab,
        [("Gemeinsamer Ordner", "Gemeinsamer Ordner"), ("Neben Mediendatei", "Neben Mediendatei")],
        str(cfg.get("output_mode", "Gemeinsamer Ordner")),
    )
    window.parity_resolution = combo_factory(
        tab,
        [(value, value) for value in ("Original", "1280×720", "1920×1080")],
        str(cfg.get("resolution", "Original")),
    )
    window.parity_codec = combo_factory(
        tab,
        [("H.264 / libx264", "libx264"), ("H.265 / libx265", "libx265")],
        str(cfg.get("codec", "libx264")),
    )
    window.parity_profile = combo_factory(
        tab,
        [(spec.label, key) for key, spec in PROFILES.items()],
        str(cfg.get("profile", "fast")),
    )
    window.parity_effect = combo_factory(
        tab,
        [(spec.label, key) for key, spec in VISUAL_EFFECTS.items()],
        str(cfg.get("visual_effect", "none")),
    )
    window.parity_transition = combo_factory(
        tab,
        [(spec.label, key) for key, spec in TRANSITIONS.items()],
        str(cfg.get("transition", "none")),
    )
    form.addRow("Ausgabeart", window.parity_output_mode)
    form.addRow("Auflösung", window.parity_resolution)
    form.addRow("Video-Codec", window.parity_codec)
    form.addRow("Renderprofil", window.parity_profile)
    form.addRow("Bildeffekt", window.parity_effect)
    form.addRow("Ein-/Ausblendung", window.parity_transition)
    layout.addLayout(form)

    window.parity_keep_lists = QCheckBox("Dateilisten nach erfolgreicher Produktion behalten")
    window.parity_keep_lists.setChecked(bool(cfg.get("keep_lists", True)))
    window.parity_auto_open = QCheckBox(
        "Ausgabeordner nach erfolgreicher Produktion automatisch öffnen"
    )
    window.parity_auto_open.setChecked(bool(cfg.get("auto_open_output", True)))
    layout.addWidget(window.parity_keep_lists)
    layout.addWidget(window.parity_auto_open)

    archive = QFrame()
    archive.setObjectName("card")
    archive_layout = QFormLayout(archive)
    window.parity_archive_used = QCheckBox(
        "Verwendete Quelldateien nach erfolgreicher Produktion sicher ablegen"
    )
    window.parity_archive_used.setChecked(bool(cfg.get("archive_used", False)))
    window.parity_archive_dir = QLineEdit(str(cfg.get("archive_project_dir", "") or ""))
    window.parity_archive_dir.setPlaceholderText("Projekt-/Archivordner")
    window.parity_archive_suffix = QLineEdit(
        str(cfg.get("archive_suffix", "__verwendet") or "__verwendet")
    )
    archive_layout.addRow(window.parity_archive_used)
    archive_layout.addRow("Ablageordner", window.parity_archive_dir)
    archive_layout.addRow("Namenszusatz", window.parity_archive_suffix)
    layout.addWidget(archive)

    appearance = QFrame()
    appearance.setObjectName("card")
    appearance_layout = QFormLayout(appearance)
    window.parity_theme = combo_factory(
        appearance,
        [
            ("Neon Gravity", "neon_gravity"),
            ("Acid Paper", "acid_paper"),
            ("Toxic Candy", "toxic_candy"),
            ("Ultraviolet", "ultraviolet"),
        ],
        str(cfg.get("theme", "neon_gravity")),
    )
    window.parity_font_scale = QSpinBox()
    window.parity_font_scale.setRange(80, 160)
    window.parity_font_scale.setSuffix(" %")
    window.parity_font_scale.setSingleStep(10)
    window.parity_font_scale.setValue(int(cfg.get("font_scale", 105)))
    appearance_layout.addRow("Farbtheme", window.parity_theme)
    appearance_layout.addRow("Schriftgröße", window.parity_font_scale)
    layout.addWidget(appearance)

    layout.addStretch()
    return tab
