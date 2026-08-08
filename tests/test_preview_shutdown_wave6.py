from __future__ import annotations

import subprocess
from pathlib import Path

from videobatch_fast.preview_player import PreviewPlayer


class _Process:
    pid = 4242

    def __init__(self):
        self.wait_calls = 0

    def poll(self):
        return None

    def wait(self, timeout=None):
        self.wait_calls += 1
        if self.wait_calls == 1:
            raise subprocess.TimeoutExpired("ffplay", timeout)
        return -9


def test_preview_stop_reaps_process_after_forced_kill(monkeypatch) -> None:
    process = _Process()
    signals = []
    monkeypatch.setattr("videobatch_fast.preview_player.os.killpg", lambda pid, sig: signals.append((pid, sig)))
    player = PreviewPlayer()
    player.process = process
    player.source = Path("movie.mp4")
    player.stop()
    assert process.wait_calls == 2
    assert len(signals) == 2
    assert player.process is None
