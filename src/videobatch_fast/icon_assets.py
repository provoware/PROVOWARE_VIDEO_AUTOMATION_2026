from __future__ import annotations

from pathlib import Path
from tkinter import PhotoImage, TclError
from typing import Any

_ICON_DIR = Path(__file__).resolve().parents[2] / "assets" / "icons" / "ui"


def load_ui_icon(owner: Any, name: str, *, size: int = 20) -> PhotoImage | None:
    """Load a packaged PNG icon once and keep a Tk-safe strong reference on owner."""
    cache = getattr(owner, "_ui_icon_cache", None)
    if cache is None:
        cache = {}
        setattr(owner, "_ui_icon_cache", cache)
    key = (str(name), int(size))
    if key in cache:
        return cache[key]
    path = _ICON_DIR / f"{name}-{int(size)}.png"
    if not path.is_file():
        cache[key] = None
        return None
    try:
        image = PhotoImage(master=owner.root, file=str(path))
    except TclError:
        image = None
    cache[key] = image
    return image
