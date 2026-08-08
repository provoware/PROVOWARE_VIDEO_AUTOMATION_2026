#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

EXPECTED = (
    ("ubuntu-22.04", "x11"),
    ("ubuntu-24.04", "x11"),
)


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def version_from_file() -> str:
    data = load_json(Path("VERSION.json"))
    return str(data.get("version") or data.get("build") or "unknown")


def append_output(name: str, value: str) -> None:
    output = os.environ.get("GITHUB_OUTPUT")
    if not output:
        return
    with Path(output).open("a", encoding="utf-8") as handle:
        handle.write(f"{name}={value}\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the consolidated Kubuntu matrix report.")
    parser.add_argument("--status-dir", default="matrix-status")
    parser.add_argument("--report-issue", required=True, type=int)
    parser.add_argument("--matrix-job-result", default="unknown")
    args = parser.parse_args()

    status_dir = Path(args.status_dir)
    records: dict[tuple[str, str], dict[str, Any]] = {}
    for path in status_dir.glob("matrix-status-*.json"):
        record = load_json(path)
        records[(str(record.get("os")), str(record.get("session")))] = record

    rows: list[dict[str, Any]] = []
    for os_name, session in EXPECTED:
        record = records.get((os_name, session), {})
        status = str(record.get("status", "missing"))
        rows.append(
            {
                "os": os_name,
                "session": session,
                "status": status,
                "symbol": "✅" if status == "success" else "❌",
                "media_toolchain": record.get("media_toolchain", {}),
                "package_metrics": record.get("package_metrics", {}),
            }
        )

    all_success = all(row["status"] == "success" for row in rows)
    run_id = os.environ.get("GITHUB_RUN_ID", "unknown")
    repository = os.environ.get("GITHUB_REPOSITORY", "unknown/unknown")
    run_url = f"https://github.com/{repository}/actions/runs/{run_id}"
    version = version_from_file()
    summary = {
        "schema_version": 4,
        "version": version,
        "status": "passed" if all_success else "failed",
        "report_issue": args.report_issue,
        "matrix_job_result": args.matrix_job_result,
        "run_id": run_id,
        "run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT", "unknown"),
        "run_url": run_url,
        "commit": os.environ.get("GITHUB_SHA", "unknown"),
        "results": [
            {
                "os": row["os"],
                "session": row["session"],
                "status": row["status"],
                "media_toolchain": row["media_toolchain"],
                "package_metrics": row["package_metrics"],
            }
            for row in rows
        ],
    }
    Path("KUBUNTU_MATRIX_SUMMARY.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    lines = [
        f"## Kubuntu-Kompatibilitätsmatrix {version}",
        "",
        f"Workflow-Lauf: [{run_id}]({run_url})",
        f"Commit: `{summary['commit']}`",
        "",
        "| System | Sitzung | Ergebnis | Paketvorrat | Paketdownload | APT-Dauer | FFmpeg-Paket |",
        "|---|---|---|---|---:|---:|---|",
    ]
    for row in rows:
        toolchain = row["media_toolchain"] if isinstance(row["media_toolchain"], dict) else {}
        metrics = row["package_metrics"] if isinstance(row["package_metrics"], dict) else {}
        package = toolchain.get("package", {}) if isinstance(toolchain.get("package"), dict) else {}
        cache_state = (
            "aktuelle Woche"
            if metrics.get("apt_cache_exact_hit") is True
            else "älterer Vorrat"
            if metrics.get("apt_cache_restored") is True
            else "neu aufgebaut"
        )
        lines.append(
            f"| {row['os']} | {row['session']} | {row['symbol']} `{row['status']}` | "
            f"{cache_state} | {metrics.get('download_summary', 'nicht ermittelt')} | "
            f"{metrics.get('apt_seconds', '–')} s | `{package.get('version', 'nicht ermittelt')}` |"
        )

    lines.extend(["", "### Medienwerkzeug-Nachweise", ""])
    for row in rows:
        toolchain = row["media_toolchain"] if isinstance(row["media_toolchain"], dict) else {}
        ffmpeg = toolchain.get("ffmpeg", {}) if isinstance(toolchain.get("ffmpeg"), dict) else {}
        ffprobe = toolchain.get("ffprobe", {}) if isinstance(toolchain.get("ffprobe"), dict) else {}
        lines.extend(
            [
                f"**{row['os']} / {row['session']}**",
                "",
                f"- FFmpeg: `{ffmpeg.get('version', 'nicht ermittelt')}`",
                f"- FFmpeg-Pfad: `{ffmpeg.get('path', 'nicht ermittelt')}`",
                f"- FFmpeg-SHA-256: `{ffmpeg.get('sha256', 'nicht ermittelt')}`",
                f"- ffprobe: `{ffprobe.get('version', 'nicht ermittelt')}`",
                f"- ffprobe-Pfad: `{ffprobe.get('path', 'nicht ermittelt')}`",
                f"- ffprobe-SHA-256: `{ffprobe.get('sha256', 'nicht ermittelt')}`",
                "",
            ]
        )

    lines.extend(
        [
            "**Gesamtergebnis: bestanden.**"
            if all_success
            else "**Gesamtergebnis: nicht vollständig bestanden.**",
            "",
            "Die vollständigen Nachweise liegen 30 Tage als Workflow-Artefakte vor.",
        ]
    )
    Path("KUBUNTU_MATRIX_SUMMARY.md").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )
    append_output("all_success", "true" if all_success else "false")
    append_output("version", version)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
