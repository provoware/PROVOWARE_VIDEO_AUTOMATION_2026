from __future__ import annotations

import os
import random
import shutil
import signal
import subprocess
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(slots=True)
class Playlist:
    items: list[Path] = field(default_factory=list)
    current: int = -1
    repeat: str = "off"
    shuffle: bool = False

    def add(self, paths: list[Path]) -> None:
        for path in paths:
            path = Path(path)
            if path.is_file() and path not in self.items:
                self.items.append(path)
        if self.items and self.current < 0:
            self.current = 0

    def remove(self, indices: list[int]) -> None:
        for index in sorted(set(indices), reverse=True):
            if 0 <= index < len(self.items):
                del self.items[index]
        if not self.items:
            self.current = -1
        else:
            self.current = min(max(0, self.current), len(self.items) - 1)

    def next_index(self) -> int | None:
        if not self.items:
            return None
        if self.repeat == "one" and self.current >= 0:
            return self.current
        if self.shuffle and len(self.items) > 1:
            choices = [i for i in range(len(self.items)) if i != self.current]
            return random.choice(choices)
        candidate = self.current + 1
        if candidate < len(self.items):
            return candidate
        if self.repeat == "all":
            return 0
        return None


class AudioPlayer:
    def __init__(self) -> None:
        self.process: subprocess.Popen[bytes] | None = None
        self.paused = False

    @property
    def available(self) -> bool:
        return bool(shutil.which("ffplay"))

    def play(self, path: Path) -> None:
        self.stop()
        binary = shutil.which("ffplay")
        if not binary:
            raise RuntimeError("FFplay ist nicht installiert.")
        self.process = subprocess.Popen(
            [binary, "-nodisp", "-autoexit", "-loglevel", "error", str(path)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        self.paused = False

    def toggle_pause(self) -> bool:
        if not self.process or self.process.poll() is not None:
            return False
        signal_value = signal.SIGCONT if self.paused else signal.SIGSTOP
        os.killpg(self.process.pid, signal_value)
        self.paused = not self.paused
        return self.paused

    def stop(self) -> None:
        if self.process and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.process.kill()
        self.process = None
        self.paused = False
