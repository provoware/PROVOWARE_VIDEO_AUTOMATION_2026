from __future__ import annotations

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (QComboBox, QFrame, QHBoxLayout, QPushButton, QSizePolicy,
                               QVBoxLayout, QWidget)
from .qt_media_list import SORT_MODES, DropList
from .qt_responsive_controls import ResponsiveControlRow
from .qt_ui_polish import configure_file_buttons, field_label
import sqlite3
import threading
import time
from .paths import state_dir
from pathlib import Path
from PySide6.QtCore import QTimer, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QComboBox, QFrame, QLabel, QMessageBox, QPlainTextEdit, QPushButton,
    QToolButton, QVBoxLayout, QWidget,
)
from .media_index_preferences import load_exclusions
from .qt_ui_polish import (
    field_label,
)


from .paths import state_dir
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QMessageBox


def open_output_folder(window) -> None:
    output = Path(window.output.text().strip()).expanduser()
    try:
        output.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        QMessageBox.warning(window, "Ausgabeordner nicht verfügbar", str(exc))
        return
    if not QDesktopServices.openUrl(QUrl.fromLocalFile(str(output))):
        QMessageBox.warning(window, "Ausgabeordner nicht geöffnet", str(output))


def _refresh_media_index_async(self) -> None:
    if self._media_index_stop.is_set():
        return
    if self._media_index_worker is not None and self._media_index_worker.is_alive():
        if self._media_rescan_pending:
            QTimer.singleShot(1500, self._refresh_media_index_async)
        return
    self._media_rescan_pending = False
    self._media_index_reconfigure.clear()
    index = self._media_index  # capture configuration for this worker
    def worker() -> None:
        from .media_watcher import MediaWatcher
        try:
            for result in index.refresh(cancel=self._media_index_stop):
                if result.error and not self._media_index_stop.is_set():
                    self.mediaIndexMessage.emit(
                        f"{result.root}: {result.error}. Gespeicherte Medien bleiben erhalten."
                    )
            if self._media_index_stop.is_set() or self._media_index_reconfigure.is_set():
                return
            with MediaWatcher(index.roots, index.excluded_paths) as watcher:
                last_full_scan = time.monotonic()
                while not (self._media_index_stop.is_set() or
                           self._media_index_reconfigure.is_set()):
                    affected = watcher.changed(timeout=1.0)
                    if affected:
                        # Bundle bursts (downloads often write in many chunks).
                        time.sleep(0.3)
                        affected.update(watcher.changed(timeout=0.0))
                        for root in sorted(affected):
                            if self._media_index_stop.is_set() or self._media_index_reconfigure.is_set():
                                return
                            index.refresh_root(root, cancel=self._media_index_stop)
                        if watcher.topology_changed:
                            watcher.reset()
                    now = time.monotonic()
                    interval = 300 if watcher.coverage_limited else 1800
                    if now - last_full_scan >= interval:
                        index.refresh(cancel=self._media_index_stop)
                        if watcher.coverage_limited:
                            watcher.reset()
                        last_full_scan = now
        except (OSError, ValueError, RuntimeError, sqlite3.DatabaseError) as exc:
            # Optional index failure is visible but never blocks rendering.
            if not self._media_index_stop.is_set():
                self.mediaIndexMessage.emit(
                    f"Index vorübergehend nicht verfügbar: {exc}. Videos erstellen ist weiterhin möglich."
                )
            return
    self._media_index_worker = threading.Thread(
        target=worker, name="VideoBatch-MediaIndex", daemon=True
    )
    self._media_index_worker.start()


