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


def _build_media_snapshot(
    *,
    audio_count: int,
    media_count: int,
    image_count: int | None,
    video_count: int | None,
    missing_sources: int,
    active_tasks: Iterable[str],
    missing_source_names: Iterable[str],
) -> KpiSnapshot:
    total_media = max(0, int(audio_count)) + max(0, int(media_count))
    missing_count = max(0, int(missing_sources))
    if _task_matches(active_tasks, "preview", "probe", "scan", "media", "slideshow"):
        return KpiSnapshot(
            str(total_media), "Quellen werden geprüft", "Prüfung läuft", "loading",
            action_enabled=False,
            cause="Eine Medienanalyse, Vorschau oder Ordnerprüfung ist noch aktiv.",
            action_label="Prüfung läuft", recovery_action="disabled",
        )
    if total_media == 0:
        return KpiSnapshot(
            "0", "Noch keine Quellen importiert", "Leer", "empty",
            cause="Das Projekt enthält weder Audio- noch Bild- oder Videoquellen.",
            action_label="Medien öffnen", recovery_action="open_media",
        )
    if missing_count:
        names = _source_names(missing_source_names)
        name_note = f" Betroffen: {', '.join(names)}." if names else ""
        return KpiSnapshot(
            str(total_media), f"{missing_count} Quelle(n) nicht erreichbar",
            "Wiederherstellung nötig", "error",
            cause=("Gespeicherte Projektpfade zeigen auf Dateien, die am ursprünglichen Ort nicht mehr vorhanden sind." + name_note),
            action_label="Fehlende entfernen", recovery_action="remove_missing_sources",
        )
    if audio_count == 0 or media_count == 0:
        audio_missing = audio_count == 0
        return KpiSnapshot(
            str(total_media), "Audio fehlt" if audio_missing else "Bild oder Video fehlt",
            "Unvollständig", "warning",
            cause=("Für eine gültige Zuordnung fehlt mindestens eine Audiodatei." if audio_missing else "Für eine gültige Zuordnung fehlt mindestens ein Bild oder Video."),
            action_label="Audio importieren" if audio_missing else "Medien importieren",
            recovery_action="import_audio" if audio_missing else "import_media",
        )
    detail = (
        f"{max(0, int(image_count))} Bilder · {max(0, int(video_count))} Videos · {audio_count} Audio"
        if image_count is not None and video_count is not None
        else f"{audio_count} Audio · {media_count} Medien"
    )
    return KpiSnapshot(str(total_media), detail, "Bereit", "success", action_label="Medien öffnen", recovery_action="open_media")


def _build_queue_snapshot(
    *,
    job_count: int, completed_jobs: int, failed_jobs: int, active_tasks: Iterable[str],
    queue_failure_reasons: Iterable[str], retryable_jobs: int, blocked_jobs: int,
) -> KpiSnapshot:
    retryable_count = max(0, int(retryable_jobs))
    blocked_count = max(0, int(blocked_jobs))
    if _task_matches(active_tasks, "batch", "render", "encode", "production"):
        return KpiSnapshot(
            str(job_count), "Produktion arbeitet", "Läuft", "loading",
            action_enabled=False, cause="Mindestens ein Render-, Encode- oder Batchauftrag ist noch aktiv.",
            action_label="Produktion läuft", recovery_action="disabled",
        )
    if failed_jobs or retryable_count or blocked_count:
        failed_total = max(int(failed_jobs), retryable_count + blocked_count)
        details = []
        if retryable_count:
            details.append(f"{retryable_count} wiederanlaufbar")
        if blocked_count:
            details.append(f"{blocked_count} gesperrt")
        detail = " · ".join(details) or f"{failed_total} Auftrag/Aufträge fehlgeschlagen"
        return KpiSnapshot(
            str(job_count), detail, "Wiederherstellung nötig", "error",
            cause=_first_reason(queue_failure_reasons, "Mindestens ein Auftrag wurde mit einem Fehler beendet; Originaldateien bleiben unverändert."),
            action_label="Wiederanlauf laden" if retryable_count else "Fehlerliste öffnen",
            recovery_action="reload_retry_queue" if retryable_count else "open_retry_queue",
        )
    if completed_jobs:
        waiting_jobs = max(0, int(job_count) - int(completed_jobs))
        return KpiSnapshot(
            str(job_count), f"{waiting_jobs} wartend · {completed_jobs} abgeschlossen",
            "Abgeschlossen", "success", action_label="Queue öffnen", recovery_action="open_queue",
        )
    if job_count:
        return KpiSnapshot(str(job_count), "Aufträge sind vorbereitet", "Startbereit", "ready", action_label="Queue öffnen", recovery_action="open_queue")
    return KpiSnapshot(
        "0", "Noch keine gültige Zuordnung", "Leer", "empty",
        cause="Audio und Medien sind noch nicht zu ausführbaren Aufträgen kombiniert.",
        action_label="Zuordnung öffnen", recovery_action="open_media",
    )


