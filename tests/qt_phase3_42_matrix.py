"""Automatisierte 42-Fälle-Prüfung der realen Qt-Phase-3-Oberfläche.

Sechs Bildschirmgrößen mal sieben Schriftstufen, mit je drei Screenshots.
Das ersetzt ausdrücklich keine physische Wayland-Sichtabnahme.
"""
from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QLabel, QPushButton, QToolButton

from videobatch_fast.qt_phase3 import VideoBatchQtPhase3Window

SIZES = ((800, 600), (1024, 768), (1280, 720), (1366, 768), (1920, 1080), (2560, 1440))
SCALES = (80, 100, 110, 125, 150, 175, 200)
ROUTES = ((0, "01_dateien"), (1, "02_ausgabe"), (2, "03_produktion"))


def findings(window: VideoBatchQtPhase3Window, width: int, height: int) -> list[str]:
    problems: list[str] = []
    if (window.width(), window.height()) != (width, height):
        problems.append(f"Fenster {window.width()}x{window.height()} statt {width}x{height}")
    # Nicht nur Widgets zählen: ein Qt-Label kann als "sichtbar" gelten,
    # obwohl es kleiner als eine einzige Textzeile zusammengedrückt wird.
    for label in window.findChildren(QLabel):
        if label.objectName() not in {"title", "statusChip", "section"}:
            continue
        if not label.isVisibleTo(window) or not label.text().strip():
            continue
        needed_height = label.fontMetrics().height()
        if label.height() + 2 < needed_height:
            problems.append(
                f"Textzeile abgeschnitten: {label.text()[:35]!r}, "
                f"{label.height()}px statt {needed_height}px"
            )
        if label.objectName() == "title":
            needed_width = label.fontMetrics().horizontalAdvance(label.text())
            if label.width() + 2 < needed_width:
                problems.append("Programmtitel horizontal abgeschnitten")
    if width <= 900 and int(window.view_scale.currentData() or 100) >= 175:
        if window.action_footer_scroll.height() < 78:
            problems.append(
                f"Nächster-Schritt-Hinweis zu flach: {window.action_footer_scroll.height()}px"
            )
    # Detect regressions in the specifically affected 800x600 / 200% layout.
    if width <= 900 and int(window.view_scale.currentData() or 100) >= 175:
        full = [window.table.horizontalHeaderItem(i).text() for i in range(5)]
        if full != ["#", "Audio", "Bild", "Stand", "%"]:
            problems.append(f"Kompakte Tabellenüberschriften fehlen: {full!r}")
        # A hidden sideways-scroll offset previously clipped the left side of
        # "Audiodateien" at 800x600 / 200%. Guard against its return.
        scroll = window._workflow_pages["media"]
        if scroll.horizontalScrollBar().value() != 0:
            problems.append("Dateiseite horizontal verschoben")
        if scroll.widget().width() > scroll.viewport().width() + 3:
            problems.append(
                f"Dateiseite rechts abgeschnitten: Inhalt {scroll.widget().width()}px, "
                f"Sichtfläche {scroll.viewport().width()}px"
            )
        for header, _full, _short in getattr(window, "_source_header_labels", []):
            if header.isVisibleTo(window) and header.mapTo(window, header.rect().topLeft()).x() < 0:
                problems.append("Quellenüberschrift links abgeschnitten")
        if window.findChildren(QLabel, "title"):
            banner = window.findChildren(QLabel, "title")[0]
            if banner.height() > 44:
                problems.append(f"Programmkopf belegt zu viel Höhe: {banner.height()}px")
    if window.workflow_stack.height() < 60:
        problems.append(f"Arbeitsseite zu flach: {window.workflow_stack.height()}px")
    route = getattr(window, "_active_workflow_route", "")
    if route != "effects" and window.settings_view.isVisibleTo(window):
        problems.append("Ausgabeeinstellungen verdecken eine andere Arbeitsseite")
    if route == "queue" and int(window.view_scale.currentData() or 100) >= 175:
        if window._workflow_pages["queue"].verticalScrollBar().value() > 2:
            problems.append("Produktion zeigt beim Öffnen nicht den Anfang der Anleitung")
    if route == "media" and width <= 900 and int(window.view_scale.currentData() or 100) >= 175:
        remove_buttons = [
            button for button, full, _short in window._source_action_labels
            if full == "Entfernen" and button.isVisibleTo(window)
        ]
        if not remove_buttons or any(button.text() != "Entf." for button in remove_buttons):
            problems.append("Dateiauswahl: kurze sichtbare Entfernen-Beschriftung fehlt")
    if route == "effects":
        output_scroll = window._workflow_pages["effects"]
        if output_scroll.verticalScrollBar().value() > 2:
            problems.append("Ausgabeseite öffnet nicht bei den Grundeinstellungen")
        if not window.settings_view.isVisibleTo(window):
            problems.append("Grundlegende Ausgabeoptionen nicht erreichbar")
    tabs = window.main_tabs
    if not tabs.isVisible():
        problems.append("Dreistufige Hauptnavigation unsichtbar")
    for index in range(tabs.count()):
        actual = tabs.tabRect(index).width()
        needed = tabs.fontMetrics().horizontalAdvance(tabs.tabText(index)) + 14
        if actual + 2 < needed:
            problems.append(f"Register {index + 1} gekürzt: {actual}px statt {needed}px")
    for button in (*window.findChildren(QPushButton), *window.findChildren(QToolButton)):
        if not button.isVisibleTo(window) or not button.text().strip():
            continue
        if button.width() < 30 or button.height() < 25:
            problems.append(f"Schaltfläche zu klein: {button.text()[:40]!r}")
    return sorted(set(problems))


