from __future__ import annotations

import json
from pathlib import Path

from videobatch_fast.canonical_shell_contract import CANONICAL_THEME_LABELS
from videobatch_fast.theme import THEME_LABELS, contrast_ratio

ROOT = Path(__file__).resolve().parents[1]
THEME_PATH = ROOT / "resources" / "themes" / "neon_gravity.json"
REFERENCE_PATH = ROOT / "docs" / "design" / "VIDEOBATCH_CANONICAL_UI_REFERENCE.svg"


def _theme() -> dict:
    return json.loads(THEME_PATH.read_text(encoding="utf-8"))


def test_public_theme_labels_match_canonical_contract() -> None:
    assert THEME_LABELS == CANONICAL_THEME_LABELS
    assert THEME_LABELS["neon_gravity"] == "Midnight Blue"


def test_midnight_blue_resource_uses_public_product_name() -> None:
    theme = _theme()
    assert theme["name"] == "Midnight Blue"
    assert theme["label"] == "Midnight Blue"


def test_midnight_blue_core_palette_is_present_in_canonical_svg() -> None:
    colors = _theme()["colors"]
    reference = REFERENCE_PATH.read_text(encoding="utf-8").lower()
    required_keys = (
        "background_main",
        "background_surface",
        "background_elevated",
        "background_toolbar",
        "text_primary",
        "text_muted",
        "border_subtle",
        "action_primary",
        "status_success",
        "state_selected",
        "state_hover",
    )
    missing = {
        key: colors[key]
        for key in required_keys
        if colors[key].lower() not in reference
    }
    assert missing == {}


def test_midnight_blue_primary_text_contrast_is_wcag_aa() -> None:
    colors = _theme()["colors"]
    assert contrast_ratio(colors["background_main"], colors["text_primary"]) >= 4.5
    assert contrast_ratio(colors["background_surface"], colors["text_primary"]) >= 4.5
    assert contrast_ratio(colors["background_elevated"], colors["text_primary"]) >= 4.5
    assert contrast_ratio(colors["action_primary"], colors["action_primary_text"]) >= 4.5


def test_midnight_blue_statuses_remain_semantically_distinct() -> None:
    colors = _theme()["colors"]
    semantic = {
        colors["status_success"],
        colors["status_information"],
        colors["status_warning"],
        colors["status_error"],
        colors["status_active"],
    }
    assert len(semantic) == 5


def test_reference_palette_keeps_four_layperson_action_colors() -> None:
    colors = _theme()["colors"]
    tiles = {
        colors["tile_gold"],
        colors["tile_magenta"],
        colors["tile_green"],
        colors["tile_blue"],
    }
    assert len(tiles) == 4
