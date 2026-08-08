from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path

from PIL import Image, ImageChops, ImageFilter, ImageOps, ImageStat

from .registry import PROJECT_ROOT, load_json


@dataclass(frozen=True, slots=True)
class VisualComparison:
    scenario_id: str
    passed: bool
    mean_difference: float
    dhash_distance: int
    baseline: str
    actual: str
    message: str
    rmse: float = 1.0
    changed_pixel_ratio: float = 1.0
    edge_difference: float = 1.0
    aspect_ratio_delta: float = 1.0
    difference_bbox: tuple[float, float, float, float] | None = None
    baseline_size: tuple[int, int] = (0, 0)
    actual_size: tuple[int, int] = (0, 0)


def _prepared(image: Image.Image) -> Image.Image:
    """Normalize orientation and alpha without mutating the source image."""
    normalized = ImageOps.exif_transpose(image)
    if normalized.mode in {"RGBA", "LA"}:
        rgba = normalized.convert("RGBA")
        background = Image.new("RGBA", rgba.size, (0, 0, 0, 255))
        normalized = Image.alpha_composite(background, rgba).convert("RGB")
    else:
        normalized = normalized.convert("RGB")
    return normalized


def _relative_canvas(left: Image.Image, right: Image.Image, size: tuple[int, int] = (960, 540)) -> tuple[Image.Image, Image.Image]:
    """Map both screenshots to the same relative viewport coordinate system.

    UI screenshots can legitimately use different physical viewport sizes.  An
    anisotropic normalized canvas preserves relative x/y positions for geometry
    comparison while aspect-ratio drift is reported independently so it cannot
    be hidden by the normalization.
    """
    return (
        left.resize(size, Image.Resampling.LANCZOS),
        right.resize(size, Image.Resampling.LANCZOS),
    )


def _dhash(image: Image.Image, size: int = 8) -> int:
    gray = image.convert("L").resize((size + 1, size), Image.Resampling.LANCZOS)
    pixels = list(gray.get_flattened_data())
    value = 0
    for row in range(size):
        for col in range(size):
            left = pixels[row * (size + 1) + col]
            right = pixels[row * (size + 1) + col + 1]
            value = (value << 1) | int(left > right)
    return value


def _hamming(left: int, right: int) -> int:
    return (left ^ right).bit_count()


def _difference_metrics(left: Image.Image, right: Image.Image) -> tuple[float, float, float, tuple[float, float, float, float] | None]:
    left, right = _relative_canvas(left, right)
    diff = ImageChops.difference(left, right)
    stat = ImageStat.Stat(diff)
    mean = sum(stat.mean) / (3.0 * 255.0)
    rms_channels = getattr(stat, "rms", (255.0, 255.0, 255.0))
    rmse = math.sqrt(sum(value * value for value in rms_channels) / 3.0) / 255.0

    gray = diff.convert("L")
    threshold = gray.point(lambda value: 255 if value >= 12 else 0)
    histogram = threshold.histogram()
    changed = sum(histogram[1:]) / max(1, left.width * left.height)
    bbox = threshold.getbbox()
    relative_bbox = None
    if bbox:
        relative_bbox = (
            round(bbox[0] / left.width, 4),
            round(bbox[1] / left.height, 4),
            round(bbox[2] / left.width, 4),
            round(bbox[3] / left.height, 4),
        )
    return mean, rmse, changed, relative_bbox


def _edge_difference(left: Image.Image, right: Image.Image) -> float:
    left, right = _relative_canvas(left, right)
    left_edge = left.convert("L").filter(ImageFilter.FIND_EDGES)
    right_edge = right.convert("L").filter(ImageFilter.FIND_EDGES)
    diff = ImageChops.difference(left_edge, right_edge)
    return float(ImageStat.Stat(diff).mean[0]) / 255.0


