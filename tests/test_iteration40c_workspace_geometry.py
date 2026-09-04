from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_workflow_refresh_never_reenters_global_idle_queue() -> None:
    source = (ROOT / "src/videobatch_fast/workflow_grid.py").read_text(encoding="utf-8")
    refresh = source.split("    def refresh(self) -> None:\n", 1)[1].split(
        "    def scroll_to_top", 1
    )[0]
    assert "update_idletasks" not in refresh
    assert "self._sync_width_and_rows()" in refresh
    assert "self._sync_scroll_region()" in refresh


def test_kpi_wrap_is_row_driven_not_card_configure_feedback() -> None:
    shell = (ROOT / "src/videobatch_fast/canonical_shell_chrome.py").read_text(
        encoding="utf-8"
    )
    compact = (ROOT / "src/videobatch_fast/canonical_kpi_compact_mixin.py").read_text(
        encoding="utf-8"
    )
    assert 'card.bind("<Configure>", self._update_shell_kpi_wraplengths' not in shell
    assert 'card.bind("<Configure>", self._compact_kpi_labels' not in compact
    assert "available_width=available, columns=columns" in shell
    assert "if current != target" in shell


def test_shell_navigation_resets_workflow_to_top_anchor() -> None:
    source = (ROOT / "src/videobatch_fast/canonical_shell_workspace.py").read_text(
        encoding="utf-8"
    )
    block = source.split("    def _select_shell_page", 1)[1].split(
        "    def _on_shell_tab_changed", 1
    )[0]
    assert '4: "production"' in block
    assert "self.root.after_idle(grid.scroll_to_top)" in block
