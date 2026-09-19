from __future__ import annotations

from collections.abc import Callable
from typing import Any

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

ComboFactory = Callable[[QWidget, list[tuple[str, str]], str], QComboBox]
WindowCallback = Callable[[object], None]


def build_playlist_tab(
    window: Any,
    *,
    combo_factory: ComboFactory,
    save_project: WindowCallback,
    save_settings: WindowCallback,
) -> QWidget:
    tab = QWidget()
    layout = QVBoxLayout(tab)
    intro = QLabel(
        "Audio direkt vorhören. Die Wiedergabe nutzt weiterhin den vorhandenen FFplay-basierten Player."
    )
    intro.setWordWrap(True)
    layout.addWidget(intro)
    window.parity_playlist_list = QListWidget()
    layout.addWidget(window.parity_playlist_list, 1)

    row = QHBoxLayout()
    add = QPushButton("Audios übernehmen")
    remove = QPushButton("Aus Liste entfernen")
    play = QPushButton("▶ Abspielen")
    pause = QPushButton("⏯ Pause/Fortsetzen")
    stop = QPushButton("■ Stop")
    for button in (add, remove, play, pause, stop):
        row.addWidget(button)
    layout.addLayout(row)

    options = QHBoxLayout()
    options.addWidget(QLabel("Wiederholen"))
    window.parity_repeat = combo_factory(
        tab,
        [("Aus", "off"), ("Aktuelles Audio", "one"), ("Alle", "all")],
        str(window._parity_config.get("playlist_repeat", "off")),
    )
    window.parity_shuffle = QCheckBox("Zufällige Reihenfolge")
    window.parity_shuffle.setChecked(bool(window._parity_config.get("playlist_shuffle", False)))
    options.addWidget(window.parity_repeat)
    options.addWidget(window.parity_shuffle)
    options.addStretch()
    layout.addLayout(options)

    window.parity_playlist_status = QLabel("Noch keine Wiedergabe.")
    window.parity_playlist_status.setWordWrap(True)
    layout.addWidget(window.parity_playlist_status)

    add.clicked.connect(lambda: add_from_sources(window, save_project=save_project))
    remove.clicked.connect(lambda: remove_selected(window, save_project=save_project))
    play.clicked.connect(lambda: play_selected(window))
    pause.clicked.connect(lambda: toggle_pause(window))
    stop.clicked.connect(lambda: stop_playback(window))
    window.parity_repeat.currentIndexChanged.connect(
        lambda *_: apply_playlist_options(window, save_settings=save_settings)
    )
    window.parity_shuffle.toggled.connect(
        lambda *_: apply_playlist_options(window, save_settings=save_settings)
    )
    return tab


def refresh_playlist_list(window: Any) -> None:
    selected = window.parity_playlist.current
    window.parity_playlist_list.clear()
    for index, path in enumerate(window.parity_playlist.items):
        window.parity_playlist_list.addItem(f"{index + 1:02d} · {path.name}")
    if 0 <= selected < window.parity_playlist_list.count():
        window.parity_playlist_list.setCurrentRow(selected)


def add_from_sources(window: Any, *, save_project: WindowCallback) -> None:
    window.parity_playlist.add(window.audio.paths())
    refresh_playlist_list(window)
    save_project(window)


def remove_selected(window: Any, *, save_project: WindowCallback) -> None:
    rows = [window.parity_playlist_list.row(item) for item in window.parity_playlist_list.selectedItems()]
    window.parity_playlist.remove(rows)
    refresh_playlist_list(window)
    save_project(window)


def apply_playlist_options(window: Any, *, save_settings: WindowCallback) -> None:
    window.parity_playlist.repeat = str(window.parity_repeat.currentData() or "off")
    window.parity_playlist.shuffle = window.parity_shuffle.isChecked()
    save_settings(window)


def play_selected(window: Any) -> None:
    row = window.parity_playlist_list.currentRow()
    if row >= 0:
        window.parity_playlist.current = row
    if window.parity_playlist.current < 0 and window.parity_playlist.items:
        window.parity_playlist.current = 0
    if window.parity_playlist.current < 0:
        window.parity_playlist_status.setText("Noch kein Audio in der Playlist.")
        return
    path = window.parity_playlist.items[window.parity_playlist.current]
    try:
        window.parity_audio_player.play(path)
    except Exception as exc:
        QMessageBox.warning(window, "Audio konnte nicht gestartet werden", str(exc))
        return
    window.parity_playlist_status.setText(f"Spielt: {path.name}")
    refresh_playlist_list(window)


def toggle_pause(window: Any) -> None:
    try:
        paused = window.parity_audio_player.toggle_pause()
    except OSError as exc:
        QMessageBox.warning(window, "Pause fehlgeschlagen", str(exc))
        return
    window.parity_playlist_status.setText("Pausiert" if paused else "Wiedergabe läuft")


def stop_playback(window: Any) -> None:
    window.parity_audio_player.stop()
    window.parity_playlist_status.setText("Wiedergabe gestoppt.")


def poll_playlist(window: Any) -> None:
    player = getattr(window, "parity_audio_player", None)
    playlist = getattr(window, "parity_playlist", None)
    if player is None or playlist is None:
        return
    process = player.process
    if process is not None and process.poll() is not None:
        player.process = None
        next_index = playlist.next_index()
        if next_index is None:
            window.parity_playlist_status.setText("Wiedergabe beendet.")
        else:
            playlist.current = next_index
            play_selected(window)
