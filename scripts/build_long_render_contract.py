#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from videobatch_fast.probe import AUDIO_EXTENSIONS, IMAGE_EXTENSIONS


ROOT = Path(__file__).resolve().parents[1]


def _candidate_version() -> str:
    try:
        payload = json.loads((ROOT / 'VERSION.json').read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f'FEHLER: VERSION.json kann nicht gelesen werden: {exc}') from exc
    candidate = str(payload.get('build') or payload.get('version') or '').strip()
    if not candidate:
        raise SystemExit('FEHLER: VERSION.json enthält weder build noch version.')
    return candidate


def _files(directory: Path, extensions: set[str]) -> list[Path]:
    return sorted(
        (path.resolve() for path in directory.iterdir() if path.is_file() and path.suffix.lower() in extensions),
        key=lambda path: path.name.casefold(),
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Versionsgebundenen Langzeitrender-Vertrag erzeugen.")
    parser.add_argument("--audio-dir", required=True, type=Path)
    parser.add_argument("--image-dir", required=True, type=Path)
    parser.add_argument("--target-dir", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--package", type=Path)
    parser.add_argument("--jobs", type=int, default=96)
    parser.add_argument("--cpu-percent", type=int, default=50)
    parser.add_argument("--memory-mb", type=int, default=4096)
    parser.add_argument("--invocation-timeout-hours", type=float, default=10.0)
    parser.add_argument("--total-timeout-hours", type=float, default=20.0)
    parser.add_argument("--heartbeat-minutes", type=float, default=15.0)
    return parser


def main() -> int:
    args = _parser().parse_args()
    if args.jobs < 2:
        raise SystemExit("FEHLER: Mindestens zwei Aufträge sind erforderlich.")
    audio_dir = args.audio_dir.expanduser().resolve()
    image_dir = args.image_dir.expanduser().resolve()
    if not audio_dir.is_dir() or not image_dir.is_dir():
        raise SystemExit("FEHLER: Audio- und Bildordner müssen existieren.")
    audio = _files(audio_dir, AUDIO_EXTENSIONS)
    images = _files(image_dir, IMAGE_EXTENSIONS)
    if len(audio) < args.jobs:
        raise SystemExit(f"FEHLER: {args.jobs} Audiodateien erforderlich, gefunden: {len(audio)}")
    if len(images) < args.jobs * 2:
        raise SystemExit(f"FEHLER: {args.jobs * 2} Bilder erforderlich, gefunden: {len(images)}")
    selected_audio = audio[: args.jobs]
    selected_images = images[: args.jobs * 2]
    jobs = [
        {
            "id": f"{index + 1:03d}",
            "audio": str(selected_audio[index]),
            "media": [str(selected_images[index * 2]), str(selected_images[index * 2 + 1])],
            "output": f"long-render-{index + 1:03d}.mp4",
        }
        for index in range(args.jobs)
    ]
    payload = {
        "schema_version": 1,
        "candidate": _candidate_version(),
        "package": str(args.package.expanduser().resolve()) if args.package else "",
        "target_dir": str(args.target_dir.expanduser().resolve()),
        "limits": {
            "cpu_percent": args.cpu_percent,
            "memory_mb": args.memory_mb,
            "invocation_timeout_seconds": int(args.invocation_timeout_hours * 3600),
            "total_timeout_seconds": int(args.total_timeout_hours * 3600),
            "heartbeat_seconds": int(args.heartbeat_minutes * 60),
        },
        "target": {
            "require_external": True,
            "required_filesystem": "ext4",
            "max_write_mib_s": 35.0,
            "min_free_gib": 500.0,
            "require_hard_limits": True,
        },
        "options": {
            "resolution": "1920×1080",
            "codec": "libx264",
            "profile": "balanced",
            "fps": 25,
            "audio_bitrate": "192k",
            "visual_effect": "none",
            "transition": "none",
            "slideshow_transition": "none",
            "slideshow_scene_sync": False,
        },
        "jobs": jobs,
    }
    output = args.output.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        with output.open("x", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
    except FileExistsError as exc:
        raise SystemExit(f"FEHLER: Vertragsdatei existiert bereits und wird nicht überschrieben: {output}") from exc
    print(f"LANGZEITRENDER_VERTRAG_ERZEUGT={output}")
    print(f"AUFTRAEGE={len(jobs)}")
    print(f"AUDIODATEIEN={len(selected_audio)}")
    print(f"BILDER={len(selected_images)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
