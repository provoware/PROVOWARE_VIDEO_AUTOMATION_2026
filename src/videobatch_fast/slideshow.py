from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .audio_waveform import SceneMarker, scene_change_points


SLIDESHOW_MODE_PAIRWISE = "pairwise"
SLIDESHOW_MODE_ALL_IMAGES = "all_images_each_audio"
SLIDESHOW_MODES = {SLIDESHOW_MODE_PAIRWISE, SLIDESHOW_MODE_ALL_IMAGES}

TRANSITION_PRESETS: dict[str, float | None] = {
    "auto": None,
    "none": 0.0,
    "soft": 0.5,
    "clear": 1.0,
}

TRANSITION_LABELS = {
    "auto": "Automatisch weich (empfohlen)",
    "none": "Ohne Überblendung",
    "soft": "Sanft · 0,5 Sekunden",
    "clear": "Deutlich · 1,0 Sekunde",
}


@dataclass(frozen=True, slots=True)
class SlideshowPlan:
    audio_duration: float
    image_count: int
    segment_duration: float
    crossfade_duration: float
    visible_duration: float
    input_durations: tuple[float, ...] = ()
    change_points: tuple[float, ...] = ()
    scene_aligned: bool = False

    @property
    def total_duration(self) -> float:
        durations = self.input_durations or (self.segment_duration,) * self.image_count
        return sum(durations) - max(0, self.image_count - 1) * self.crossfade_duration

    @property
    def visible_durations(self) -> tuple[float, ...]:
        if self.change_points and len(self.change_points) == self.image_count + 1:
            return tuple(
                round(self.change_points[index + 1] - self.change_points[index], 3)
                for index in range(self.image_count)
            )
        return (self.visible_duration,) * self.image_count


def transition_seconds(preset: str, *, audio_duration: float, image_count: int) -> float:
    if image_count <= 1 or audio_duration <= 0:
        return 0.0
    selected = TRANSITION_PRESETS.get(preset, None)
    if selected is None:
        base = audio_duration / image_count
        selected = min(0.75, max(0.20, base * 0.12))
    maximum = max(0.0, audio_duration / max(2.0, image_count * 2.5))
    return round(min(float(selected), maximum), 3)


def _input_durations(visible: tuple[float, ...], fade: float) -> tuple[float, ...]:
    if not visible:
        return ()
    if fade <= 0 or len(visible) == 1:
        return tuple(round(max(0.05, value), 3) for value in visible)
    result = [max(0.05, value + fade) for value in visible[:-1]]
    result.append(max(0.05, visible[-1]))
    return tuple(round(value, 3) for value in result)


def build_slideshow_plan(
    audio_duration: float | None,
    image_count: int,
    preset: str = "auto",
    *,
    scene_markers: Iterable[SceneMarker] = (),
    scene_sync: bool = False,
) -> SlideshowPlan | None:
    if audio_duration is None or audio_duration <= 0 or image_count <= 0:
        return None
    duration = float(audio_duration)
    fade = transition_seconds(preset, audio_duration=duration, image_count=image_count)
    markers = tuple(scene_markers)
    if scene_sync and markers and image_count > 1:
        points = scene_change_points(duration, image_count, markers)
        visible = tuple(max(0.05, points[index + 1] - points[index]) for index in range(image_count))
        # Scene markers can create shorter intervals than the uniform plan.
        # Keep every crossfade below half of the shortest interval so xfade
        # never receives a transition longer than its source segment.
        if fade > 0:
            fade = round(min(fade, max(0.0, min(visible) * 0.45)), 3)
        inputs = _input_durations(visible, fade)
        return SlideshowPlan(
            audio_duration=duration,
            image_count=image_count,
            segment_duration=round(sum(inputs) / len(inputs), 3),
            crossfade_duration=fade,
            visible_duration=round(sum(visible) / len(visible), 3),
            input_durations=inputs,
            change_points=points,
            scene_aligned=True,
        )

    visible = tuple(duration / image_count for _ in range(image_count))
    inputs = _input_durations(visible, fade)
    points = tuple(round(index * duration / image_count, 3) for index in range(image_count + 1))
    return SlideshowPlan(
        audio_duration=duration,
        image_count=image_count,
        segment_duration=round(sum(inputs) / len(inputs), 3),
        crossfade_duration=fade,
        visible_duration=round(duration / image_count, 3),
        input_durations=inputs,
        change_points=points,
        scene_aligned=False,
    )


def slideshow_summary(
    audio_duration: float | None,
    image_count: int,
    preset: str = "auto",
    *,
    scene_sync: bool = False,
    marker_count: int = 0,
) -> str:
    plan = build_slideshow_plan(audio_duration, image_count, preset)
    if image_count <= 0:
        return "Noch keine Bilder ausgewählt."
    if plan is None:
        return f"{image_count} Bilder · Audiodauer wird beim Einlesen ermittelt."
    minutes, seconds = divmod(round(plan.audio_duration), 60)
    fade = "ohne Überblendung" if plan.crossfade_duration <= 0 else f"{plan.crossfade_duration:.2f}s Überblendung"
    rhythm = f" · {marker_count} Szenenmarken" if scene_sync else " · gleichmäßig"
    return (
        f"Audio {minutes}:{seconds:02d} · {plan.image_count} Bilder · "
        f"Ø {plan.visible_duration:.2f}s je Bild · {fade}{rhythm}"
    )
