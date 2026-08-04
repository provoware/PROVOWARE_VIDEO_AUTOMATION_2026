from __future__ import annotations

from pathlib import Path
import subprocess

from PIL import Image

from videobatch_fast.audio_waveform import SceneMarker, analyze_audio, scene_change_points
from videobatch_fast.command_builder import build_command
from videobatch_fast.jobs import build_jobs
from videobatch_fast.models import BatchOptions
from videobatch_fast.slideshow import build_slideshow_plan
from videobatch_fast.slideshow_sequence import (
    ORDER_ALPHABETICAL,
    ORDER_RANDOM,
    move_image,
    order_images,
    reverse_images,
)


def test_ordering_is_deterministic_and_respects_anchors(tmp_path: Path) -> None:
    paths = [tmp_path / name for name in ("c.png", "a.png", "b.png", "z.png")]
    for path in paths:
        Image.new("RGB", (20, 20), "white").save(path)
    ordered = order_images(paths, ORDER_ALPHABETICAL, start_image=paths[2], end_image=paths[3])
    assert ordered[0] == paths[2]
    assert ordered[-1] == paths[3]
    assert [item.name for item in ordered[1:-1]] == ["a.png", "c.png"]
    assert order_images(paths, ORDER_RANDOM, random_seed=77) == order_images(paths, ORDER_RANDOM, random_seed=77)


def test_drag_move_and_reverse_keep_fixed_images(tmp_path: Path) -> None:
    paths = [tmp_path / f"{index}.png" for index in range(5)]
    moved = move_image(paths, 1, 3, start_image=paths[0], end_image=paths[4])
    assert moved[0] == paths[0]
    assert moved[-1] == paths[4]
    assert moved.index(paths[1]) == 3
    reversed_paths = reverse_images(moved, start_image=paths[0], end_image=paths[4])
    assert reversed_paths[0] == paths[0]
    assert reversed_paths[-1] == paths[4]


def test_scene_change_points_are_bounded_and_complete() -> None:
    markers = (
        SceneMarker("Intro", 0.0, "intro"),
        SceneMarker("Beat", 8.0, "beat", 0.7),
        SceneMarker("Ruhe", 23.0, "quiet", 0.6),
        SceneMarker("Drop", 34.0, "drop", 0.95),
        SceneMarker("Outro", 52.0, "outro", 0.8),
    )
    points = scene_change_points(60.0, 8, markers)
    assert len(points) == 9
    assert points[0] == 0.0
    assert points[-1] == 60.0
    assert all(right > left for left, right in zip(points, points[1:]))
    assert any(abs(value - 34.0) < 0.1 for value in points)


def test_scene_plan_preserves_exact_audio_duration() -> None:
    markers = (
        SceneMarker("Beat", 5.0, "beat"),
        SceneMarker("Drop", 18.0, "drop"),
        SceneMarker("Outro", 27.0, "outro"),
    )
    plan = build_slideshow_plan(30.0, 6, "soft", scene_markers=markers, scene_sync=True)
    assert plan is not None
    assert plan.scene_aligned
    assert len(plan.input_durations) == 6
    assert len(plan.change_points) == 7
    assert abs(plan.total_duration - 30.0) < 0.02
    assert len(set(plan.visible_durations)) > 1


def test_waveform_analysis_and_scene_synced_real_render(tmp_path: Path) -> None:
    audio = tmp_path / "audio.wav"
    subprocess.run(
        [
            "ffmpeg", "-v", "error", "-y",
            "-f", "lavfi", "-i", "sine=frequency=220:duration=1.2",
            "-f", "lavfi", "-i", "sine=frequency=660:duration=1.2",
            "-filter_complex", "[0:a]volume=0.15[a0];[1:a]volume=0.9[a1];[a0][a1]concat=n=2:v=0:a=1[out]",
            "-map", "[out]", str(audio),
        ],
        check=True,
    )
    analysis = analyze_audio(audio, points=240, refresh=True)
    assert analysis.duration > 2.2
    assert len(analysis.peaks) >= 160
    assert any(marker.kind == "drop" for marker in analysis.markers)

    images = []
    for index, color in enumerate(("red", "green", "blue")):
        path = tmp_path / f"image-{index}.png"
        Image.new("RGB", (320, 180), color).save(path)
        images.append(path)
    options = BatchOptions(
        output_dir=tmp_path,
        overwrite=True,
        profile="turbo",
        assignment_mode="all_images_each_audio",
        slideshow_transition="soft",
        slideshow_scene_sync=True,
    )
    jobs = build_jobs([audio], images, options, scene_analyses={audio: analysis})
    assert len(jobs) == 1
    assert jobs[0].scene_markers
    assert len(jobs[0].slide_durations) == 3
    command = build_command(jobs[0], options)
    subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=60)
    assert jobs[0].output.is_file()
    assert jobs[0].output.stat().st_size > 10_000


def test_scene_points_remain_strict_for_very_short_audio() -> None:
    for duration in (0.2, 0.5, 1.0, 2.0):
        for image_count in (2, 5, 10, 20):
            points = scene_change_points(duration, image_count, ())
            assert len(points) == image_count + 1
            assert points[0] == 0.0
            assert points[-1] == duration
            assert all(right > left for left, right in zip(points, points[1:]))


def test_waveform_points_are_bounded_and_cache_rejects_invalid_payload(tmp_path: Path, monkeypatch) -> None:
    import json
    from videobatch_fast import audio_waveform

    audio = tmp_path / "audio.wav"
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "sine=frequency=330:duration=0.4", str(audio)],
        check=True,
    )
    cache_root = tmp_path / "cache"
    monkeypatch.setattr(audio_waveform, "cache_dir", lambda: cache_root)
    analysis = analyze_audio(audio, points=50_000, refresh=True)
    assert 160 <= len(analysis.peaks) <= 1800

    stat = audio.resolve().stat()
    cache_path = audio_waveform._cache_path(audio.resolve(), stat.st_size, stat.st_mtime_ns, 1800)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(
        json.dumps(
            {
                "source": str(audio.resolve()),
                "size": stat.st_size,
                "modified_ns": stat.st_mtime_ns,
                "duration": analysis.duration,
                "sample_rate": 1000,
                "peaks": [float("nan")],
                "markers": [],
            }
        ),
        encoding="utf-8",
    )
    assert audio_waveform._load_persistent_cache(cache_path, audio.resolve(), stat.st_size, stat.st_mtime_ns) is None
