from __future__ import annotations

from pathlib import Path

from videobatch_fast.media_tags import add_tag, normalize_media_tags, remove_tag, tags_for
from videobatch_fast.project_state import normalize_project_state


def test_media_tags_are_normalized_and_persisted_in_project_state(tmp_path: Path) -> None:
    media = tmp_path / "Bild 01.png"
    state = normalize_project_state({
        "media_paths": [str(media)],
        "media_tags": {str(media.absolute()): [" Favorit ", "favorit", " Szene 1 "]},
    })
    assert state["media_tags"][str(media.absolute())] == ["Favorit", "Szene 1"]


def test_media_tag_mutation_is_case_insensitive_and_path_stable(tmp_path: Path) -> None:
    media = tmp_path / "clip.mp4"
    mapping: dict[str, list[str]] = {}
    assert add_tag(mapping, [media], " Review ") is True
    assert add_tag(mapping, [media], "review") is False
    assert tags_for(mapping, media) == ("Review",)
    assert remove_tag(mapping, [media], "REVIEW") is True
    assert tags_for(mapping, media) == ()


def test_invalid_tag_mapping_is_discarded() -> None:
    assert normalize_media_tags({"a": "not-a-list", "": ["x"]}) == {}
