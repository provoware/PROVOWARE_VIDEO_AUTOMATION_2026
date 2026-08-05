from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .app_events import TypedEventPayload
from .models import MediaInfo


@dataclass(frozen=True, slots=True)
class SelectionPreviewReadyPayload(TypedEventPayload):
    _field_names = ("token", "path", "preview", "info", "size_bytes", "include_image")

    token: int
    path: Path
    preview: Path | None
    info: MediaInfo
    size_bytes: int
    include_image: bool

    def __post_init__(self) -> None:
        if self.token < 1:
            raise ValueError("Auswahlvorschau benötigt ein positives Token.")
        if self.size_bytes < 0:
            raise ValueError("Dateigröße der Auswahlvorschau darf nicht negativ sein.")
        if self.include_image and self.preview is None:
            raise ValueError("Bildvorschau benötigt einen Vorschaudateipfad.")
        if not self.include_image and self.preview is not None:
            raise ValueError("Audiovorschau darf keinen Bildvorschaupfad enthalten.")
        object.__setattr__(self, "path", Path(self.path))
        if self.preview is not None:
            object.__setattr__(self, "preview", Path(self.preview))


@dataclass(frozen=True, slots=True)
class SelectionPreviewFailedPayload(TypedEventPayload):
    _field_names = ("token", "path", "message", "include_image")

    token: int
    path: Path
    message: str
    include_image: bool

    def __post_init__(self) -> None:
        if self.token < 1:
            raise ValueError("Fehlgeschlagene Auswahlvorschau benötigt ein positives Token.")
        if not self.message.strip():
            raise ValueError("Fehlgeschlagene Auswahlvorschau benötigt eine Fehlermeldung.")
        object.__setattr__(self, "path", Path(self.path))
