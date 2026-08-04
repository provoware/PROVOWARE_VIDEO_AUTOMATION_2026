from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

VERSION_FILE = Path(__file__).resolve().parents[2] / "VERSION.json"


@lru_cache(maxsize=1)
def version_info() -> dict:
    try:
        data = json.loads(VERSION_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def app_version() -> str:
    return str(version_info().get("version", "0.0.0"))


def build_label() -> str:
    return str(version_info().get("build", app_version()))
