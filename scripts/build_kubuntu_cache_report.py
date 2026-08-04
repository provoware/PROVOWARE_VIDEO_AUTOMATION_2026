#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

OS_NAMES = ("ubuntu-22.04", "ubuntu-24.04")


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def format_bytes(value: int) -> str:
    size = float(value)
    for unit in ("B", "KiB", "MiB", "GiB"):
        if size < 1024 or unit == "GiB":
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{value} B"


def parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def newest_time(items: list[dict[str, Any]], field: str) -> str | None:
    values = [parse_time(str(item.get(field) or "")) for item in items]
    valid = [value for value in values if value is not None]
    return max(valid).astimezone(timezone.utc).isoformat() if valid else None


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a readable Kubuntu cache inventory report.")
    parser.add_argument("--metrics-dir", default="warmup-metrics")
    parser.add_argument("--inventory", default="cache-inventory.json")
    args = parser.parse_args()

    metrics: dict[str, dict[str, Any]] = {}
    for path in Path(args.metrics_dir).rglob("CI_PACKAGE_METRICS.json"):
        value = load_json(path)
        if isinstance(value, dict) and value.get("os") in OS_NAMES:
            metrics[str(value["os"])] = value

    inventory_value = load_json(Path(args.inventory))
    caches = inventory_value.get("actions_caches", []) if isinstance(inventory_value, dict) else []
    caches = [item for item in caches if isinstance(item, dict)]

    rows: list[dict[str, Any]] = []
    exact_hits = 0
    hit_checks = 0
    for os_name in OS_NAMES:
        os_metrics = metrics.get(os_name, {})
        apt_items = [item for item in caches if str(item.get("key", "")).startswith(f"apt-v4-{os_name}-")]
        pip_items = [item for item in caches if str(item.get("key", "")).startswith(f"pip-v4-{os_name}-")]
        for field in ("apt_cache_exact_hit", "pip_cache_exact_hit"):
            if field in os_metrics:
                hit_checks += 1
                exact_hits += int(os_metrics.get(field) is True)
        rows.append(
            {
                "os": os_name,
                "apt_count": len(apt_items),
                "apt_bytes": sum(int(item.get("size_in_bytes") or 0) for item in apt_items),
                "apt_last_accessed": newest_time(apt_items, "last_accessed_at"),
                "pip_count": len(pip_items),
                "pip_bytes": sum(int(item.get("size_in_bytes") or 0) for item in pip_items),
                "pip_last_accessed": newest_time(pip_items, "last_accessed_at"),
                "apt_exact_hit": os_metrics.get("apt_cache_exact_hit"),
                "pip_exact_hit": os_metrics.get("pip_cache_exact_hit"),
                "download_summary": os_metrics.get("download_summary", "nicht ermittelt"),
                "apt_seconds": os_metrics.get("apt_seconds"),
                "cache_week": os_metrics.get("cache_week", "nicht ermittelt"),
            }
        )

    report = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "run_id": os.environ.get("GITHUB_RUN_ID", "unknown"),
        "current_exact_hit_ratio": exact_hits / hit_checks if hit_checks else None,
        "current_exact_hits": exact_hits,
        "current_hit_checks": hit_checks,
        "total_matching_cache_bytes": sum(row["apt_bytes"] + row["pip_bytes"] for row in rows),
        "systems": rows,
    }
    Path("KUBUNTU_CACHE_STATUS.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    ratio = "nicht ermittelt" if not hit_checks else f"{exact_hits}/{hit_checks} ({exact_hits / hit_checks:.0%})"
    lines = [
        "# 🟢 Kubuntu-Cache-Zustand",
        "",
        f"**Aktueller exakter Trefferanteil:** {ratio}",
        f"**Gesamtgröße der passenden Caches:** {format_bytes(report['total_matching_cache_bytes'])}",
        "",
        "| System | Woche | APT-Caches | APT-Größe | APT letzter Zugriff | Pip-Caches | Pip-Größe | Pip letzter Zugriff | Paketdownload | APT-Dauer |",
        "|---|---|---:|---:|---|---:|---:|---|---:|---:|",
    ]
    for row in rows:
        lines.append(
            f"| {row['os']} | {row['cache_week']} | {row['apt_count']} | {format_bytes(row['apt_bytes'])} | "
            f"{row['apt_last_accessed'] or 'nicht ermittelt'} | {row['pip_count']} | {format_bytes(row['pip_bytes'])} | "
            f"{row['pip_last_accessed'] or 'nicht ermittelt'} | {row['download_summary']} | {row['apt_seconds'] if row['apt_seconds'] is not None else '–'} s |"
        )
    lines.extend(
        [
            "",
            "## Einfache Einordnung",
            "",
            "- **Exakter Treffer:** Der Vorrat dieser Kalenderwoche wurde direkt verwendet.",
            "- **Älterer Treffer:** Ein vorhandener Vorrat wurde übernommen und als aktuelle Woche erneuert.",
            "- **Kein Treffer:** Der Vorrat wurde neu aufgebaut; das ist beim ersten Lauf normal.",
            "- Der Bericht löscht keine Caches. Er macht Alter, Größe und Nutzung nur transparent.",
        ]
    )
    markdown = "\n".join(lines) + "\n"
    Path("KUBUNTU_CACHE_STATUS.md").write_text(markdown, encoding="utf-8")
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with Path(summary_path).open("a", encoding="utf-8") as handle:
            handle.write(markdown)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
