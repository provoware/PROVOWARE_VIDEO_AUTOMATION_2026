from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / "src/videobatch_fast/canonical_ui.py").read_text(encoding="utf-8")


def test_ready_handshake_does_not_block_on_update_idletasks() -> None:
    block = SOURCE.split("CanonicalVideoBatchFastUI(root)", 1)[1].split("root.mainloop()", 1)[0]
    assert "root.update_idletasks()" not in block
    assert "signal_ui_ready" in block
    assert '"first_idle_flush": 0.0' in block
