from __future__ import annotations

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
