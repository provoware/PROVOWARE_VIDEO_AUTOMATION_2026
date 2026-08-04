from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .probe import classify_extension, probe_media

SORT_KEYS = {
    "import": "Importreihenfolge",
    "name_asc": "Name · aufsteigend",
    "name_desc": "Name · absteigend",
    "size_asc": "Größe · klein zuerst",
    "size_desc": "Größe · groß zuerst",
    "modified_new": "Änderungsdatum · neu zuerst",
    "modified_old": "Änderungsdatum · alt zuerst",
    "created_new": "Erstellzeit · neu zuerst",
    "created_old": "Erstellzeit · alt zuerst",
    "duration_short": "Dauer · kurz zuerst",
    "duration_long": "Dauer · lang zuerst",
    "type": "Dateityp",
}


@dataclass(frozen=True, slots=True)
class LibraryItem:
    path: Path
    import_index: int
    size: int
    modified: float
    created: float | None
    duration: float | None
    kind: str
    available: bool


def item_for(path: Path, index: int) -> LibraryItem:
    path = Path(path)
    try:
        stat = path.stat()
    except OSError:
        return LibraryItem(path, index, 0, 0.0, None, None, classify_extension(path), False)
    info = probe_media(path)
    created = getattr(stat, "st_birthtime", None)
    return LibraryItem(path, index, stat.st_size, stat.st_mtime, float(created) if created else None, info.duration, info.kind, True)


def sort_paths(paths: Iterable[Path], key: str) -> list[Path]:
    items = [item_for(Path(path), index) for index, path in enumerate(paths)]
    if key == "name_asc":
        items.sort(key=lambda i: (not i.available, i.path.name.casefold(), i.import_index))
    elif key == "name_desc":
        items.sort(key=lambda i: (i.path.name.casefold(), -i.import_index), reverse=True)
        items.sort(key=lambda i: not i.available)
    elif key == "size_asc":
        items.sort(key=lambda i: (not i.available, i.size, i.import_index))
    elif key == "size_desc":
        items.sort(key=lambda i: (not i.available, -i.size, i.import_index))
    elif key == "modified_new":
        items.sort(key=lambda i: (not i.available, -i.modified, i.import_index))
    elif key == "modified_old":
        items.sort(key=lambda i: (not i.available, i.modified, i.import_index))
    elif key == "created_new":
        items.sort(key=lambda i: (not i.available, -(i.created if i.created is not None else i.modified), i.import_index))
    elif key == "created_old":
        items.sort(key=lambda i: (not i.available, (i.created if i.created is not None else i.modified), i.import_index))
    elif key == "duration_short":
        items.sort(key=lambda i: (not i.available, i.duration is None, i.duration or 0, i.import_index))
    elif key == "duration_long":
        items.sort(key=lambda i: (not i.available, i.duration is None, -(i.duration or 0), i.import_index))
    elif key == "type":
        items.sort(key=lambda i: (not i.available, i.kind, i.path.suffix.casefold(), i.path.name.casefold(), i.import_index))
    else:
        items.sort(key=lambda i: i.import_index)
    return [item.path for item in items]
