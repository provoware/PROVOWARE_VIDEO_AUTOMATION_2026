from __future__ import annotations

import json
import math
from dataclasses import dataclass, asdict
from pathlib import Path

from PIL import Image, ImageChops, ImageStat

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


def _mean_difference(left: Image.Image, right: Image.Image) -> float:
    if left.size != right.size:
        right = right.resize(left.size, Image.Resampling.LANCZOS)
    diff = ImageChops.difference(left.convert("RGB"), right.convert("RGB"))
    stat = ImageStat.Stat(diff)
    return sum(stat.mean) / (3.0 * 255.0)


def compare_visual(scenario_id: str, baseline: Path, actual: Path) -> VisualComparison:
    registry = load_json("registries/VISUAL_REGRESSION_REGISTRY.json")
    policy = registry.get("policy", {})
    maximum_mean = float(policy.get("maximum_mean_difference", 0.035))
    maximum_hash = int(policy.get("maximum_dhash_distance", 10))
    if not baseline.is_file():
        return VisualComparison(scenario_id, False, 1.0, 64, str(baseline), str(actual), "Referenzbild fehlt. Kandidat darf nicht automatisch akzeptiert werden.")
    if not actual.is_file():
        return VisualComparison(scenario_id, False, 1.0, 64, str(baseline), str(actual), "Aktuelles Bildschirmbild fehlt.")
    with Image.open(baseline) as base_image, Image.open(actual) as actual_image:
        mean = _mean_difference(base_image, actual_image)
        distance = _hamming(_dhash(base_image), _dhash(actual_image))
    passed = mean <= maximum_mean and distance <= maximum_hash
    message = "Visuelle Referenz bestanden." if passed else f"Abweichung zu groß: Mittelwert {mean:.4f}, dHash {distance}."
    return VisualComparison(scenario_id, passed, mean, distance, str(baseline), str(actual), message)


def write_visual_report(results: list[VisualComparison], target: Path, contract_errors: list[str] | None = None) -> Path:
    target.parent.mkdir(parents=True, exist_ok=True)
    errors = list(contract_errors or [])
    payload = {
        "schema_version": 1,
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
    with Image.open(path) as image:
        width, height = image.size
        if width < 700 or height < 600:
            errors.append(f"Designreferenz ist unerwartet klein: {width}x{height}")
        rgb = image.convert("RGB").resize((160, 140), Image.Resampling.LANCZOS)
        colors = rgb.getcolors(maxcolors=160 * 140) or []
        dark_pixels = sum(count for count, color in colors if sum(color) / 3 < 50)
        if dark_pixels < 0.45 * 160 * 140:
            errors.append("Designreferenz besitzt nicht den erwarteten dunklen Grundcharakter.")
    return errors


def validate_semantic_colors(image_path: Path, tolerance: int = 8, minimum_pixels: int = 80, expected_colors: list[str] | None = None) -> list[str]:
    registry = load_json("registries/VISUAL_REGRESSION_REGISTRY.json")
    expected = expected_colors if expected_colors is not None else registry.get("policy", {}).get("required_semantic_colors", [])
    errors: list[str] = []
    with Image.open(image_path) as image:
        pixels = list(image.convert("RGB").resize((640, 360), Image.Resampling.NEAREST).get_flattened_data())
    for value in expected:
        raw = str(value).lstrip("#")
        target = tuple(int(raw[index:index + 2], 16) for index in (0, 2, 4))
        count = sum(1 for pixel in pixels if all(abs(pixel[channel] - target[channel]) <= tolerance for channel in range(3)))
        if count < minimum_pixels:
            errors.append(f"Semantische Farbe {value} fehlt oder ist zu schwach sichtbar ({count} Pixel).")
    return errors


def create_difference_image(baseline: Path, actual: Path, target: Path) -> Path:
    target.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(baseline) as base_image, Image.open(actual) as actual_image:
        base = base_image.convert("RGB")
        current = actual_image.convert("RGB")
        if base.size != current.size:
            current = current.resize(base.size, Image.Resampling.LANCZOS)
        diff = ImageChops.difference(base, current)
        enhanced = diff.point(lambda value: min(255, value * 4))
        enhanced.save(target)
    return target
