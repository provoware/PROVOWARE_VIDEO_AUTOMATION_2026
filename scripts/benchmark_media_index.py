#!/usr/bin/env python3
"""Repeatable temporary-tree benchmark of the media-only index (no FFmpeg).

Usage:
  PYTHONPATH=src python scripts/benchmark_media_index.py --count 100000
Only generated files inside a temporary directory are touched.
"""
from __future__ import annotations

import argparse
import json
import os
import resource
import tempfile
import time
from pathlib import Path

from videobatch_fast.media_index import MediaIndex


def benchmark(count: int) -> dict[str, int | float | str]:
    if not 1 <= count <= 100_000:
        raise ValueError("Anzahl muss zwischen 1 und 100000 liegen")
    with tempfile.TemporaryDirectory(prefix="videobatch-index-bench-") as folder:
        base = Path(folder)
        roots = {key: base / key for key in ("videos", "downloads", "pictures")}
        for directory in roots.values():
            directory.mkdir()
        downloads = roots["downloads"]
        media_files = []
        creation_start = time.monotonic()
        for number in range(count):
            ext = ".png" if number % 5 == 0 else ".py"
            target = downloads / f"item-{number:06d}{ext}"
            target.touch()
            if ext == ".png":
                media_files.append(target)
        creation_seconds = time.monotonic() - creation_start

        index = MediaIndex(database=base / "cache" / "index.sqlite3", roots=roots)
        started = time.monotonic()
        first = index.refresh_root("downloads")
        cold_seconds = time.monotonic() - started
        started = time.monotonic()
        warm = index.refresh_root("downloads")
        warm_seconds = time.monotonic() - started
        expected = len(media_files)
        if not first.complete or first.added != expected:
            raise AssertionError(f"Ersteinlesung unvollständig: {first}")
        if not warm.complete or warm.unchanged != expected or warm.changed:
            raise AssertionError(f"Unveränderter Ordner wurde neu indexiert: {warm}")

        modified = media_files[: min(10, len(media_files))]
        stamp = time.time_ns() + 2_000_000_000
        for number, path in enumerate(modified):
            os.utime(path, ns=(stamp + number, stamp + number))
        started = time.monotonic()
        changed = index.refresh_root("downloads")
        changed_seconds = time.monotonic() - started
        if not changed.complete or changed.changed != len(modified):
            raise AssertionError(f"Änderungsprüfung unvollständig: {changed}")
        current = index.cached_directory(downloads, limit=max(1, expected))
        if len(current) != expected:
            raise AssertionError("Gespeicherter Medienbestand stimmt nicht")
        peak_kib = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
        return {
            "schema_version": 1,
            "status": "passed",
            "directory_entries": count,
            "media_entries": expected,
            "ignored_nonmedia_entries": count - expected,
            "creation_seconds": round(creation_seconds, 3),
            "first_scan_seconds": round(cold_seconds, 3),
            "unchanged_scan_seconds": round(warm_seconds, 3),
            "changed_scan_seconds": round(changed_seconds, 3),
            "media_modified": len(modified),
            "first_scan_entries_per_second": round(count / max(cold_seconds, 1e-9)),
            "warm_scan_entries_per_second": round(count / max(warm_seconds, 1e-9)),
            "peak_process_rss_kib": peak_kib,
        }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count", type=int, default=10000)
    args = parser.parse_args()
    print(json.dumps(benchmark(args.count), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
