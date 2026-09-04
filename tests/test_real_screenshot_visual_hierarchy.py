from __future__ import annotations

import json
from pathlib import Path

from videobatch_fast.theme import contrast_ratio

ROOT = Path(__file__).resolve().parents[1]


def _violet() -> dict:
    return json.loads((ROOT / "resources/themes/toxic_candy.json").read_text(encoding="utf-8"))


def test_violet_pulse_uses_canonical_navy_foundation() -> None:
    theme = _violet()
    colors = theme["colors"]
    assert theme["name"] == theme["label"] == "Violet Pulse"
    assert colors["background_main"] == "#061426"
    assert colors["background_toolbar"] == "#07172A"
    assert colors["action_primary"] == "#6C52D8"
    assert colors["border_subtle"] != colors["status_information"]
    assert colors["state_selected"] != colors["status_information"]


def test_violet_pulse_core_contrast_is_wcag_aa() -> None:
    colors = _violet()["colors"]
    assert contrast_ratio(colors["background_surface"], colors["text_primary"]) >= 4.5
    assert contrast_ratio(colors["background_elevated"], colors["text_secondary"]) >= 4.5
    assert contrast_ratio(colors["action_primary"], colors["action_primary_text"]) >= 4.5


def test_theme_reserves_bright_color_for_focus_and_selection_semantics() -> None:
    source = (ROOT / "src/videobatch_fast/theme.py").read_text(encoding="utf-8")
    assert 'QuickModeSelected.TButton", background=COLORS["selection"]' in source
    assert 'TEntry", fieldbackground=COLORS["panel2"]' in source
    assert 'bordercolor=COLORS["border_subtle"]' in source
    assert 'background=[("selected", COLORS["selection"])' in source


def test_canonical_shell_uses_subtle_container_borders() -> None:
    source = (ROOT / "src/videobatch_fast/canonical_shell_chrome.py").read_text(encoding="utf-8")
    assert source.count('bordercolor=COLORS["border_subtle"]') >= 4
    assert '"ShellActionBar.TFrame"' in source
    assert 'style="ShellActionBar.TFrame"' in source


def test_kpi_diagnostics_are_preserved_but_visually_compacted() -> None:
    source = (ROOT / "src/videobatch_fast/canonical_kpi_detail_mixin.py").read_text(encoding="utf-8")
    assert '_shell_kpi_cause_vars' in source
    assert '_shell_kpi_updated_vars' in source
    assert '_shell_kpi_meta_vars' in source
    assert 'style="ShellKpiMeta.TLabel"' in source
    assert 'snapshot.state in {"warning", "error"}' in source


def test_sidebar_focus_does_not_look_like_second_active_page() -> None:
    source = (ROOT / "src/videobatch_fast/canonical_shell_chrome.py").read_text(encoding="utf-8")
    assert '("focus", COLORS["toolbar"])' in source
    assert '("focus", COLORS["selection"])' in source


def test_redundant_disabled_scheduler_is_not_in_primary_action_strip() -> None:
    source = (ROOT / "src/videobatch_fast/canonical_shell_chrome.py").read_text(encoding="utf-8")
    action_block = source.split("actions: tuple", 1)[1].split("self._shell_action_buttons", 1)[0]
    assert "Startzeituhr · Checkpoint 5" not in action_block
    assert action_block.count("TButton") == 6


def test_settings_shortcut_is_not_rendered_as_second_active_nav_item() -> None:
    source = (ROOT / "src/videobatch_fast/canonical_shell_workspace.py").read_text(encoding="utf-8")
    assert 'item.action not in {"disabled", "settings"}' in source


def test_wide_action_strip_prefers_single_row_for_six_primary_actions() -> None:
    source = (ROOT / "src/videobatch_fast/canonical_shell_chrome.py").read_text(encoding="utf-8")
    assert 'available >= 1380 and len(buttons) <= 6' in source
    assert 'columns = len(buttons)' in source
