from __future__ import annotations

import json
from pathlib import Path

from scripts.validate_design_manifest import EXPECTED_FONT_PROFILES, EXPECTED_THEMES, validate

ROOT = Path(__file__).resolve().parents[1]


def test_design_manifest_contract_is_complete() -> None:
    assert validate(ROOT) == []


def test_design_tokens_keep_canonical_theme_and_font_contract() -> None:
    tokens = json.loads((ROOT / "docs/design/VIDEOBATCH_DESIGN_TOKENS.json").read_text(encoding="utf-8"))
    assert {key: value["label"] for key, value in tokens["themes"].items()} == EXPECTED_THEMES
    assert tokens["font_profiles"] == EXPECTED_FONT_PROFILES


def test_design_references_are_vector_and_offline() -> None:
    for name in ("VIDEOBATCH_CANONICAL_UI_REFERENCE.svg", "VIDEOBATCH_GRAPHICS_MANIFEST_POSTER.svg"):
        content = (ROOT / "docs/design" / name).read_text(encoding="utf-8")
        assert content.startswith("<svg")
        assert "<rect" in content
        assert "<text" in content
        assert 'href="http' not in content
        assert 'href="https' not in content
