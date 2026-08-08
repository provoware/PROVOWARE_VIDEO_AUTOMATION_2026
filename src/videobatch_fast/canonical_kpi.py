from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Literal

KpiState = Literal["empty", "ready", "loading", "success", "warning", "error", "disabled"]
KPI_STATES: tuple[KpiState, ...] = (
    "empty",
    "ready",
    "loading",
    "success",
    "warning",
    "error",
    "disabled",
)


@dataclass(frozen=True, slots=True)
class KpiSnapshot:
    value: str
    detail: str
    status: str
    state: KpiState
    action_enabled: bool = True
    cause: str = ""
    action_label: str = "Bereich öffnen"
    recovery_action: str = "open"


def _task_matches(active_tasks: Iterable[str], *fragments: str) -> bool:
    lowered = tuple(str(name).casefold() for name in active_tasks)
    return any(fragment in name for name in lowered for fragment in fragments)


def _first_reason(values: Iterable[str], fallback: str) -> str:
    for value in values:
        normalized = " ".join(str(value).strip().split())
        if normalized:
            return normalized[:280]
    return fallback


def _source_names(values: Iterable[str]) -> tuple[str, ...]:
    names: list[str] = []
    for value in values:
        name = str(value).strip()
        if name and name not in names:
            names.append(name)
        if len(names) == 3:
            break
    return tuple(names)


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
    missing_source_names: Iterable[str] = (),
    queue_failure_reasons: Iterable[str] = (),
    retryable_jobs: int = 0,
    blocked_jobs: int = 0,
    effect_valid: bool = True,
    transition_valid: bool = True,
) -> dict[str, KpiSnapshot]:
    total_media = max(0, int(audio_count)) + max(0, int(media_count))
    missing_count = max(0, int(missing_sources))
    retryable_count = max(0, int(retryable_jobs))
    blocked_count = max(0, int(blocked_jobs))
    media_loading = _task_matches(active_tasks, "preview", "probe", "scan", "media", "slideshow")
    production_active = _task_matches(active_tasks, "batch", "render", "encode", "production")

    if media_loading:
        media = KpiSnapshot(
            str(total_media),
            "Quellen werden geprüft",
            "Prüfung läuft",
            "loading",
            action_enabled=False,
            cause="Eine Medienanalyse, Vorschau oder Ordnerprüfung ist noch aktiv.",
            action_label="Prüfung läuft",
            recovery_action="disabled",
        )
    elif total_media == 0:
        media = KpiSnapshot(
            "0",
            "Noch keine Quellen importiert",
            "Leer",
            "empty",
            cause="Das Projekt enthält weder Audio- noch Bild- oder Videoquellen.",
            action_label="Medien öffnen",
            recovery_action="open_media",
        )
    elif missing_count:
        names = _source_names(missing_source_names)
        name_note = f" Betroffen: {', '.join(names)}." if names else ""
        media = KpiSnapshot(
            str(total_media),
            f"{missing_count} Quelle(n) nicht erreichbar",
            "Wiederherstellung nötig",
            "error",
            cause=(
                "Gespeicherte Projektpfade zeigen auf Dateien, die am ursprünglichen Ort nicht mehr vorhanden sind."
                + name_note
            ),
            action_label="Fehlende entfernen",
            recovery_action="remove_missing_sources",
        )
    elif audio_count == 0 or media_count == 0:
        missing_kind = "Audio fehlt" if audio_count == 0 else "Bild oder Video fehlt"
        media = KpiSnapshot(
            str(total_media),
            missing_kind,
            "Unvollständig",
            "warning",
            cause=(
                "Für eine gültige Zuordnung fehlt mindestens eine Audiodatei."
                if audio_count == 0
                else "Für eine gültige Zuordnung fehlt mindestens ein Bild oder Video."
            ),
            action_label="Audio importieren" if audio_count == 0 else "Medien importieren",
            recovery_action="import_audio" if audio_count == 0 else "import_media",
        )
    else:
        media = KpiSnapshot(
            str(total_media),
            f"{audio_count} Audio · {media_count} Medien",
            "Bereit",
            "success",
            action_label="Medien öffnen",
            recovery_action="open_media",
        )

    if production_active:
        queue = KpiSnapshot(
            str(job_count),
            "Produktion arbeitet",
            "Läuft",
            "loading",
            action_enabled=False,
            cause="Mindestens ein Render-, Encode- oder Batchauftrag ist noch aktiv.",
            action_label="Produktion läuft",
            recovery_action="disabled",
        )
    elif failed_jobs or retryable_count or blocked_count:
        failed_total = max(int(failed_jobs), retryable_count + blocked_count)
        recovery_detail = []
        if retryable_count:
            recovery_detail.append(f"{retryable_count} wiederanlaufbar")
        if blocked_count:
            recovery_detail.append(f"{blocked_count} gesperrt")
        detail = " · ".join(recovery_detail) or f"{failed_total} Auftrag/Aufträge fehlgeschlagen"
        queue = KpiSnapshot(
            str(job_count),
            detail,
            "Wiederherstellung nötig",
            "error",
            cause=_first_reason(
                queue_failure_reasons,
                "Mindestens ein Auftrag wurde mit einem Fehler beendet; Originaldateien bleiben unverändert.",
            ),
            action_label="Wiederanlauf laden" if retryable_count else "Fehlerliste öffnen",
            recovery_action="reload_retry_queue" if retryable_count else "open_retry_queue",
        )
    elif completed_jobs:
        queue = KpiSnapshot(
            str(job_count),
            f"{completed_jobs} Auftrag/Aufträge abgeschlossen",
            "Abgeschlossen",
            "success",
            action_label="Queue öffnen",
            recovery_action="open_queue",
        )
    elif job_count:
        queue = KpiSnapshot(
            str(job_count),
            "Aufträge sind vorbereitet",
            "Startbereit",
            "ready",
            action_label="Queue öffnen",
            recovery_action="open_queue",
        )
    else:
        queue = KpiSnapshot(
            "0",
            "Noch keine gültige Zuordnung",
            "Leer",
            "empty",
            cause="Audio und Medien sind noch nicht zu ausführbaren Aufträgen kombiniert.",
            action_label="Zuordnung öffnen",
            recovery_action="open_queue",
        )

    effect = str(visual_effect or "none")
    transition_value = str(transition or "none")
    mode = str(quick_mode or "smart_auto")
    if not effect_valid or not transition_valid:
        invalid = []
        if not effect_valid:
            invalid.append(f"Effekt „{effect}“")
        if not transition_valid:
            invalid.append(f"Übergang „{transition_value}“")
        effects = KpiSnapshot(
            "Ungültig",
            "Gestaltungsvertrag weicht ab",
            "Wiederherstellung nötig",
            "error",
            cause=f"{' und '.join(invalid)} ist nicht im aktuellen Effektregister enthalten.",
            action_label="Automatik herstellen",
            recovery_action="reset_effects",
        )
    elif effect != "none" or transition_value != "none":
        value = effect if effect != "none" else transition_value
        detail = f"Effekt: {effect} · Übergang: {transition_value}"
        effects = KpiSnapshot(
            value,
            detail,
            "Aktiv",
            "success",
            action_label="Effekte öffnen",
            recovery_action="open_effects",
        )
    elif mode not in {"custom", "smart_auto"}:
        effects = KpiSnapshot(
            mode,
            "Schnellmodus steuert die Gestaltung",
            "Modus aktiv",
            "ready",
            action_label="Effekte öffnen",
            recovery_action="open_effects",
        )
    else:
        effects = KpiSnapshot(
            "Automatik",
            "Noch kein fester Look gewählt",
            "Neutral",
            "empty",
            action_label="Effekte öffnen",
            recovery_action="open_effects",
        )

    scheduler = KpiSnapshot(
        "Nicht geplant",
        "Produktive Startplanung folgt in Checkpoint 5",
        "Deaktiviert",
        "disabled",
        action_enabled=False,
        cause="Die Startzeituhr ist absichtlich noch nicht freigegeben und startet keine Aufträge.",
        action_label="Checkpoint 5",
        recovery_action="disabled",
    )
    return {
        "media": media,
        "queue": queue,
        "effects": effects,
        "scheduler": scheduler,
    }
