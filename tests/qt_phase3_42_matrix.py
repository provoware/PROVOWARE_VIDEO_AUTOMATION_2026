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

from PySide6.QtWidgets import QApplication, QAbstractButton

from videobatch_fast.qt_phase3 import VideoBatchQtPhase3Window

SIZES = ((800, 600), (1024, 768), (1280, 720), (1366, 768), (1920, 1080), (2560, 1440))
SCALES = (80, 100, 110, 125, 150, 175, 200)
ROUTES = ((0, "01_dateien"), (1, "02_ausgabe"), (2, "03_produktion"))


def findings(window: VideoBatchQtPhase3Window, width: int, height: int) -> list[str]:
    problems: list[str] = []
    if (window.width(), window.height()) != (width, height):
        problems.append(f"Fenster {window.width()}x{window.height()} statt {width}x{height}")
    tabs = window.main_tabs
    if not tabs.isVisible():
        problems.append("Dreistufige Hauptnavigation unsichtbar")
    for index in range(tabs.count()):
        actual = tabs.tabRect(index).width()
        needed = tabs.fontMetrics().horizontalAdvance(tabs.tabText(index)) + 14
        if actual + 2 < needed:
            problems.append(f"Register {index + 1} gekürzt: {actual}px statt {needed}px")
    for button in window.findChildren(QAbstractButton):
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
