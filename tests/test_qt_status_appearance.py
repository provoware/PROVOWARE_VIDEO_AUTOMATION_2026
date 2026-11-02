"""Real Qt regression checks for result persistence and appearance settings."""
from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")
from PySide6.QtCore import QCoreApplication, QEvent
from PySide6.QtWidgets import QApplication
from videobatch_fast.qt_phase3 import VideoBatchQtPhase3Window


@pytest.fixture
def window(tmp_path, monkeypatch):
    for name in ("CONFIG", "DATA", "STATE", "CACHE"):
        monkeypatch.setenv(f"XDG_{name}_HOME", str(tmp_path / name.lower()))
    monkeypatch.setattr(VideoBatchQtPhase3Window, "_refresh_media_index_async", lambda self: None)
    app = QApplication.instance() or QApplication([])
    app.setStyle("Fusion")
    view = VideoBatchQtPhase3Window(autoload_project=False)
    view.show()
    for _ in range(4):
        app.processEvents()
    yield view
    view._project_dirty = False
    view.close()
    view.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    app.processEvents()


@pytest.mark.parametrize("slideshow", [False, True])
@pytest.mark.parametrize("successes,failures,unprocessed,cancelled,status", [
    (1, 0, 0, False, "FERTIG"),
    (1, 1, 0, False, "FERTIG MIT HINWEIS"),
    (0, 1, 0, False, "FERTIG MIT HINWEIS"),
    (0, 0, 1, True, "ABGEBROCHEN"),
])
def test_completion_survives_refresh(window, slideshow, successes, failures, unprocessed, cancelled, status):
    if slideshow:
        window.slideshow.assignment.setCurrentIndex(1)
    window.table.setRowCount(1)
    window._finish_batch(dict(successes=successes, failures=failures,
                              unprocessed=unprocessed, cancelled=cancelled))
    expected_hint = window.next_step.text()
    for _ in range(2):
        window._refresh()
        QApplication.processEvents()
        assert window.status.text() == status
        assert window.next_step.text() == expected_hint
        assert window.table.rowCount() == 1
    assert f"{failures} Fehler" in expected_hint
    assert f"{unprocessed} offen" in expected_hint
    window.output.setText(str(window.output.text()) + "-neu")
    assert window._completion_status is None
    assert window.status.text() != status


def test_new_preparation_clears_completion(window):
    window._finish_batch(dict(successes=0, failures=1, unprocessed=0, cancelled=False))
    window._status("PRÜFT")
    assert window._completion_status is None
    assert window.status.property("state") == "busy"


def _contrast(first, second):
    def luminance(color):
        channels = [color.redF(), color.greenF(), color.blueF()]
        linear = [v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4 for v in channels]
        return sum(v * weight for v, weight in zip(linear, (.2126, .7152, .0722)))
    low, high = sorted((luminance(first), luminance(second)))
    return (high + .05) / (low + .05)


def test_real_theme_roles_and_synchronized_size(window):
    from PySide6.QtGui import QPalette
    from videobatch_fast.config import load_config
    for theme in ("neon_gravity", "acid_paper", "toxic_candy", "ultraviolet"):
        window.parity_theme.setCurrentIndex(window.parity_theme.findData(theme))
        for percent in (80, 120, 150, 200):
            window.parity_font_scale.setValue(percent)
            QApplication.processEvents()
            assert window.view_scale.currentData() == percent
            assert window.parity_font_scale.value() == percent
            assert abs(window.output.font().pointSizeF() - 12 * percent / 100) < .1
            assert load_config()["font_scale"] == percent
            assert load_config()["theme"] == theme
            assert not window.styleSheet()
        window.view_scale.setCurrentIndex(window.view_scale.findData(110))
        QApplication.processEvents()
        assert window.parity_font_scale.value() == 110
        palette = window.output.palette()
        assert _contrast(palette.color(QPalette.ColorRole.Text),
                         palette.color(QPalette.ColorRole.Base)) >= 4.5
        for status, state in (("BEREIT", "ready"), ("FEHLER", "error"),
                              ("FERTIG MIT HINWEIS", "warning"), ("UNBEKANNT", "unknown")):
            window._status(status)
            QApplication.processEvents()
            assert window.status.property("state") == state
        assert window.start.palette().color(QPalette.ColorRole.Button).name() == "#ffbf3f"
    window.parity_font_scale.setValue(200)
    assert load_config()["font_scale"] == 200


