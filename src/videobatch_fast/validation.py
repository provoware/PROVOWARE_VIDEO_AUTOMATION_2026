from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path

from .storage_validation import _validate_storage
from .resource_estimation import estimate_required_by_filesystem
from .models import BatchOptions, PairJob
from .command_builder import PROFILES
from .effects import TRANSITIONS, VISUAL_EFFECTS
from .ffmpeg_capabilities import encoder_smoke_test, read_ffmpeg_capabilities, required_filter_names
from .probe import ffmpeg_path, ffprobe_path, sampled_audio_peak
from .quick_modes import QUICK_MODES, processing_options_for_job, validate_quick_modes


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    code: str
    title: str
    message: str
    solution: str
    blocking: bool = True
    actions: tuple[str, ...] = ()


def validate_runtime(*, startup: bool = False) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    mode_errors = validate_quick_modes(VISUAL_EFFECTS, TRANSITIONS, PROFILES)
    for message in mode_errors:
        issues.append(ValidationIssue(
            "QUICK_MODE_INVALID",
            "Schnellmodus ist unvollständig",
            message,
            "Installiere das vollständige geprüfte Programmpaket.",
            blocking=not startup,
        ))
    ffmpeg = ffmpeg_path()
    ffprobe = ffprobe_path()
    if not ffmpeg:
        issues.append(ValidationIssue(
            "FFMPEG_MISSING", "FFmpeg fehlt", "FFmpeg wurde nicht gefunden.",
            "Die Oberfläche bleibt nutzbar; Videoerstellung wird bis zur automatischen Reparatur deaktiviert.",
            blocking=not startup,
            actions=("retry_runtime", "open_install_help", "open_logs"),
        ))
    if not ffprobe:
        issues.append(ValidationIssue(
            "FFPROBE_MISSING", "FFprobe fehlt", "FFprobe wurde nicht gefunden.",
            "Die Oberfläche bleibt nutzbar; Medienprüfung wird bis zur automatischen Reparatur deaktiviert.",
            blocking=not startup,
            actions=("retry_runtime", "open_install_help", "open_logs"),
        ))
    if ffmpeg:
        capabilities = read_ffmpeg_capabilities(ffmpeg)
        if capabilities.error:
            issues.append(ValidationIssue(
                "FFMPEG_CAPABILITIES_UNKNOWN",
                "FFmpeg-Fähigkeiten konnten nicht gelesen werden",
                capabilities.error,
                "VideoBatch prüft die benötigten Funktionen beim konkreten Renderauftrag erneut.",
                blocking=False if startup else True,
            ))
        aac_ok, aac_detail = encoder_smoke_test(ffmpeg, "aac", "audio")
        if not aac_ok:
            issues.append(ValidationIssue(
                "FFMPEG_AAC_MISSING",
                "AAC-Ausgabe ist nicht verfügbar",
                aac_detail or "Der reale AAC-Kurztest ist fehlgeschlagen.",
                "Die Oberfläche bleibt nutzbar; Audioausgabe wird bis zur Reparatur blockiert.",
                blocking=not startup,
                actions=("retry_runtime", "open_install_help", "open_logs"),
            ))
    return issues


def validate_output_dir(directory: Path) -> list[ValidationIssue]:
    directory = Path(directory).expanduser()
    issues: list[ValidationIssue] = []
    try:
        directory.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        return [ValidationIssue(
            "OUTPUT_CREATE_FAILED",
            "Ausgabeordner nicht verfügbar",
            str(exc),
            "VideoBatch kann einen sicheren Benutzerordner erstellen oder einen anderen Ordner verwenden.",
            actions=("create_output_folder", "choose_output", "use_safe_output", "retry_validation"),
        )]
    if not directory.is_dir():
        issues.append(ValidationIssue(
            "OUTPUT_NOT_DIRECTORY",
            "Ungültiges Ziel",
            "Der Zielpfad ist kein Ordner.",
            "Erstelle einen sicheren Ausgabeordner oder wähle einen vorhandenen Ordner.",
            actions=("create_output_folder", "choose_output", "use_safe_output"),
        ))
    elif not os.access(directory, os.W_OK | os.X_OK):
        issues.append(ValidationIssue(
            "OUTPUT_PERMISSION",
            "Keine Schreibberechtigung",
            "Der Ausgabeordner ist nicht beschreibbar.",
            "VideoBatch kann einen neuen beschreibbaren Ordner im Benutzerbereich anlegen.",
            actions=("create_output_folder", "choose_output", "use_safe_output", "retry_validation"),
        ))
    return issues


