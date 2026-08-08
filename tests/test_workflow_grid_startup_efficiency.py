from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / "src/videobatch_fast/workflow_grid.py").read_text(encoding="utf-8")


def test_card_creation_coalesces_geometry_refreshes() -> None:
    add_card = SOURCE.split("def add_card", 1)[1].split("def set_layout_mode", 1)[0]
    assert "schedule_refresh()" in add_card
    assert "update_idletasks" not in add_card


def test_workflow_refresh_does_not_enter_nested_idle_loop() -> None:
    refresh = SOURCE.split("def refresh", 1)[1].split("def scroll_to_widget", 1)[0]
    assert "update_idletasks" not in refresh
    assert "_sync_width_and_rows" in refresh
    assert "_sync_scroll_region" in refresh


def test_explicit_scroll_can_resolve_geometry_once() -> None:
    scroll = SOURCE.split("def scroll_to_widget", 1)[1].split("def _configure_columns", 1)[0]
    assert "update_idletasks" in scroll
