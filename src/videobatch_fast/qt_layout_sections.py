from __future__ import annotations


from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QComboBox, QDoubleSpinBox, QSlider, QHBoxLayout, QLabel, QWidget, QLineEdit, QPushButton, QScrollArea

from .qt_theme import scaled_style
from .qt_adaptive_settings import ResponsiveSettingsPanel
from .dashboard_settings import RESOLUTION_LABELS, QUALITY_LABELS, EFFECT_LABELS
from .effects import TRANSITIONS




def build_settings(window) -> None:
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



def apply_scale(window, title, subtitle, dashboard) -> None:
    value = int(window.view_scale.currentData() or 100)
    app = QApplication.instance()
    if app is not None:
        app.setStyleSheet(scaled_style(value))
    window.table.verticalHeader().setDefaultSectionSize(round(38 * value / 100))
    # A compact title keeps all original font choices for the WORK controls;
    # only the decorative brand loses excess height on tiny screens.
    small_large = value >= 175 and window.width() <= 900
    # The persistent next-step hint must show more than one line at 800x600.
    # It remains visible while the workflow itself can scroll vertically.
    window.action_footer_scroll.setMinimumHeight(82 if small_large else 52)
    title.setStyleSheet("font-size: 24px; font-weight: 800;" if small_large else "")
    window.status.setStyleSheet(
        "font-size: 17px; padding: 3px 6px; font-weight: 800;" if small_large else ""
    )
    for button, full, short in getattr(window, "_source_action_labels", []):
        button.setText(short if small_large else full)
    for label_widget, full, short in getattr(window, "_source_header_labels", []):
        label_widget.setText(short if small_large else full)
    # Full headings remain available via tooltips and at normal screen sizes.
    full_headers = ("#", "Audio", "Medium", "Status", "Einzel-Fortschritt")
    short_headers = ("#", "Audio", "Bild", "Stand", "%")
    for column, full_label in enumerate(full_headers):
        header_item = window.table.horizontalHeaderItem(column)
        if header_item is not None:
            header_item.setText(short_headers[column] if small_large else full_label)
            header_item.setToolTip(full_label)
    compact = value >= 150
    window.menuBar().setVisible(not compact)
    window.compact_menu.setVisible(compact)
    window.main_tabs.setTabText(3, "Hilfe" if compact else "Hilfe / Werkzeuge")
    subtitle.setVisible(value <= 110)
    window.load_dashboard.frame.setVisible(not compact)
    route = getattr(window, "_active_workflow_route", "media")
    dashboard.setVisible(not compact or route == "queue")
    window.settings_grid.set_zoom_percent(value)
    window.source_columns.set_zoom_percent(value)
    for control_row in window._responsive_control_rows:
        control_row.set_zoom_percent(value)



def update_slideshow_hint(self, audios, images, jobs, output_ready, ready, pending) -> None:
    if pending and not self.runner.running and not self.preparing:
        self._status("ANALYSE")
        self.next_step.setText("Audioanalyse läuft. Danach wird Schritt 3 automatisch freigegeben.")
    elif not self.runner.running and not self.preparing:
        if not audios:
            self.next_step.setText("Nächster Schritt: 1 · Mindestens eine Audiodatei auswählen.")
        elif not images:
            self.next_step.setText("Nächster Schritt: 1 · Bilder für die Diashow auswählen.")
        elif not output_ready:
            self.next_step.setText("Nächster Schritt: 2 · Einen Ausgabeordner wählen.")
        else:
            self.next_step.setText(f"Bereit: {jobs} Diashow-Video(s). Nächster Schritt: 3 · Videos erstellen.")
        self._status("BEREIT" if ready else "PRÜFEN")