def validate_pairs(
    jobs: list[PairJob], options: BatchOptions, *, audio_peak_limit: int = 0
) -> list[ValidationIssue]:
    issues = validate_runtime() + validate_output_dir(options.output_dir)
    if options.quick_mode not in QUICK_MODES:
        issues.append(ValidationIssue(
            "QUICK_MODE_UNKNOWN",
            "Unbekannter Schnellmodus",
            str(options.quick_mode),
            "VideoBatch kann die empfohlene Automatik wiederherstellen.",
            actions=("repair_settings", "retry_validation"),
        ))
    if not jobs:
        solution = (
            "Füge Audios und Bilder hinzu. Im Diashowmodus werden automatisch alle Bilder auf jedes Audio verteilt."
            if options.assignment_mode == "all_images_each_audio"
            else "Füge gleich viele Audios und Bilder oder Videos hinzu."
        )
        issues.append(ValidationIssue(
            "NO_JOBS",
            "Keine gültigen Produktionsaufträge",
            "Es wurden noch keine verwendbaren Audio-/Medienaufträge gebildet.",
            solution,
            actions=("add_audio", "add_media", "switch_to_slideshow", "focus_file_lists"),
        ))
        return issues
    issues.extend(_validate_capabilities(options))
    checked_directories: set[Path] = {Path(options.output_dir).expanduser()}
    peak_checked: set[Path] = set()
    flash_notice = False
    for job in jobs:
        selected = processing_options_for_job(job, options)
        if selected.visual_effect == "strobe_safe" and not flash_notice:
            issues.append(ValidationIssue(
                "FLASHING_EFFECT", "Hinweis zu Lichtimpulsen",
                "Der gewählte Effekt enthält schnelle Helligkeitswechsel.",
                "Bei Lichtempfindlichkeit einen anderen Bildeffekt wählen. "
                "Die eingebaute Begrenzung ersetzt keine individuelle Prüfung.",
                blocking=False,
            ))
            flash_notice = True
        if job.media_info.kind == "video" and job.media_info.variable_frame_rate:
            issues.append(ValidationIssue(
                "VIDEO_FRAME_RATE_MAY_VARY", "Bildrate kontrollieren",
                f"{job.media.name}: FFprobe meldet abweichende Bildraten.",
                "Die Zeitgenauigkeit im Ergebnis kontrollieren; bei Bedarf "
                "Video neu codieren. Dies ist ein Verdacht, kein Defektnachweis.",
                blocking=False,
            ))
        if audio_peak_limit > 0 and job.audio not in peak_checked and job.audio.is_file():
            if len(peak_checked) < audio_peak_limit:
                peak_checked.add(job.audio)
                peak = sampled_audio_peak(job.audio)
                if peak is not None and peak >= -0.5:
                    issues.append(ValidationIssue(
                        "AUDIO_NEAR_PEAK", "Audiopegel prüfen",
                        f"{job.audio.name}: In den ersten 6 Sekunden liegt der "
                        f"Spitzenpegel bei {peak:.1f} dB.",
                        "Die Originaldatei bleibt unverändert. Bei hörbaren "
                        "Verzerrungen die Audioquelle prüfen.",
                        blocking=False,
                    ))
        parent = job.output.parent
        if parent not in checked_directories:
            issues.extend(validate_output_dir(parent))
            checked_directories.add(parent)
        if not job.audio.is_file():
            issues.append(ValidationIssue(
                "AUDIO_MISSING", "Audiodatei fehlt", job.audio.name,
                "Entferne den Eintrag oder wähle eine neue Audiodatei.",
                actions=("add_audio", "remove_missing", "focus_file_lists"),
            ))
        if not job.media.is_file():
            issues.append(ValidationIssue(
                "MEDIA_MISSING", "Mediendatei fehlt", job.media.name,
                "Entferne den Eintrag oder wähle neue Medien.",
                actions=("add_media", "remove_missing", "focus_file_lists"),
            ))
        for slide in job.media_sequence:
            if not slide.is_file():
                issues.append(ValidationIssue("SLIDESHOW_IMAGE_MISSING", "Diashow-Bild fehlt", slide.name, "Entferne die Datei oder wähle den Bildordner erneut."))
        if job.audio_info.kind != "audio":
            issues.append(ValidationIssue("AUDIO_INVALID", "Audio nicht lesbar", job.audio.name, "Verwende eine gültige Audiodatei."))
        if job.media_info.kind not in {"image", "video"}:
            issues.append(ValidationIssue("MEDIA_INVALID", "Medium nicht lesbar", job.media.name, "Verwende ein unterstütztes Bild oder Video."))
        if job.is_slideshow and not job.audio_info.duration:
            issues.append(ValidationIssue(
                "SLIDESHOW_DURATION_UNKNOWN",
                "Audiodauer ist für die Diashow nicht lesbar",
                job.audio.name,
                "Wähle eine lesbare Audiodatei; VideoBatch berechnet danach alle Bildzeiten automatisch.",
            ))
        if job.is_slideshow and len(job.media_sequence) > 250:
            issues.append(ValidationIssue(
                "SLIDESHOW_TOO_MANY_IMAGES",
                "Zu viele Bilder für einen einzelnen Diashow-Auftrag",
                f"{len(job.media_sequence)} Bilder ausgewählt.",
                "Teile die Bildmenge in kleinere Projekte mit höchstens 250 Bildern.",
            ))

    issues.extend(_validate_storage(jobs, options, estimate_required_by_filesystem))
    return issues


def _validate_capabilities(options: BatchOptions) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    capabilities = read_ffmpeg_capabilities(ffmpeg_path()) if ffmpeg_path() else None
    if capabilities and not capabilities.error:
        codec_ok = options.codec in capabilities.encoders
        if not codec_ok and ffmpeg_path():
            codec_ok, _detail = encoder_smoke_test(ffmpeg_path(), options.codec, "video")
        if not codec_ok:
            issues.append(ValidationIssue(
                "FFMPEG_VIDEO_ENCODER_MISSING",
                "Gewählter Video-Encoder fehlt",
                f"Der FFmpeg-Build kann {options.codec} nicht verwenden.",
                "Wähle einen verfügbaren Encoder oder installiere den vollständigen FFmpeg-Build.",
            ))
        required_filters = required_filter_names(options.visual_effect, options.transition)
        if options.assignment_mode == "all_images_each_audio":
            required_filters |= {"scale", "pad", "fps", "trim", "setpts"}
            required_filters.add("xfade" if options.slideshow_transition != "none" else "concat")
        missing_filters = required_filters - set(capabilities.filters)
        if missing_filters:
            issues.append(ValidationIssue(
                "FFMPEG_FILTER_MISSING",
                "Benötigter Video-Filter fehlt",
                ", ".join(sorted(missing_filters)),
                "Wähle einen einfacheren Look oder installiere den vollständigen FFmpeg-Build.",
            ))
    return issues
