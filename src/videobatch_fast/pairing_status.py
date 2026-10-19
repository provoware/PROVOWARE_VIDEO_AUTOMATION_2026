"""Shared beginner-facing preflight for simple one-audio/one-media jobs.

The actual media probe remains the responsibility of build_jobs()/FFprobe.
This module never opens or changes original media.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PairingStatus:
    audio_count: int
    media_count: int
    output_chosen: bool

    @property
    def pairs_complete(self) -> bool:
        return self.audio_count > 0 and self.audio_count == self.media_count

    @property
    def ready(self) -> bool:
        return self.pairs_complete and self.output_chosen

    @property
    def missing_audio(self) -> int:
        return max(0, self.media_count - self.audio_count)

    @property
    def missing_media(self) -> int:
        return max(0, self.audio_count - self.media_count)

    @property
    def explanation(self) -> str:
        if not self.audio_count and not self.media_count:
            return "Bitte mindestens eine Audiodatei und ein Bild oder Video hinzufügen."
        if not self.audio_count:
            return f"Es fehlen {self.missing_audio} Audiodatei(en) zu den ausgewählten Medien."
        if not self.media_count:
            return f"Es fehlen {self.missing_media} Bilder oder Videos."
        if self.missing_media:
            return f"{self.missing_media} Bild(er) oder Video(s) fehlen noch."
        if self.missing_audio:
            return f"{self.missing_audio} Audiodatei(en) fehlen noch."
        if not self.output_chosen:
            return "Bitte einen Ausgabeordner oben auswählen."
        return f"Bereit für {self.audio_count} Video(s). Dateipaare vor dem Start prüfen."


def pairing_status(audio_count: int, media_count: int, output: str = "") -> PairingStatus:
    if audio_count < 0 or media_count < 0:
        raise ValueError("Dateianzahlen dürfen nicht negativ sein")
    return PairingStatus(audio_count, media_count, bool(output.strip()))
