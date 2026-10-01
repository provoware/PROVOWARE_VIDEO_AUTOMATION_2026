import sqlite3
from pathlib import Path

from PIL import Image

from videobatch_fast.motion_planner import preset
from videobatch_fast.photofilmstrip_adapter import build_render_command, write_pfs_project


def _image(path: Path) -> None:
    Image.new("RGB", (1600, 900), "black").save(path)


def test_write_pfs_project_uses_upstream_schema_and_motion(tmp_path: Path) -> None:
    image = tmp_path / "photo.jpg"
    audio = tmp_path / "audio.wav"
    project = tmp_path / "demo.pfs"
    _image(image)
    audio.write_bytes(b"RIFF-test")

    plan = write_pfs_project(project, image, preset("zoom_in", duration=6.0), audio_path=audio)

    assert project.is_file()
    with sqlite3.connect(project) as connection:
        row = connection.execute(
            "SELECT filename, width, height, start_width, start_height, target_width, target_height, duration, movement "
            "FROM picture"
        ).fetchone()
        props = dict(connection.execute("SELECT name, value FROM property").fetchall())
    assert row[0] == str(image.resolve())
    assert row[1:3] == (1600, 900)
    assert row[3:5] == (plan.start.width, plan.start.height)
    assert row[5:7] == (plan.target.width, plan.target.height)
    assert row[7] == 6.0
    assert row[8] == 1
    assert props["rev"] == "4"
    assert props["aspect"] == "16:9"
    assert props["audiofile"] == str(audio.resolve())


def test_build_render_command_is_cli_only_and_deterministic(tmp_path: Path) -> None:
    command = build_render_command(
        tmp_path / "demo.pfs",
        tmp_path / "out",
        profile=2,
        renderer_format=4,
        draft=True,
        binary="/usr/bin/photofilmstrip-cli",
    )
    assert command == [
        "/usr/bin/photofilmstrip-cli",
        "--project", str((tmp_path / "demo.pfs").resolve()),
        "--outputpath", str((tmp_path / "out").resolve()),
        "--profile", "2",
        "--format", "4",
        "--draft",
    ]
