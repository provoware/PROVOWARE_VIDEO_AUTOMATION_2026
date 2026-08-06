from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Literal

KpiState = Literal["empty", "ready", "loading", "success", "warning", "error", "disabled"]


@dataclass(frozen=True, slots=True)
class KpiSnapshot:
    value: str
    detail: str
    status: str
    state: KpiState
    action_enabled: bool = True


def _task_matches(active_tasks: Iterable[str], *fragments: str) -> bool:
    lowered = tuple(str(name).casefold() for name in active_tasks)
    return any(fragment in name for name in lowered for fragment in fragments)


def build_kpi_snapshots(
    *,
    audio_count: int,
    media_count: int,
    missing_sources: int,
    job_count: int,
    completed_jobs: int,
    failed_jobs: int,
    active_tasks: Iterable[str],
    visual_effect: str,
    transition: str,
    quick_mode: str,
) -> dict[str, KpiSnapshot]:
    total_media = max(0, int(audio_count)) + max(0, int(media_count))
    media_loading = _task_matches(active_tasks, "preview", "probe", "scan", "media", "slideshow")
    production_active = _task_matches(active_tasks, "batch", "render", "encode", "production")

    if media_loading:
        media = KpiSnapshot(str(total_media), "Quellen werden geprüft", "Prüfung läuft", "loading")
    elif total_media == 0:
        media = KpiSnapshot("0", "Noch keine Quellen importiert", "Leer", "empty")
    elif missing_sources:
        media = KpiSnapshot(
            str(total_media),
            f"{missing_sources} Quelle(n) nicht erreichbar",
            "Fehler prüfen",
            "error",
        )
    elif audio_count == 0 or media_count == 0:
        missing_kind = "Audio fehlt" if audio_count == 0 else "Bild oder Video fehlt"
        media = KpiSnapshot(str(total_media), missing_kind, "Unvollständig", "warning")
    else:
        media = KpiSnapshot(
            str(total_media),
            f"{audio_count} Audio · {media_count} Medien",
            "Bereit",
            "success",
        )

    if production_active:
        queue = KpiSnapshot(str(job_count), "Produktion arbeitet", "Läuft", "loading")
    elif failed_jobs:
        queue = KpiSnapshot(str(job_count), f"{failed_jobs} Auftrag/Aufträge fehlgeschlagen", "Fehler", "error")
    elif completed_jobs:
        queue = KpiSnapshot(str(job_count), f"{completed_jobs} Auftrag/Aufträge abgeschlossen", "Abgeschlossen", "success")
    elif job_count:
        queue = KpiSnapshot(str(job_count), "Aufträge sind vorbereitet", "Startbereit", "ready")
    else:
        queue = KpiSnapshot("0", "Noch keine gültige Zuordnung", "Leer", "empty")

    effect = str(visual_effect or "none")
    transition_value = str(transition or "none")
    mode = str(quick_mode or "smart_auto")
    if effect != "none" or transition_value != "none":
        value = effect if effect != "none" else transition_value
        detail = f"Effekt: {effect} · Übergang: {transition_value}"
        effects = KpiSnapshot(value, detail, "Aktiv", "success")
    elif mode not in {"custom", "smart_auto"}:
        effects = KpiSnapshot(mode, "Schnellmodus steuert die Gestaltung", "Modus aktiv", "ready")
    else:
        effects = KpiSnapshot("Automatik", "Noch kein fester Look gewählt", "Neutral", "empty")

    scheduler = KpiSnapshot(
        "Nicht geplant",
        "Produktive Startplanung folgt in Checkpoint 5",
        "Deaktiviert",
        "disabled",
        action_enabled=False,
    )
    return {
        "media": media,
        "queue": queue,
        "effects": effects,
        "scheduler": scheduler,
    }
