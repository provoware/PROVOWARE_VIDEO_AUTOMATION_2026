import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run_script(script: str, args: list[str], cwd: Path, env: dict[str, str]) -> None:
    subprocess.run(
        [sys.executable, str(ROOT / "scripts" / script), *args],
        cwd=cwd,
        env={**os.environ, **env},
        check=True,
        text=True,
    )


def test_status_writer_includes_package_metrics(tmp_path: Path) -> None:
    (tmp_path / "FFMPEG_TOOLCHAIN.json").write_text(
        json.dumps({"package": {"version": "1.2.3"}}),
        encoding="utf-8",
    )
    (tmp_path / "CI_PACKAGE_METRICS.json").write_text(
        json.dumps({"apt_seconds": 42, "download_summary": "0 B/206 MB"}),
        encoding="utf-8",
    )
    run_script(
        "write_kubuntu_matrix_status.py",
        ["--os", "ubuntu-22.04", "--session", "x11", "--status", "success"],
        tmp_path,
        {
            "GITHUB_RUN_ID": "123",
            "GITHUB_RUN_ATTEMPT": "1",
            "GITHUB_SHA": "abc",
            "GITHUB_WORKFLOW": "test",
        },
    )
    value = json.loads(
        (tmp_path / "matrix-status-ubuntu-22.04-x11.json").read_text(encoding="utf-8")
    )
    assert value["schema_version"] == 3
    assert value["package_metrics"]["apt_seconds"] == 42
    assert value["media_toolchain"]["package"]["version"] == "1.2.3"


def test_matrix_report_requires_all_four_successes(tmp_path: Path) -> None:
    (tmp_path / "VERSION.json").write_text(
        json.dumps({"version": "2.8.3-rc24"}),
        encoding="utf-8",
    )
    status_dir = tmp_path / "matrix-status"
    status_dir.mkdir()
    for os_name in ("ubuntu-22.04", "ubuntu-24.04"):
        for session in ("x11", "wayland"):
            record = {
                "os": os_name,
                "session": session,
                "status": "success",
                "media_toolchain": {"package": {"version": "ffmpeg-test"}},
                "package_metrics": {
                    "apt_cache_exact_hit": True,
                    "download_summary": "0 B/206 MB",
                    "apt_seconds": 45,
                },
            }
            (status_dir / f"matrix-status-{os_name}-{session}.json").write_text(
                json.dumps(record),
                encoding="utf-8",
            )
    output = tmp_path / "github-output.txt"
    run_script(
        "build_kubuntu_matrix_report.py",
        ["--status-dir", str(status_dir), "--report-issue", "12", "--matrix-job-result", "success"],
        tmp_path,
        {
            "GITHUB_RUN_ID": "456",
            "GITHUB_RUN_ATTEMPT": "1",
            "GITHUB_REPOSITORY": "provoware/test",
            "GITHUB_SHA": "def",
            "GITHUB_OUTPUT": str(output),
        },
    )
    report = json.loads((tmp_path / "KUBUNTU_MATRIX_SUMMARY.json").read_text(encoding="utf-8"))
    markdown = (tmp_path / "KUBUNTU_MATRIX_SUMMARY.md").read_text(encoding="utf-8")
    assert report["status"] == "passed"
    assert len(report["results"]) == 4
    assert "0 B/206 MB" in markdown
    assert "all_success=true" in output.read_text(encoding="utf-8")


def test_cache_report_is_read_only_and_explains_inventory(tmp_path: Path) -> None:
    metrics_dir = tmp_path / "warmup-metrics"
    for os_name, seconds in (("ubuntu-22.04", 40), ("ubuntu-24.04", 50)):
        target = metrics_dir / os_name
        target.mkdir(parents=True)
        (target / "CI_PACKAGE_METRICS.json").write_text(
            json.dumps(
                {
                    "os": os_name,
                    "cache_week": "2026-W32",
                    "apt_cache_exact_hit": True,
                    "pip_cache_exact_hit": True,
                    "download_summary": "0 B/200 MB",
                    "apt_seconds": seconds,
                }
            ),
            encoding="utf-8",
        )
    inventory = {
        "actions_caches": [
            {
                "key": "apt-v4-ubuntu-22.04-hash-2026-W32",
                "size_in_bytes": 1000,
                "last_accessed_at": "2026-08-05T00:00:00Z",
            },
            {
                "key": "pip-v4-ubuntu-22.04-hash-2026-W32",
                "size_in_bytes": 2000,
                "last_accessed_at": "2026-08-05T00:00:00Z",
            },
            {
                "key": "apt-v4-ubuntu-24.04-hash-2026-W32",
                "size_in_bytes": 3000,
                "last_accessed_at": "2026-08-05T00:00:00Z",
            },
            {
                "key": "pip-v4-ubuntu-24.04-hash-2026-W32",
                "size_in_bytes": 4000,
                "last_accessed_at": "2026-08-05T00:00:00Z",
            },
        ]
    }
    inventory_path = tmp_path / "cache-inventory.json"
    inventory_path.write_text(json.dumps(inventory), encoding="utf-8")
    summary = tmp_path / "step-summary.md"
    run_script(
        "build_kubuntu_cache_report.py",
        ["--metrics-dir", str(metrics_dir), "--inventory", str(inventory_path)],
        tmp_path,
        {"GITHUB_RUN_ID": "789", "GITHUB_STEP_SUMMARY": str(summary)},
    )
    report = json.loads((tmp_path / "KUBUNTU_CACHE_STATUS.json").read_text(encoding="utf-8"))
    markdown = (tmp_path / "KUBUNTU_CACHE_STATUS.md").read_text(encoding="utf-8")
    assert report["current_exact_hits"] == 4
    assert report["current_hit_checks"] == 4
    assert report["total_matching_cache_bytes"] == 10000
    assert "Der Bericht löscht keine Caches" in markdown
    assert summary.read_text(encoding="utf-8") == markdown
