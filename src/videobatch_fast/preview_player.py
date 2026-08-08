from __future__ import annotations

import os
import shutil
import signal
import subprocess
import time
from pathlib import Path


class PreviewPlayerError(RuntimeError):
    pass


class PreviewPlayer:
    """Small ffplay-backed preview transport with pause and restart-based seek."""

    def __init__(self) -> None:
        self.process: subprocess.Popen[bytes] | None = None
        self.source: Path | None = None
        self.offset_seconds = 0.0
        self.started_at = 0.0
        self.paused_at = 0.0
        self.paused_total = 0.0
        self.paused = False

    @property
    def available(self) -> bool:
        return bool(shutil.which("ffplay"))

    @property
    def running(self) -> bool:
        return bool(self.process and self.process.poll() is None)

    @property
    def position_seconds(self) -> float:
        if not self.running:
            return max(0.0, self.offset_seconds)
        now = self.paused_at if self.paused else time.monotonic()
        elapsed = max(0.0, now - self.started_at - self.paused_total)
        return max(0.0, self.offset_seconds + elapsed)

    def play(self, source: Path, *, start_seconds: float = 0.0) -> None:
        path = Path(source)
        if not path.is_file():
            raise PreviewPlayerError("Die Vorschauquelle ist nicht erreichbar.")
        binary = shutil.which("ffplay")
        if not binary:
            raise PreviewPlayerError("FFplay ist nicht verfügbar.")
        self.stop()
        offset = max(0.0, float(start_seconds))
        command = [binary, "-autoexit", "-loglevel", "error"]
        if offset > 0.05:
            command += ["-ss", f"{offset:.3f}"]
        command.append(str(path))
        try:
            self.process = subprocess.Popen(
                command,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
        except OSError as exc:
            self.process = None
            raise PreviewPlayerError("Die Videovorschau konnte nicht gestartet werden.") from exc
        self.source = path
        self.offset_seconds = offset
        self.started_at = time.monotonic()
        self.paused_at = 0.0
        self.paused_total = 0.0
        self.paused = False

    def toggle_pause(self) -> bool:
        if not self.running or self.process is None:
            return False
        try:
            if self.paused:
                os.killpg(self.process.pid, signal.SIGCONT)
                if self.paused_at:
                    self.paused_total += max(0.0, time.monotonic() - self.paused_at)
                self.paused_at = 0.0
                self.paused = False
            else:
                os.killpg(self.process.pid, signal.SIGSTOP)
                self.paused_at = time.monotonic()
                self.paused = True
        except OSError as exc:
            raise PreviewPlayerError("Die Vorschau konnte nicht pausiert oder fortgesetzt werden.") from exc
        return self.paused

    def seek(self, seconds: float) -> None:
        source = self.source
        if source is None:
            raise PreviewPlayerError("Es ist keine Videovorschau aktiv.")
        self.play(source, start_seconds=max(0.0, float(seconds)))

    def stop(self) -> None:
        process = self.process
        if process is not None and process.poll() is None:
            try:
                os.killpg(process.pid, signal.SIGTERM)
                process.wait(timeout=2.0)
            except (OSError, subprocess.TimeoutExpired):
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except OSError:
                    pass
                try:
                    process.wait(timeout=0.5)
                except (OSError, subprocess.TimeoutExpired):
                    pass
        self.process = None
        self.paused = False
        self.paused_at = 0.0
