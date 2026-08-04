from __future__ import annotations

from pathlib import Path

from .effects import effect_filter, transition_filters
from .models import BatchOptions, EncodeProfile, PairJob
from .probe import ffmpeg_path
from .quick_modes import processing_options_for_job

PROFILES: dict[str, EncodeProfile] = {
    "turbo": EncodeProfile("turbo", "Turbo", "ultrafast", 23, "Maximale Geschwindigkeit, größere Datei."),
    "fast": EncodeProfile("fast", "Schnell", "veryfast", 21, "Sehr schnell bei guter Qualität."),
    "balanced": EncodeProfile("balanced", "Ausgewogen", "faster", 20, "Etwas kleiner, moderat langsamer."),
    "quality": EncodeProfile("quality", "Qualität", "medium", 18, "Hohe Qualität, deutlich langsamer."),
}

RESOLUTIONS = {
    "Original": None,
    "1280×720": (1280, 720),
    "1920×1080": (1920, 1080),
}

COPY_COMPATIBLE_CODECS = {"h264", "hevc", "av1", "mpeg4"}


def resolved_options(job: PairJob, options: BatchOptions) -> BatchOptions:
    return processing_options_for_job(job, options)


def can_use_fast_copy(job: PairJob, options: BatchOptions) -> tuple[bool, str]:
    selected = resolved_options(job, options)
    if job.is_slideshow:
        return False, "Diashows werden als ein synchronisierter Video-Stream erzeugt."
    if selected.visual_effect != "none":
        return False, "Der gewählte Bildeffekt im Automatik-Look benötigt eine schnelle Einpass-Neucodierung."
    if selected.transition != "none":
        return False, "Die gewählte Ein-/Ausblendung benötigt eine schnelle Einpass-Neucodierung."
    if job.media_info.kind != "video":
        return False, "Bilder müssen einmal zu Video codiert werden."
    if selected.resolution != "Original":
        return False, "Die Auflösung wird geändert."
    if job.media_info.codec not in COPY_COMPATIBLE_CODECS:
        return False, f"Codec {job.media_info.codec or 'unbekannt'} wird sicher neu codiert."
    audio_duration = job.audio_info.duration
    video_duration = job.media_info.duration
    if audio_duration and video_duration and video_duration + 0.2 < audio_duration:
        return False, "Das Video ist kürzer als das Audio und muss wiederholt werden."
    return True, "Videostream wird ohne Qualitätsverlust direkt kopiert."


def _scale_filter(resolution: str) -> str | None:
    target = RESOLUTIONS.get(resolution)
    if not target:
        return None
    width, height = target
    return f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2"


def _video_filter(job: PairJob, options: BatchOptions) -> str | None:
    filters: list[str] = []
    scale_filter = _scale_filter(options.resolution)
    if scale_filter:
        filters.append(scale_filter)
    selected_effect = effect_filter(options.visual_effect)
    if selected_effect:
        filters.append(selected_effect)
    filters.extend(transition_filters(options.transition, job.audio_info.duration))
    return ",".join(filters) if filters else None



def _even(value: int, fallback: int) -> int:
    selected = value if value and value > 0 else fallback
    return selected if selected % 2 == 0 else selected + 1


def _slideshow_canvas(job: PairJob, options: BatchOptions) -> tuple[int, int]:
    target = RESOLUTIONS.get(options.resolution)
    if target:
        return target
    return _even(int(job.media_info.width or 0), 1920), _even(int(job.media_info.height or 0), 1080)


def _slideshow_input_durations(job: PairJob) -> tuple[float, ...]:
    if job.slide_durations and len(job.slide_durations) == len(job.media_sequence):
        return tuple(max(0.05, float(value)) for value in job.slide_durations)
    if not job.slide_duration:
        return ()
    return tuple(float(job.slide_duration) for _ in job.media_sequence)