def _settings_panel(self) -> QWidget:
    panel, layout = self._panel(
        "Erweiterte Einstellungen",
        "Hier stehen selten benötigte Prüf- und Sicherheitsoptionen. "
        "Die alltäglichen Ausgabeoptionen stehen vor diesen Expertenoptionen.",
    )
    layout.addWidget(field_label("Kontrolle nach der Erstellung"))
    # Compatibility-only adapter for older project/playlist services.
    # Not displayed; the authoritative values live in dashboard_settings.
    self.mode = QComboBox()
    self.mode.addItem("Dashboard-Vorgaben", "custom")
    self.verification = QComboBox()
    self.verification.addItems(["Vollständig", "Schnell"])
    self.verification.setToolTip("Vollständig überprüft das fertige Video genauer.")
    layout.addWidget(self.verification)
    self.exclusions_toggle = QToolButton()
    self.exclusions_toggle.setText("▸ Eigene Programmierordner auslassen")
    self.exclusions_toggle.setCheckable(True)
    self.exclusions_toggle.setAccessibleDescription(
        "Optional. Ordner innerhalb von Videos, Downloads und Bilder gezielt auslassen."
    )
    layout.addWidget(self.exclusions_toggle)
    exclusions_box = QFrame()
    exclusion_layout = QVBoxLayout(exclusions_box)
    exclusion_layout.setContentsMargins(6, 4, 6, 4)
    exclusions_box.setVisible(False)
    self.exclusions_toggle.toggled.connect(exclusions_box.setVisible)
    exclusion_layout.addWidget(field_label("Ordner bei der Mediensuche auslassen"))
    info = QLabel(
        "Hier kannst du eigene Programmierordner in Videos, Downloads oder Bilder "
        "ausschließen. Ein vollständiger Ordnerpfad pro Zeile. "
        "Andere Dateien werden ohnehin ignoriert."
    )
    info.setWordWrap(True)
    exclusion_layout.addWidget(info)
    self.media_exclusions = QPlainTextEdit()
    self.media_exclusions.setAccessibleName("Ausgeschlossene Projektordner")
    self.media_exclusions.setPlaceholderText(
        str(Path.home() / "Downloads" / "Mein-Programmierprojekt")
    )
    self.media_exclusions.setMaximumHeight(94)
    try:
        self.media_exclusions.setPlainText(
            "\n".join(str(path) for path in load_exclusions())
        )
    except ValueError:
        self.media_exclusions.setPlaceholderText(
            "Gespeicherte Liste ist beschädigt. Bitte hier neue Ordner eingeben."
        )
    exclusion_layout.addWidget(self.media_exclusions)
    self.browse_exclusion_button = QPushButton("Projektordner auswählen …")
    self.browse_exclusion_button.clicked.connect(self._browse_media_exclusion)
    exclusion_layout.addWidget(self.browse_exclusion_button)
    self.save_exclusions_button = QPushButton("Ausgeschlossene Ordner speichern")
    self.save_exclusions_button.clicked.connect(self._save_media_exclusions)
    exclusion_layout.addWidget(self.save_exclusions_button)
    self.media_exclusion_status = QLabel("")
    self.media_exclusion_status.setObjectName("subtitle")
    self.media_exclusion_status.setWordWrap(True)
    exclusion_layout.addWidget(self.media_exclusion_status)
    layout.addWidget(exclusions_box)
    self.details_toggle = QToolButton()
    self.details_toggle.setText("▸ Technische Details und Sicherheit")
    self.details_toggle.setCheckable(True)
    layout.addWidget(self.details_toggle)
    self.safety_details = QLabel(
        "Originaldateien bleiben unverändert.\n"
        "Ausgaben erhalten eindeutige Dateinamen.\n"
        "VideoBatch kann die Verarbeitung kontrolliert abbrechen."
    )
    self.safety_details.setObjectName("subtitle")
    self.safety_details.setWordWrap(True)
    self.safety_details.setVisible(False)
    layout.addWidget(self.safety_details)
    self.details_toggle.toggled.connect(self._toggle_details)
    self.runtime = QLabel()
    self.runtime.setObjectName("subtitle")
    layout.addWidget(self.runtime)
    layout.addStretch()
    self._runtime_state()
    return panel



def _source_card(window, label: str, widget: DropList, add_text: str) -> QFrame:
    card = QFrame()
    card.setObjectName("sourceCard")
    layout = QVBoxLayout(card)
    layout.setContentsMargins(10, 10, 10, 10)
    layout.setSpacing(7)

    header = QHBoxLayout()
    source_label = field_label(label)
    source_label.setAccessibleName(label)
    source_label.setToolTip(label)
    if not hasattr(window, "_source_header_labels"):
        window._source_header_labels = []
    window._source_header_labels.append((source_label, label, "Audio" if widget is window.audio else "Medien"))
    header.addWidget(source_label)
    header.addStretch()
    sorter = QComboBox()
    sorter.setAccessibleName(f"{label} sortieren")
    # At 200% the previous hard minimum expanded the entire scroll page.
    sorter.setMinimumWidth(0)
    sorter.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
    for sort_label, sort_mode in SORT_MODES:
        sorter.addItem(sort_label, sort_mode)
    sorter.currentIndexChanged.connect(
        lambda _index, target=widget, control=sorter: target.sort_by(str(control.currentData()))
    )
    header.addWidget(sorter)
    layout.addLayout(header)

    widget.setMinimumHeight(170)
    layout.addWidget(widget, 1)

    add = QPushButton(add_text)
    add.setAccessibleName(add_text)
    add.setToolTip(add_text)
    if not hasattr(window, "_source_action_labels"):
        window._source_action_labels = []
    short = "Audio wählen …" if widget is window.audio else "Medien wählen …"
    window._source_action_labels.append((add, add_text, short))
    remove = QPushButton("Entfernen")
    configure_file_buttons(add, remove, label)
    # The full accessible text remains available while 200%-zoom screens
    # receive a short visible action label instead of clipped letters.
    remove.setAccessibleName("Ausgewählte Dateien aus der Liste entfernen")
    remove.setToolTip(
        "Markierte Dateien nur aus der Liste entfernen; Originalmedien bleiben erhalten."
    )
    window._source_action_labels.append((remove, "Entfernen", "Entf."))
    add.clicked.connect(window._choose_audio if widget is window.audio else window._choose_media)
    remove.clicked.connect(widget.remove_selected)
    actions = ResponsiveControlRow((add, remove))
    window._responsive_control_rows.append(actions)
    layout.addWidget(actions)
    return card


def _diagnostic_payload(self) -> dict[str, object]:
    logs = state_dir() / "logs"
    from .diagnostics_service import build_diagnostic_payload

    return build_diagnostic_payload(
        session_id=self._session_id,
        project_file=self._project_file,
        human_log=logs / "qt_phase3_human.log",
        machine_log=logs / "qt_phase3_machine.jsonl",
    )
