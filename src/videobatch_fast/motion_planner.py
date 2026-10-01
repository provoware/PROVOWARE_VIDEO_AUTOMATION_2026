from __future__ import annotations

from dataclasses import dataclass

ASPECT_RATIOS: dict[str, float] = {
    "16:9": 16 / 9,
    "9:16": 9 / 16,
    "4:3": 4 / 3,
    "3:2": 3 / 2,
    "1:1": 1.0,
}

PFS_MOVEMENT = {"linear": 0, "accelerated": 1, "delayed": 2}


@dataclass(frozen=True, slots=True)
class CropRect:
    left: int
    top: int
    width: int
    height: int

    def as_tuple(self) -> tuple[int, int, int, int]:
        return self.left, self.top, self.width, self.height


@dataclass(frozen=True, slots=True)
class MotionRecipe:
    start_zoom: float = 1.0
    end_zoom: float = 1.25
    start_center: tuple[float, float] = (0.5, 0.5)
    end_center: tuple[float, float] = (0.5, 0.5)
    easing: str = "accelerated"
    duration: float = 7.0

    def __post_init__(self) -> None:
        if self.start_zoom < 1.0 or self.end_zoom < 1.0:
            raise ValueError("Zoomfaktoren müssen mindestens 1.0 betragen.")
        if self.duration <= 0:
            raise ValueError("Die Bewegungsdauer muss größer als null sein.")
        if self.easing not in PFS_MOVEMENT:
            raise ValueError(f"Unbekannte Bewegungskurve: {self.easing}")
        for center in (self.start_center, self.end_center):
            if len(center) != 2 or any(value < 0.0 or value > 1.0 for value in center):
                raise ValueError("Fokuspunkte müssen als normierte Werte zwischen 0 und 1 vorliegen.")


@dataclass(frozen=True, slots=True)
class MotionPlan:
    start: CropRect
    target: CropRect
    movement: int
    duration: float


def preset(name: str, *, duration: float = 7.0) -> MotionRecipe:
    presets = {
        "zoom_in": MotionRecipe(1.0, 1.25, duration=duration),
        "zoom_out": MotionRecipe(1.25, 1.0, duration=duration),
        "pan_left_right": MotionRecipe(1.12, 1.12, (0.35, 0.5), (0.65, 0.5), duration=duration),
        "pan_right_left": MotionRecipe(1.12, 1.12, (0.65, 0.5), (0.35, 0.5), duration=duration),
    }
    try:
        return presets[name]
    except KeyError as exc:
        raise ValueError(f"Unbekanntes Bewegungs-Preset: {name}") from exc


def _base_cover_size(image_width: int, image_height: int, target_ratio: float) -> tuple[float, float]:
    if image_width <= 0 or image_height <= 0:
        raise ValueError("Bildmaße müssen größer als null sein.")
    image_ratio = image_width / image_height
    if image_ratio > target_ratio:
        return image_height * target_ratio, float(image_height)
    return float(image_width), image_width / target_ratio


def _rect_for_zoom(
    image_width: int,
    image_height: int,
    target_ratio: float,
    zoom: float,
    center: tuple[float, float],
) -> CropRect:
    base_width, base_height = _base_cover_size(image_width, image_height, target_ratio)
    width = base_width / zoom
    height = base_height / zoom
    wanted_x = center[0] * image_width
    wanted_y = center[1] * image_height
    center_x = min(max(wanted_x, width / 2), image_width - width / 2)
    center_y = min(max(wanted_y, height / 2), image_height - height / 2)
    left = round(center_x - width / 2)
    top = round(center_y - height / 2)
    rect_width = max(2, round(width))
    rect_height = max(2, round(height))
    left = max(0, min(left, image_width - rect_width))
    top = max(0, min(top, image_height - rect_height))
    return CropRect(left, top, rect_width, rect_height)


def plan_motion(
    image_width: int,
    image_height: int,
    recipe: MotionRecipe,
    *,
    aspect: str = "16:9",
) -> MotionPlan:
    try:
        ratio = ASPECT_RATIOS[aspect]
    except KeyError as exc:
        raise ValueError(f"Nicht unterstütztes Seitenverhältnis: {aspect}") from exc
    return MotionPlan(
        start=_rect_for_zoom(image_width, image_height, ratio, recipe.start_zoom, recipe.start_center),
        target=_rect_for_zoom(image_width, image_height, ratio, recipe.end_zoom, recipe.end_center),
        movement=PFS_MOVEMENT[recipe.easing],
        duration=recipe.duration,
    )