def _slideshow_filter(job: PairJob, options: BatchOptions) -> tuple[str, str]:
    durations = _slideshow_input_durations(job)
    if not job.media_sequence or not durations or not job.audio_info.duration:
        raise ValueError("Diashowplan ist unvollständig: Audiodauer oder Bildzeiten fehlen.")
    width, height = _slideshow_canvas(job, options)
    crossfade = max(0.0, float(job.slide_transition))
    effect = effect_filter(options.visual_effect)
    chains: list[str] = []
    labels: list[str] = []
    for index, (_path, duration) in enumerate(zip(job.media_sequence, durations)):
        label = f"s{index}"
        filters = [
            f"scale={width}:{height}:force_original_aspect_ratio=decrease",
            f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=black",
            "setsar=1",
            "format=yuv420p",
        ]
        if effect:
            filters.append(effect)
        filters.extend([
            f"settb=1/{options.fps}",
            "setpts=N",
            f"fps={options.fps}",
            f"trim=duration={duration:.3f}",
        ])
        chains.append(f"[{index}:v]{','.join(filters)}[{label}]")
        labels.append(label)

    if len(labels) == 1:
        current = labels[0]
    elif crossfade > 0:
        current = labels[0]
        offset = max(0.0, durations[0] - crossfade)
        for index, label in enumerate(labels[1:], start=1):
            output = f"xf{index}"
            chains.append(
                f"[{current}][{label}]xfade=transition=fade:duration={crossfade:.3f}:offset={offset:.3f}[{output}]"
            )
            current = output
            if index < len(durations) - 1:
                offset += max(0.05, durations[index] - crossfade)
    else:
        current = "slideshow_concat"
        inputs = "".join(f"[{label}]" for label in labels)
        chains.append(f"{inputs}concat=n={len(labels)}:v=1:a=0[{current}]")

    finishing = transition_filters(options.transition, job.audio_info.duration)
    if finishing:
        output = "slideshow_out"
        chains.append(f"[{current}]{','.join(finishing)},format=yuv420p[{output}]")
        current = output
    return ";".join(chains), current


def _build_slideshow_command(job: PairJob, options: BatchOptions) -> list[str]:
    binary = ffmpeg_path() or "ffmpeg"
    profile = PROFILES[options.profile]
    command: list[str] = [binary, "-hide_banner", "-y" if options.overwrite else "-n"]
    durations = _slideshow_input_durations(job)
    if not durations:
        raise ValueError("Die Audiodauer konnte nicht für die automatische Diashow bestimmt werden.")
    for image, duration in zip(job.media_sequence, durations):
        command += ["-loop", "1", "-framerate", str(options.fps), "-t", f"{duration:.3f}", "-i", str(image)]
    audio_index = len(job.media_sequence)
    command += ["-i", str(job.audio)]
    graph, video_label = _slideshow_filter(job, options)
    command += ["-filter_complex", graph, "-map", f"[{video_label}]", "-map", f"{audio_index}:a:0"]
    command += ["-c:v", options.codec, "-preset", profile.preset, "-crf", str(profile.crf)]
    command += ["-pix_fmt", "yuv420p", "-r", str(options.fps)]
    if options.max_threads > 0:
        command += ["-threads", str(options.max_threads)]
    command += ["-c:a", "aac", "-b:a", options.audio_bitrate]
    command += ["-t", f"{job.audio_info.duration:.3f}", "-movflags", "+faststart", "-progress", "pipe:1", "-nostats", str(job.output)]
    return command

def build_command(job: PairJob, options: BatchOptions, *, force_encode: bool = False) -> list[str]:
    selected = resolved_options(job, options)
    if job.is_slideshow:
        return _build_slideshow_command(job, selected)
    binary = ffmpeg_path() or "ffmpeg"
    profile = PROFILES[selected.profile]
    command: list[str] = [binary, "-hide_banner", "-y" if selected.overwrite else "-n"]
    duration = job.audio_info.duration
    video_filter = _video_filter(job, selected)
    use_copy = job.fast_path and not force_encode and video_filter is None

    if job.media_info.kind == "image":
        command += ["-loop", "1", "-framerate", str(selected.fps), "-i", str(job.media), "-i", str(job.audio)]
    elif job.media_info.kind == "video":
        if not use_copy and duration and job.media_info.duration and job.media_info.duration + 0.2 < duration:
            command += ["-stream_loop", "-1"]
        command += ["-i", str(job.media), "-i", str(job.audio)]
    else:
        raise ValueError(f"Nicht unterstützter Medientyp: {job.media_info.kind}")

    command += ["-map", "0:v:0", "-map", "1:a:0"]
    if use_copy:
        command += ["-c:v", "copy"]
    else:
        command += ["-c:v", selected.codec, "-preset", profile.preset, "-crf", str(profile.crf)]
        if job.media_info.kind == "image":
            if selected.codec == "libx264":
                command += ["-tune", "stillimage"]
            command += ["-r", str(selected.fps)]
        if video_filter:
            command += ["-vf", video_filter]
        command += ["-pix_fmt", "yuv420p"]
        if selected.max_threads > 0:
            command += ["-threads", str(selected.max_threads)]
    if use_copy and job.media_info.codec == "hevc":
        command += ["-tag:v", "hvc1"]
    command += ["-c:a", "aac", "-b:a", selected.audio_bitrate]
    if duration:
        command += ["-t", f"{duration:.3f}"]
    else:
        command += ["-shortest"]
    command += ["-movflags", "+faststart", "-progress", "pipe:1", "-nostats", str(job.output)]
    return command
