"""Projektübergreifender Einzeilenspeicher ohne frei wählbare Schreibziele."""
from __future__ import annotations

import fcntl
import os
import stat
import time
from datetime import datetime
from pathlib import Path

NOTE_FILENAME = "SCHNELLSPEICHER.txt"
MAX_NOTE_BYTES = 1024
MAX_FILE_BYTES = 8 * 1024 * 1024


def default_note_path() -> Path:
    """Im Quellprojekt ins Hauptverzeichnis, installiert in den lokalen App-Datenordner."""
    project = Path(__file__).resolve().parents[2]
    if all((project / name).is_file() for name in ("README.md", "AGENTS.md", "pyproject.toml")):
        return project / NOTE_FILENAME
    data = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share")
    if not data.is_absolute():
        data = Path.home() / ".local" / "share"
    return data / "provoware-video-automation" / NOTE_FILENAME


def append_quick_note(note: str, *, target: Path | None = None) -> Path:
    """Notiz exakt einmal am Dateiende anhängen, kein Löschen oder Ersetzen."""
    # Vor strip() prüfen: sonst verschwinden Zeilenumbrüche am Rand unbemerkt.
    if any(ord(ch) < 32 or 0x7F <= ord(ch) <= 0x9F or ch in "\u2028\u2029" for ch in note):
        raise ValueError("Bitte nur eine Zeile ohne Steuerzeichen eingeben.")
    clean = note.strip()
    if not clean or len(clean.encode("utf-8")) > MAX_NOTE_BYTES:
        raise ValueError("Bitte 1 bis 1.024 Byte Text eingeben.")

    path = target if target is not None else default_note_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink():
        raise ValueError("Notizdatei ist eine Verknüpfung und wird nicht beschrieben.")

    flags = os.O_WRONLY | os.O_APPEND | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags, 0o600)
    try:
        # Größenprüfung und Anhängen zwischen mehreren Programmfenstern atomar koordinieren.
        deadline = time.monotonic() + 2.0
        while True:
            try:
                fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    raise TimeoutError("Notizdatei ist gerade belegt; bitte erneut versuchen.")
                time.sleep(0.05)
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode):
            raise ValueError("Notizdatei ist keine normale Datei.")
        payload = (datetime.now().astimezone().isoformat(timespec="seconds") + " | " + clean + "\n").encode("utf-8")
        if info.st_size + len(payload) > MAX_FILE_BYTES:
            raise ValueError("Notizdatei ist voll (8 MiB). Bereits gespeicherte Notizen bleiben erhalten.")
        written = os.write(descriptor, payload)
        if written != len(payload):
            raise OSError("Notiz wurde nicht vollständig angehängt; bitte Datei prüfen.")
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    return path
