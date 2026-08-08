from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / "scripts" / "capture_visual_scenarios.py").read_text(encoding="utf-8")


def test_visual_runner_uses_bounded_tk_event_pump() -> None:
    assert "def _pump_tk_events" in SOURCE
    capture = SOURCE.split("def capture_scenario", 1)[1].split("def main", 1)[0]
    assert "root.update_idletasks()" not in capture
    assert "root.update()" not in capture
    assert "capture_widget.update_idletasks()" not in capture
    assert "capture_widget.update()" not in capture
    assert "_pump_tk_events(root" in capture


def test_visual_runner_rejects_undersized_capture_display() -> None:
    assert "Testanzeige zu klein für einen belastbaren Screenshot" in SOURCE
    assert "2560x1440x24" in SOURCE