def _build_effects_snapshot(
    *, visual_effect: str, transition: str, quick_mode: str, effect_valid: bool, transition_valid: bool,
) -> KpiSnapshot:
    effect = str(visual_effect or "none")
    transition_value = str(transition or "none")
    mode = str(quick_mode or "smart_auto")
    if not effect_valid or not transition_valid:
        invalid = []
        if not effect_valid:
            invalid.append(f"Effekt „{effect}“")
        if not transition_valid:
            invalid.append(f"Übergang „{transition_value}“")
        return KpiSnapshot(
            "Ungültig", "Gestaltungsvertrag weicht ab", "Wiederherstellung nötig", "error",
            cause=f"{' und '.join(invalid)} ist nicht im aktuellen Effektregister enthalten.",
            action_label="Automatik herstellen", recovery_action="reset_effects",
        )
    if effect != "none" or transition_value != "none":
        value = effect if effect != "none" else transition_value
        return KpiSnapshot(
            value, f"Effekt: {effect} · Übergang: {transition_value}", "Aktiv", "success",
            action_label="Effekte öffnen", recovery_action="open_effects",
        )
    if mode not in {"custom", "smart_auto"}:
        return KpiSnapshot(
            mode, "Schnellmodus steuert die Gestaltung", "Modus aktiv", "ready",
            action_label="Effekte öffnen", recovery_action="open_effects",
        )
    return KpiSnapshot(
        "Automatik", "Noch kein fester Look gewählt", "Neutral", "empty",
        action_label="Effekte öffnen", recovery_action="open_effects",
    )




def _build_scheduler_snapshot(*, scheduler_ready: bool, scheduler_status: str = "", scheduler_when: str = "") -> KpiSnapshot:
    status = str(scheduler_status or "").strip().lower()
    when = str(scheduler_when or "").replace("T", " ")[:16]
    if status == "running":
        return KpiSnapshot(
            "Läuft", f"Geplanter Lauf aktiv · {when or 'jetzt'}", "Aktiv", "loading",
            action_enabled=True, cause="Der systemd-Benutzertimer hat den eingefrorenen Renderplan gestartet.",
            action_label="Zeitplan öffnen", recovery_action="open_scheduler",
        )
    if status == "pending":
        return KpiSnapshot(
            "Geplant", f"Start: {when or '–'}", "Bereit", "ready",
            action_enabled=True, cause="Projekt- und Quellzustand sind bis zum Start fingerprintgebunden.",
            action_label="Zeitplan öffnen", recovery_action="open_scheduler",
        )
    if status in {"failed", "blocked", "missed"}:
        label = {"failed": "Fehler", "blocked": "Blockiert", "missed": "Verpasst"}[status]
        return KpiSnapshot(
            label, "Letzte Planung benötigt Prüfung", "Prüfen", "warning",
            action_enabled=True, cause="Der letzte geplante Lauf wurde nicht erfolgreich automatisch ausgeführt.",
            action_label="Zeitplan prüfen", recovery_action="open_scheduler",
        )
    if scheduler_ready:
        return KpiSnapshot(
            "Nicht geplant", "Lokale Startzeituhr ist verfügbar", "Bereit", "ready",
            action_enabled=True, cause="systemd --user und Medienwerkzeuge sind verfügbar.",
            action_label="Startzeit planen", recovery_action="open_scheduler",
        )
    return KpiSnapshot(
        "Nicht verfügbar", "Systemvoraussetzungen fehlen", "Deaktiviert", "disabled",
        action_enabled=False, cause="systemd --user oder ein benötigtes Medienwerkzeug ist nicht verfügbar.",
        action_label="Nicht verfügbar", recovery_action="disabled",
    )

def build_kpi_snapshots(
    *,
    audio_count: int, media_count: int, image_count: int | None = None, video_count: int | None = None,
    missing_sources: int, job_count: int, completed_jobs: int, failed_jobs: int,
    active_tasks: Iterable[str], visual_effect: str, transition: str, quick_mode: str,
    missing_source_names: Iterable[str] = (), queue_failure_reasons: Iterable[str] = (),
    retryable_jobs: int = 0, blocked_jobs: int = 0, effect_valid: bool = True, transition_valid: bool = True,
    scheduler_ready: bool = False, scheduler_status: str = "", scheduler_when: str = "",
) -> dict[str, KpiSnapshot]:
    media = _build_media_snapshot(
        audio_count=audio_count, media_count=media_count, image_count=image_count, video_count=video_count,
        missing_sources=missing_sources, active_tasks=active_tasks, missing_source_names=missing_source_names,
    )
    queue = _build_queue_snapshot(
        job_count=job_count, completed_jobs=completed_jobs, failed_jobs=failed_jobs, active_tasks=active_tasks,
        queue_failure_reasons=queue_failure_reasons, retryable_jobs=retryable_jobs, blocked_jobs=blocked_jobs,
    )
    effects = _build_effects_snapshot(
        visual_effect=visual_effect, transition=transition, quick_mode=quick_mode,
        effect_valid=effect_valid, transition_valid=transition_valid,
    )
    scheduler = _build_scheduler_snapshot(
        scheduler_ready=scheduler_ready, scheduler_status=scheduler_status, scheduler_when=scheduler_when
    )
    return {"media": media, "queue": queue, "effects": effects, "scheduler": scheduler}
