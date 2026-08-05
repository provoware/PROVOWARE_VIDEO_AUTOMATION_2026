from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Any, Callable

from .command_builder import build_command
from .long_render_schema import JobSpec, LoadedContract, LongRenderContractError, ResourceLimits
from .long_render_target import hard_limit_prefix
from .models import BatchOptions, JobResult, PairJob
from .probe import probe_media
from .runner import _process_cpu_ticks, terminate_process_group
from .runner_process import ProcessExecution
from .verification import verify_output

Executor = Callable[[PairJob, BatchOptions, Callable[[str, dict[str, Any]], None], Callable[[], bool]], JobResult]


def _job_index(job_id: str) -> int:
    if job_id.isdigit():
        return int(job_id)
    return int(hashlib.sha256(job_id.encode()).hexdigest()[:8], 16)


def build_pair_job(spec: JobSpec, output: Path) -> PairJob:
    audio_info = probe_media(spec.audio)
    if audio_info.kind != "audio" or not audio_info.duration:
        raise LongRenderContractError(f"Audio ist nicht vollständig prüfbar: {spec.audio}")
    media_info = probe_media(spec.media[0])
    if len(spec.media) > 1:
        for path in spec.media:
            info = probe_media(path)
            if info.kind != "image":
                raise LongRenderContractError(f"Mehrfachmedien müssen Bilder sein: {path}")
        duration = max(0.1, audio_info.duration / len(spec.media))
        return PairJob(
            index=_job_index(spec.job_id),
            audio=spec.audio,
            media=spec.media[0],
            output=output,
            audio_info=audio_info,
            media_info=media_info,
            fast_path=False,
            reason="Gebundener Langzeitrender-Vertrag",
            media_sequence=spec.media,
            slide_duration=duration,
            slide_durations=tuple(duration for _ in spec.media),
        )
    if media_info.kind not in {"image", "video"}:
        raise LongRenderContractError(f"Medium ist nicht vollständig prüfbar: {spec.media[0]}")
    return PairJob(
        index=_job_index(spec.job_id),
        audio=spec.audio,
        media=spec.media[0],
        output=output,
        audio_info=audio_info,
        media_info=media_info,
        fast_path=False,
        reason="Gebundener Langzeitrender-Vertrag",
    )


def batch_options(contract: LoadedContract) -> BatchOptions:
    values = contract.options
    cpu_threads = max(1, int((os.cpu_count() or 1) * contract.limits.cpu_percent / 100))
    return BatchOptions(
        output_dir=contract.target_dir,
        resolution=str(values.get("resolution", "1920×1080")),
        codec=str(values.get("codec", "libx264")),
        profile=str(values.get("profile", "balanced")),
        verification="Vollständig",
        overwrite=False,
        keep_lists=True,
        audio_bitrate=str(values.get("audio_bitrate", "192k")),
        fps=int(values.get("fps", 25)),
        max_threads=int(values.get("max_threads", cpu_threads)),
        visual_effect=str(values.get("visual_effect", "none")),
        transition=str(values.get("transition", "none")),
        quick_mode=str(values.get("quick_mode", "custom")),
        assignment_mode="pairwise",
        slideshow_transition=str(values.get("slideshow_transition", "none")),
        slideshow_scene_sync=bool(values.get("slideshow_scene_sync", False)),
    )


def execute_job(
    job: PairJob,
    options: BatchOptions,
    emit: Callable[[str, dict[str, Any]], None],
    cancelled: Callable[[], bool],
    *,
    hard_limits: bool,
    limits: ResourceLimits,
) -> JobResult:
    command = build_command(job, options)
    prefix = hard_limit_prefix(limits) if hard_limits else []
    if hard_limits and not prefix:
        raise LongRenderContractError("Harte CPU-/RAM-Grenzen benötigen systemd-run im Benutzerkontext.")
    wrapped = [*prefix, *command]

    def emit_adapter(name: str, **payload: Any) -> None:
        emit(name, payload)

    execution = ProcessExecution(
        emit=emit_adapter,
        cancelled=cancelled,
        set_process=lambda _process: None,
        terminate=terminate_process_group,
        cpu_ticks=_process_cpu_ticks,
    )
    raw = execution.run(wrapped, job, 1, 1)
    if raw.returncode != 0:
        return raw
    valid, message = verify_output(job.output, job, "Vollständig")
    return JobResult(
        job=job,
        success=valid,
        returncode=0 if valid else 65,
        elapsed_seconds=raw.elapsed_seconds,
        message=message,
        retried=raw.retried,
        command=wrapped,
        fallback_mode=raw.fallback_mode,
    )
