from __future__ import annotations

import os
import shutil
import sqlite3
from pathlib import Path

from PIL import Image

from .motion_planner import MotionPlan, MotionRecipe, plan_motion

PFS_SCHEMA_REV = 4
PFS_SCHEMA = """
CREATE TABLE picture (
    picture_id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT,
    width INTEGER,
    height INTEGER,
    start_left INTEGER,
    start_top INTEGER,
    start_width INTEGER,
    start_height INTEGER,
    target_left INTEGER,
    target_top INTEGER,
    target_width INTEGER,
    target_height INTEGER,
    rotation INTEGER,
    duration DOUBLE,
    movement INTEGER,
    comment TEXT,
    effect INTEGER,
    transition INTEGER,
    transition_duration DOUBLE,
    data BLOB
);
CREATE TABLE property (
    property_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    value TEXT
);
CREATE TABLE thumbnail (
    thumbnail_id INTEGER PRIMARY KEY AUTOINCREMENT,
    picture_id INTEGER,
    width INTEGER,
    height INTEGER,
    data BLOB,
    FOREIGN KEY(picture_id) REFERENCES picture(picture_id) ON DELETE CASCADE
);
"""


def photofilmstrip_cli_path() -> str:
    configured = os.environ.get("VIDEOBATCH_PHOTOFILMSTRIP_CLI", "").strip()
    if configured:
        candidate = Path(configured).expanduser()
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
    return shutil.which("photofilmstrip-cli") or ""


def image_size(path: Path) -> tuple[int, int]:
    with Image.open(path) as image:
        return int(image.width), int(image.height)


def write_pfs_project(
    project_path: Path,
    image_path: Path,
    recipe: MotionRecipe,
    *,
    audio_path: Path | None = None,
    aspect: str = "16:9",
) -> MotionPlan:
    image_path = Path(image_path).expanduser().resolve()
    if not image_path.is_file():
        raise FileNotFoundError(image_path)
    audio = Path(audio_path).expanduser().resolve() if audio_path else None
    if audio is not None and not audio.is_file():
        raise FileNotFoundError(audio)
    width, height = image_size(image_path)
    plan = plan_motion(width, height, recipe, aspect=aspect)

    project_path = Path(project_path).expanduser()
    project_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = project_path.with_suffix(project_path.suffix + ".tmp")
    temporary.unlink(missing_ok=True)
    connection = sqlite3.connect(temporary)
    try:
        connection.executescript(PFS_SCHEMA)
        connection.execute(
            """
            INSERT INTO picture (
                filename, width, height,
                start_left, start_top, start_width, start_height,
                target_left, target_top, target_width, target_height,
                rotation, duration, movement, comment, effect,
                transition, transition_duration, data
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(image_path), width, height,
                *plan.start.as_tuple(), *plan.target.as_tuple(),
                0, plan.duration, plan.movement, "", 0,
                0, 0.0, None,
            ),
        )
        properties: list[tuple[str, object]] = [
            ("rev", PFS_SCHEMA_REV),
            ("aspect", aspect),
            ("duration", plan.duration),
            ("timelapse", 0),
        ]
        if audio is not None:
            properties.append(("audiofile", str(audio)))
        connection.executemany("INSERT INTO property (name, value) VALUES (?, ?)", properties)
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
    temporary.replace(project_path)
    return plan


def build_render_command(
    project_path: Path,
    output_dir: Path,
    *,
    profile: int = 0,
    renderer_format: int = 4,
    draft: bool = False,
    binary: str | None = None,
) -> list[str]:
    executable = binary or photofilmstrip_cli_path() or "photofilmstrip-cli"
    command = [
        executable,
        "--project", str(Path(project_path).expanduser().resolve()),
        "--outputpath", str(Path(output_dir).expanduser().resolve()),
        "--profile", str(profile),
        "--format", str(renderer_format),
    ]
    if draft:
        command.append("--draft")
    return command
