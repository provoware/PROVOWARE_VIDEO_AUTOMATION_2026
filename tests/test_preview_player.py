from __future__ import annotations

from pathlib import Path

import pytest

from videobatch_fast.preview_player import PreviewPlayer, PreviewPlayerError


class FakeProcess:
    def __init__(self) -> None:
        self.pid = 4321
        self._poll = None

    def poll(self):
        return self._poll

    def wait(self, timeout=None):
        self._poll = 0
        return 0


def test_preview_player_uses_ffplay_and_supports_restart_seek(monkeypatch, tmp_path: Path) -> None:
    media = tmp_path / "clip.mp4"
    media.write_bytes(b"video")
    commands = []
    process = FakeProcess()

    monkeypatch.setattr("videobatch_fast.preview_player.shutil.which", lambda name: "/usr/bin/ffplay" if name == "ffplay" else None)
    monkeypatch.setattr("videobatch_fast.preview_player.subprocess.Popen", lambda command, **kwargs: commands.append(command) or process)
    monkeypatch.setattr("videobatch_fast.preview_player.os.killpg", lambda *_args: None)

    player = PreviewPlayer()
    player.play(media, start_seconds=4.5)
    assert commands[-1][-1] == str(media)
    assert "-ss" in commands[-1]
    player.seek(9.0)
    assert commands[-1][commands[-1].index("-ss") + 1] == "9.000"


def test_preview_player_rejects_missing_source(tmp_path: Path) -> None:
    player = PreviewPlayer()
    with pytest.raises(PreviewPlayerError):
        player.play(tmp_path / "missing.mp4")
