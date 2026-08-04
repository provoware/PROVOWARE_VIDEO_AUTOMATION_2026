from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from .audio_waveform import WaveformAnalysis
from .command_builder import can_use_fast_copy
from .models import BatchOptions, PairJob
from .naming import unique_output_path
from .probe import probe_media
from .slideshow import SLIDESHOW_MODE_ALL_IMAGES, build_slideshow_plan


def _pairwise_jobs(audios: list[Path], media: list[Path], options: BatchOptions) -> list[PairJob]:
    if len(audios) != len(media):
        return []
    jobs: list[PairJob] = []
    reserved_outputs: set[Path] = set()
    for index, (audio, visual) in enumerate(zip(audios, media), start=1):
        audio_info = probe_media(audio)
        media_info = probe_media(visual)
        target_dir = visual.parent if options.output_mode == "Neben Mediendatei" else options.output_dir
        target_dir.mkdir(parents=True, exist_ok=True)
        provisional = PairJob(
            index,
            audio,
            visual,
            unique_output_path(target_dir, audio, reserved=reserved_outputs, index=index),
            audio_info,
            media_info,
            False,
            "",
        )
        fast_path, reason = can_use_fast_copy(provisional, options)
        jobs.append(PairJob(index, audio, visual, provisional.output, audio_info, media_info, fast_path, reason))
    return jobs


def _slideshow_jobs(
    audios: list[Path],
    media: list[Path],
    options: BatchOptions,
    scene_analyses: Mapping[Path, WaveformAnalysis] | None = None,
) -> list[PairJob]:
    if not audios or not media:
        return []
    image_records = [(path, probe_media(path)) for path in media]
    images = [(path, info) for path, info in image_records if info.kind == "image"]
    if not images:
        return []
    image_paths = tuple(path for path, _info in images)
    primary_path, primary_info = images[0]
    jobs: list[PairJob] = []
    reserved_outputs: set[Path] = set()
    analyses = scene_analyses or {}
    for index, audio in enumerate(audios, start=1):
        audio_info = probe_media(audio)
        analysis = analyses.get(audio)
        markers = analysis.markers if analysis is not None else ()
        scene_sync = bool(options.slideshow_scene_sync and analysis is not None)
        plan = build_slideshow_plan(
            audio_info.duration,
            len(image_paths),
            options.slideshow_transition,
            scene_markers=markers,
            scene_sync=scene_sync,
        )
        target_dir = primary_path.parent if options.output_mode == "Neben Mediendatei" else options.output_dir
        target_dir.mkdir(parents=True, exist_ok=True)
        output = unique_output_path(target_dir, audio, reserved=reserved_outputs, index=index)
        if plan is None:
            reason = f"Diashow mit {len(image_paths)} Bildern · Audiodauer muss lesbar sein."
            slide_duration = None
            slide_transition = 0.0
            slide_durations: tuple[float, ...] = ()
            change_points: tuple[float, ...] = ()
        else:
            rhythm = " · Szenenmarken" if plan.scene_aligned else " · gleichmäßig"
            reason = f"Diashow · {len(image_paths)} Bilder · Ø {plan.visible_duration:.2f}s{rhythm}"
            slide_duration = plan.segment_duration
            slide_transition = plan.crossfade_duration
            slide_durations = plan.input_durations
            change_points = plan.change_points
        jobs.append(
            PairJob(
                index=index,
                audio=audio,
                media=primary_path,
                output=output,
                audio_info=audio_info,
                media_info=primary_info,
                fast_path=False,
                reason=reason,
                media_sequence=image_paths,
                slide_duration=slide_duration,
                slide_transition=slide_transition,
                slide_durations=slide_durations,
                slide_change_points=change_points,
                scene_markers=analysis.marker_tuples() if analysis is not None else (),
            )
        )
    return jobs


def build_jobs(
    audios: list[Path],
    media: list[Path],
    options: BatchOptions,
    *,
    scene_analyses: Mapping[Path, WaveformAnalysis] | None = None,
) -> list[PairJob]:
    if options.assignment_mode == SLIDESHOW_MODE_ALL_IMAGES:
        return _slideshow_jobs(audios, media, options, scene_analyses)
    return _pairwise_jobs(audios, media, options)
