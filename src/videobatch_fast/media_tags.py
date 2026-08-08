from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Iterable

MAX_TAGS_PER_MEDIA = 20
MAX_TAG_LENGTH = 32
_TAG_WS = re.compile(r"\s+")


def normalize_tag(value: object) -> str:
    """Return a compact human tag or an empty string for unusable input."""
    text = _TAG_WS.sub(" ", str(value or "").strip())
    text = "".join(char for char in text if char.isprintable() and char not in "\r\n\t")
    return text[:MAX_TAG_LENGTH].strip()


def normalize_media_tags(raw: Any) -> dict[str, list[str]]:
    """Normalize the persisted path -> tags mapping without touching the filesystem."""
    if not isinstance(raw, dict):
        return {}
    normalized: dict[str, list[str]] = {}
    for raw_path, raw_tags in raw.items():
        path = str(raw_path or "").strip()
        if not path or not isinstance(raw_tags, (list, tuple, set)):
            continue
        tags: list[str] = []
        seen: set[str] = set()
        for value in raw_tags:
            tag = normalize_tag(value)
            key = tag.casefold()
            if not tag or key in seen:
                continue
            seen.add(key)
            tags.append(tag)
            if len(tags) >= MAX_TAGS_PER_MEDIA:
                break
        if tags:
            normalized[path] = tags
    return normalized


def path_key(path: Path | str) -> str:
    """Stable project-local key; resolve only lexically and never require path existence."""
    return str(Path(path).expanduser().absolute())


def tags_for(mapping: dict[str, list[str]], path: Path | str) -> tuple[str, ...]:
    return tuple(mapping.get(path_key(path), ()))


def add_tag(mapping: dict[str, list[str]], paths: Iterable[Path | str], tag: str) -> bool:
    tag = normalize_tag(tag)
    if not tag:
        return False
    changed = False
    for path in paths:
        key = path_key(path)
        existing = list(mapping.get(key, ()))
        if any(item.casefold() == tag.casefold() for item in existing):
            continue
        if len(existing) >= MAX_TAGS_PER_MEDIA:
            continue
        existing.append(tag)
        mapping[key] = existing
        changed = True
    return changed


def remove_tag(mapping: dict[str, list[str]], paths: Iterable[Path | str], tag: str | None = None) -> bool:
    wanted = normalize_tag(tag).casefold() if tag else ""
    changed = False
    for path in paths:
        key = path_key(path)
        existing = list(mapping.get(key, ()))
        if not existing:
            continue
        if not wanted:
            mapping.pop(key, None)
            changed = True
            continue
        filtered = [item for item in existing if item.casefold() != wanted]
        if filtered == existing:
            continue
        changed = True
        if filtered:
            mapping[key] = filtered
        else:
            mapping.pop(key, None)
    return changed