def compare_visual(scenario_id: str, baseline: Path, actual: Path) -> VisualComparison:
    registry = load_json("registries/VISUAL_REGRESSION_REGISTRY.json")
    policy = registry.get("policy", {})
    maximum_mean = float(policy.get("maximum_mean_difference", 0.075))
    maximum_hash = int(policy.get("maximum_dhash_distance", 24))
    maximum_changed = float(policy.get("maximum_changed_pixel_ratio", 0.55))
    maximum_edge = float(policy.get("maximum_edge_difference", 0.18))
    maximum_aspect = float(policy.get("maximum_aspect_ratio_delta", 0.40))
    if not baseline.is_file():
        return VisualComparison(scenario_id, False, 1.0, 64, str(baseline), str(actual), "Referenzbild fehlt. Kandidat darf nicht automatisch akzeptiert werden.")
    if not actual.is_file():
        return VisualComparison(scenario_id, False, 1.0, 64, str(baseline), str(actual), "Aktuelles Bildschirmbild fehlt.")
    with Image.open(baseline) as baseline_raw, Image.open(actual) as actual_raw:
        base = _prepared(baseline_raw)
        current = _prepared(actual_raw)
        baseline_size = base.size
        actual_size = current.size
        mean, rmse, changed, bbox = _difference_metrics(base, current)
        edge = _edge_difference(base, current)
        distance = _hamming(_dhash(base), _dhash(current))
        base_ratio = base.width / max(1, base.height)
        actual_ratio = current.width / max(1, current.height)
        aspect_delta = abs(base_ratio - actual_ratio) / max(base_ratio, 1e-9)
    passed = (
        mean <= maximum_mean
        and distance <= maximum_hash
        and changed <= maximum_changed
        and edge <= maximum_edge
        and aspect_delta <= maximum_aspect
    )
    if passed:
        message = "Visuelle Referenz bestanden."
    else:
        message = (
            f"Abweichung zu groß: Mittelwert {mean:.4f}, RMSE {rmse:.4f}, "
            f"geänderte Fläche {changed:.1%}, Kanten {edge:.4f}, dHash {distance}, "
            f"Seitenverhältnis Δ {aspect_delta:.1%}."
        )
    return VisualComparison(
        scenario_id=scenario_id,
        passed=passed,
        mean_difference=mean,
        dhash_distance=distance,
        baseline=str(baseline),
        actual=str(actual),
        message=message,
        rmse=rmse,
        changed_pixel_ratio=changed,
        edge_difference=edge,
        aspect_ratio_delta=aspect_delta,
        difference_bbox=bbox,
        baseline_size=baseline_size,
        actual_size=actual_size,
    )


def write_visual_report(results: list[VisualComparison], target: Path, contract_errors: list[str] | None = None) -> Path:
    target.parent.mkdir(parents=True, exist_ok=True)
    errors = list(contract_errors or [])
    payload = {
        "schema_version": 2,
        "passed": all(result.passed for result in results) and not errors,
        "contract_errors": errors,
        "results": [asdict(result) for result in results],
    }
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return target


def validate_reference_palette(image_path: Path | None = None) -> list[str]:
    registry = load_json("registries/VISUAL_REGRESSION_REGISTRY.json")
    path = image_path or PROJECT_ROOT / str(registry.get("reference_image"))
    if not path.is_file():
        return [f"Designreferenz fehlt: {path}"]
    errors: list[str] = []
    with Image.open(path) as raw:
        image = _prepared(raw)
        width, height = image.size
        if width < 700 or height < 600:
            errors.append(f"Designreferenz ist unerwartet klein: {width}x{height}")
        rgb = image.resize((160, 140), Image.Resampling.LANCZOS)
        colors = rgb.getcolors(maxcolors=160 * 140) or []
        dark_pixels = sum(count for count, color in colors if sum(color) / 3 < 50)
        if dark_pixels < 0.45 * 160 * 140:
            errors.append("Designreferenz besitzt nicht den erwarteten dunklen Grundcharakter.")
    return errors


def validate_semantic_colors(image_path: Path, tolerance: int = 8, minimum_pixels: int = 80, expected_colors: list[str] | None = None) -> list[str]:
    registry = load_json("registries/VISUAL_REGRESSION_REGISTRY.json")
    expected = expected_colors if expected_colors is not None else registry.get("policy", {}).get("required_semantic_colors", [])
    errors: list[str] = []
    with Image.open(image_path) as raw:
        image = _prepared(raw)
        pixels = list(image.resize((640, 360), Image.Resampling.NEAREST).get_flattened_data())
    for value in expected:
        raw = str(value).lstrip("#")
        target = tuple(int(raw[index:index + 2], 16) for index in (0, 2, 4))
        count = sum(1 for pixel in pixels if all(abs(pixel[channel] - target[channel]) <= tolerance for channel in range(3)))
        if count < minimum_pixels:
            errors.append(f"Semantische Farbe {value} fehlt oder ist zu schwach sichtbar ({count} Pixel).")
    return errors


def create_difference_image(baseline: Path, actual: Path, target: Path) -> Path:
    target.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(baseline) as baseline_raw, Image.open(actual) as actual_raw:
        base = _prepared(baseline_raw)
        current = _prepared(actual_raw)
        base, current = _relative_canvas(base, current)
        diff = ImageChops.difference(base, current)
        enhanced = diff.point(lambda value: min(255, value * 4))
        enhanced.save(target)
    return target
