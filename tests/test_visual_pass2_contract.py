from __future__ import annotations

import inspect
from pathlib import Path

from videobatch_fast.canonical_visual_polish_mixin import (
    CanonicalVisualPolishMixin,
    VISUAL_PASS2_CARD_PADDING,
    VISUAL_PASS2_GAP,
    VISUAL_PASS2_HALF_GAP,
)

ROOT = Path(__file__).resolve().parents[1]


def test_visual_pass2_uses_consistent_8_12_spacing_contract() -> None:
    assert VISUAL_PASS2_GAP == 8
    assert VISUAL_PASS2_HALF_GAP == 4
    assert VISUAL_PASS2_CARD_PADDING == 12


def test_visual_pass2_is_presentation_only() -> None:
    source = inspect.getsource(CanonicalVisualPolishMixin)
    forbidden = (
        "write_text(",
        "write_bytes(",
        "unlink(",
        "remove(",
        "rename(",
        "replace(",
        "self.audios =",
        "self.media =",
        "self.jobs =",
        "self._start(",
        "self._cancel(",
    )
    for token in forbidden:
        assert token not in source


def test_visual_pass2_makes_queue_primary_without_new_widget_actions() -> None:
    source = inspect.getsource(CanonicalVisualPolishMixin)
    assert 'queue.configure(style="ShellPrimaryCard.TFrame")' in source
    assert 'style="ShellActionBar.TFrame"' in source
    assert 'ShellKpiMedia.TFrame' in source
    assert 'bordercolor=COLORS["border_subtle"]' in source
    assert "command=" not in source


def test_visual_pass2_keeps_responsive_layout_delegated_to_existing_shell() -> None:
    source = inspect.getsource(CanonicalVisualPolishMixin)
    assert "super()._layout_shell_kpis" in source
    assert "super()._layout_shell_actions" in source
    assert "super()._layout_canonical_dashboard" in source
    assert 'mode == "three_columns"' in source
    assert 'mode == "two_columns"' in source
    assert 'mode == "stacked"' in source


def test_canonical_ui_activates_visual_polish_before_shell_mixins() -> None:
    source = (ROOT / "src/videobatch_fast/canonical_ui.py").read_text(encoding="utf-8")
    assert "from .canonical_visual_polish_mixin import CanonicalVisualPolishMixin" in source
    class_header = source.split("class CanonicalVideoBatchFastUI(", 1)[1].split("):", 1)[0]
    assert "CanonicalVisualPolishMixin" in class_header
    assert class_header.index("CanonicalVisualPolishMixin") < class_header.index("CanonicalWindowMixin")