def test_saved_large_size_is_restored(window):
    window.parity_font_scale.setValue(200)
    window.parity_theme.setCurrentIndex(window.parity_theme.findData("acid_paper"))
    restored = VideoBatchQtPhase3Window(autoload_project=False)
    try:
        for _ in range(4):
            QApplication.processEvents()
        assert restored.view_scale.currentData() == 200
        assert restored.parity_font_scale.value() == 200
        assert restored.parity_theme.currentData() == "acid_paper"
    finally:
        restored._project_dirty = False
        restored.close()
        restored.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)


def test_preparation_cancel_and_start_error_remain_visible(window):
    window.preparing = True
    window._cancel()
    window._refresh()
    assert window.status.text() == "ABGEBROCHEN"
    assert "Vorbereitung abgebrochen" in window.next_step.text()
    window._show_start_error("Datei fehlt", "Vorbereitung")
    window._refresh()
    assert window.status.text() == "FEHLER"
    assert "Nächster Schritt" in window.next_step.text()


def test_completion_is_restored_after_worker_exits(window):
    from types import SimpleNamespace
    alive = [True]
    window.runner._thread = SimpleNamespace(is_alive=lambda: alive[0])
    try:
        window._finish_batch(dict(successes=0, failures=1, unprocessed=0, cancelled=False))
        alive[0] = False
        window._poll()
        assert window.status.text() == "FERTIG MIT HINWEIS"
        assert "1 Fehler" in window.next_step.text()
    finally:
        window.runner._thread = None


def test_resize_reflows_long_status_after_zoom(window):
    from PySide6.QtWidgets import QLabel
    window.resize(1366, 768)
    window.parity_font_scale.setValue(200)
    window.resize(800, 600)
    for status in ("FERTIG MIT HINWEIS", "ABGEBROCHEN", "UNBEKANNT"):
        window._status(status)
        for _ in range(5):
            QApplication.processEvents()
        title = window.findChild(QLabel, "title")
        assert title.text() == "VideoBatch"
        assert title.width() >= title.fontMetrics().horizontalAdvance(title.text())
        assert window.status.width() >= window.status.fontMetrics().horizontalAdvance(max(status.split(), key=len))
    window.resize(1366, 768)
    QApplication.processEvents()
    assert window.findChild(QLabel, "title").text() == "VideoBatch 2026"

def test_slideshow_start_readiness_after_completion(window, tmp_path):
    """A finished slideshow must not leave the 1:1 start gate disabled."""
    import wave
    from PySide6.QtGui import QImage

    audio = tmp_path / "ton.wav"
    with wave.open(str(audio), "wb") as stream:
        stream.setnchannels(1)
        stream.setsampwidth(1)
        stream.setframerate(8000)
        stream.writeframes(bytes([128]) * 8000)
    images = []
    for number in (1, 2):
        path = tmp_path / f"bild-{number}.png"
        image = QImage(2, 2, QImage.Format.Format_RGB32)
        image.fill(0xff336699)
        assert image.save(str(path))
        images.append(path)

    window.audio.add_paths([audio])
    window.media.add_paths(images)
    window.output.setText(str(tmp_path))
    window.slideshow.assignment.setCurrentIndex(1)
    window._refresh()
    assert window.start.isEnabled()
    assert window.kpi_values["jobs"].text() == "1"

    window.table.setRowCount(1)
    window._finish_batch(dict(successes=1, failures=0,
                              unprocessed=0, cancelled=False))
    completion_hint = window.next_step.text()
    for _ in range(2):
        window._refresh()
        QApplication.processEvents()
        assert window.start.isEnabled()
        assert window.step_start.text() == "3 · Start bereit"
        assert window.kpi_values["jobs"].text() == "1"
        assert window.status.text() == "FERTIG"
        assert window.next_step.text() == completion_hint
        assert window.table.rowCount() == 1
