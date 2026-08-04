from __future__ import annotations

from datetime import datetime
from pathlib import Path
import random
from typing import Iterable

from PIL import Image

ORDER_MANUAL = "manual"
ORDER_ALPHABETICAL = "alphabetical"
ORDER_CAPTURE_DATE = "capture_date"
ORDER_RANDOM = "random"
ORDER_MODES = {ORDER_MANUAL, ORDER_ALPHABETICAL, ORDER_CAPTURE_DATE, ORDER_RANDOM}

_EXIF_DATE_TAGS = (36867, 36868, 306)  # DateTimeOriginal, DateTimeDigitized, DateTime
_EXIF_FORMATS = ("%Y:%m:%d %H:%M:%S", "%Y-%m-%d %H:%M:%S")


def _capture_datetime(path: Path) -> datetime | None:
    try:
        with Image.open(path) as image:
            exif = image.getexif()
            for tag in _EXIF_DATE_TAGS:
                raw = exif.get(tag)
                if not raw:
                    continue
                value = str(raw).strip().replace("\x00", "")
                for fmt in _EXIF_FORMATS:
                    try:
                        return datetime.strptime(value, fmt)
                    except ValueError:
                        continue
    except (OSError, ValueError, Image.DecompressionBombError):
        return None
    return None


def capture_timestamp(path: Path) -> float:
    captured = _capture_datetime(path)
    if captured is not None:
        return captured.timestamp()
    try:
        return path.stat().st_mtime
    except OSError:
        return 0.0


def _existing_anchor(value: Path | str | None, candidates: list[Path]) -> Path | None:
    if value is None:
        return None
    target = Path(value)
    return target if target in candidates else None


def apply_anchors(
    paths: Iterable[Path],
    *,
    start_image: Path | str | None = None,
    end_image: Path | str | None = None,
) -> list[Path]:
    result = list(dict.fromkeys(Path(item) for item in paths))
    start = _existing_anchor(start_image, result)
    end = _existing_anchor(end_image, result)
    if start is not None:
        result.remove(start)
        result.insert(0, start)
    if end is not None and end != start:
        result.remove(end)
        result.append(end)
    return result


def order_images(
    paths: Iterable[Path],
    mode: str = ORDER_MANUAL,
    *,
    random_seed: int = 0,
    start_image: Path | str | None = None,
    end_image: Path | str | None = None,
) -> list[Path]:
    result = list(dict.fromkeys(Path(item) for item in paths))
    selected = mode if mode in ORDER_MODES else ORDER_MANUAL
    if selected == ORDER_ALPHABETICAL:
        result.sort(key=lambda path: (path.name.casefold(), str(path).casefold()))
    elif selected == ORDER_CAPTURE_DATE:
        result.sort(key=lambda path: (capture_timestamp(path), path.name.casefold()))
    elif selected == ORDER_RANDOM:
        random.Random(int(random_seed)).shuffle(result)
    return apply_anchors(result, start_image=start_image, end_image=end_image)


def reverse_images(
    paths: Iterable[Path],
    *,
    start_image: Path | str | None = None,
    end_image: Path | str | None = None,
) -> list[Path]:
    return apply_anchors(reversed(list(paths)), start_image=start_image, end_image=end_image)


def move_image(
    paths: Iterable[Path],
    source_index: int,
    target_index: int,
    *,
    start_image: Path | str | None = None,
    end_image: Path | str | None = None,
) -> list[Path]:
    result = list(paths)
    if not result:
        return result
    source = max(0, min(len(result) - 1, int(source_index)))
    target = max(0, min(len(result) - 1, int(target_index)))
    item = result.pop(source)
    result.insert(target, item)
    return apply_anchors(result, start_image=start_image, end_image=end_image)
