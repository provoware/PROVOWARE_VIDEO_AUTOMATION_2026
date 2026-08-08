from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_kpi_wraplength_only_changes_when_target_differs() -> None:
    source = (ROOT / "src/videobatch_fast/canonical_shell_chrome.py").read_text(encoding="utf-8")
    method = source.split("def _update_shell_kpi_wraplengths", 1)[1].split("def _refresh_kpi_cards", 1)[0]
    assert 'label.cget("wraplength")' in method
    assert "if current != target" in method


def test_dashboard_wraplength_only_changes_when_target_differs() -> None:
    source = (ROOT / "src/videobatch_fast/canonical_dashboard_mixin.py").read_text(encoding="utf-8")
    method = source.split("def _update_dashboard_wraplengths", 1)[1].split("def _refresh_canonical_dashboard", 1)[0]
    assert 'label.cget("wraplength")' in method
    assert "if current != width" in method