def run(output: Path) -> int:
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="videobatch-qt-matrix-") as temporary:
        isolated = Path(temporary)
        os.environ.update({
            "XDG_CONFIG_HOME": str(isolated / "config"),
            "XDG_STATE_HOME": str(isolated / "state"),
            "XDG_DATA_HOME": str(isolated / "data"),
            "XDG_CACHE_HOME": str(isolated / "cache"),
        })
        app = QApplication.instance() or QApplication([])
        app.setStyle("Fusion")
        window = VideoBatchQtPhase3Window(autoload_project=False)
        window.show()
        app.processEvents()
        results: list[dict[str, object]] = []
        try:
            for width, height in SIZES:
                for zoom in SCALES:
                    zoom_index = window.view_scale.findData(zoom)
                    if zoom_index < 0:
                        raise AssertionError(f"Unbekannte Schriftstufe {zoom}")
                    window.view_scale.setCurrentIndex(zoom_index)
                    window.resize(width, height)
                    app.processEvents()
                    for index, route in ROUTES:
                        window.main_tabs.setCurrentIndex(index)
                        app.processEvents()
                        image = output / f"{width}x{height}_{zoom:03d}_{route}.jpg"
                        issues = findings(window, width, height)
                        if not window.grab().save(str(image), "JPG", 83):
                            issues.append("Screenshot nicht gespeichert")
                        results.append({
                            "size": [width, height], "zoom": zoom,
                            "page": route, "image": image.name,
                            "status": "failed" if issues else "passed", "findings": issues,
                        })
        finally:
            window.close()
            app.processEvents()
    passed = all(record["status"] == "passed" for record in results)
    report = {
        "schema_version": 1,
        "scope": "Echte Qt-Fenstergeometrie und Bilddateien; keine manuelle Sichtabnahme",
        "cases": len(SIZES) * len(SCALES),
        "screenshots": len(results),
        "status": "passed" if passed else "failed",
        "results": results,
    }
    (output / "42_matrix_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"QT_MATRIX {report['status']}: {report['cases']} Kombinationen, {report['screenshots']} Bilder")
    for row in results:
        if row["findings"]:
            print(f"{row['image']}: {'; '.join(row['findings'])}")
    return 0 if passed else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    raise SystemExit(run(args.output))
