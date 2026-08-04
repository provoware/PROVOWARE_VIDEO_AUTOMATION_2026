from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

from PIL import Image, UnidentifiedImageError

from .paths import cache_dir
from .probe import ffmpeg_path, probe_media


class PreviewError(RuntimeError):
    pass


def preview_cache_path(source: Path, width: int = 1280) -> Path:
    stat = source.stat()
    digest = hashlib.sha256(f"{source.resolve()}:{stat.st_mtime_ns}:{stat.st_size}:{width}".encode()).hexdigest()[:24]
    directory = cache_dir() / "previews"
    directory.mkdir(parents=True, exist_ok=True)
    return directory / f"{digest}.png"


def build_preview(source: Path, width: int = 1280) -> Path:
    source = Path(source)
    if not source.is_file():
        raise PreviewError("Quelldatei ist nicht erreichbar.")
    binary = ffmpeg_path()
    if not binary:
        raise PreviewError("FFmpeg fehlt.")
    target = preview_cache_path(source, width)
    if target.exists() and target.stat().st_size > 100:
        return target
    info = probe_media(source)
    if info.kind not in {"image", "video"}:
        raise PreviewError("Für diesen Dateityp ist keine Bildvorschau verfügbar.")
    command = [binary, "-v", "error", "-y"]
    if info.kind == "video":
        command += ["-ss", "0.5"]
    command += ["-i", str(source), "-frames:v", "1", "-vf", f"scale='min({max(320, width)},iw)':-2", str(target)]
    result = subprocess.run(command, capture_output=True, text=True, timeout=30, errors="replace")
    if result.returncode or not target.exists() or target.stat().st_size < 100:
        target.unlink(missing_ok=True)
        detail = (result.stderr or "Vorschau konnte nicht erzeugt werden.").strip().splitlines()[-1]
        raise PreviewError(detail)
    return target


MAX_PREVIEW_FILE_BYTES = 64 * 1024 * 1024
MAX_PREVIEW_PIXELS = 24_000_000


def load_preview_bitmap(
    preview_path: Path,
    *,
    max_width: int,
    max_height: int,
) -> Image.Image:
    """Load a generated preview defensively before handing pixels to Tk."""
    path = Path(preview_path)
    try:
        size = path.stat().st_size
    except OSError as exc:
        raise PreviewError("Vorschaudatei ist nicht mehr erreichbar.") from exc
    if size <= 0 or size > MAX_PREVIEW_FILE_BYTES:
        raise PreviewError("Vorschaudatei besitzt eine unzulässige Größe.")
    try:
        with Image.open(path) as source:
            width, height = source.size
            if width <= 0 or height <= 0 or width * height > MAX_PREVIEW_PIXELS:
                raise PreviewError("Vorschaubild überschreitet die sichere Pixelgrenze.")
            image = source.convert("RGBA")
            image.thumbnail((max(64, int(max_width)), max(64, int(max_height))))
            return image.copy()
    except (OSError, UnidentifiedImageError, Image.DecompressionBombError) as exc:
        raise PreviewError("Vorschaubild ist beschädigt oder nicht sicher lesbar.") from exc
