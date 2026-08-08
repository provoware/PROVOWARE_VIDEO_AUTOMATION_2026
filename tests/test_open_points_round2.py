from __future__ import annotations

import json
from pathlib import Path

from videobatch_fast.canonical_kpi import build_kpi_snapshots
from videobatch_fast.startup_handshake import signal_ui_ready

ROOT = Path(__file__).resolve().parents[1]


def test_ready_marker_persists_structured_start_timing(tmp_path: Path, monkeypatch) -> None:
    marker = tmp_path / "ready.json"
    monkeypatch.setenv("VIDEOBATCH_UI_READY_FILE", str(marker))
    signal_ui_ready(
        timing_ms={
            "launch_to_run_app": 12.3456,
            "tk_create": 20.0,
            "ui_construct": 310.125,
            "first_idle_flush": 4.5,
            "launch_to_ready": 347.0,
        }
    )
    payload = json.loads(marker.read_text(encoding="utf-8"))
    assert payload["schema_version"] == 2
    assert payload["timing_ms"]["ui_construct"] == 310.125
    assert payload["timing_ms"]["launch_to_run_app"] == 12.346


def test_media_kpi_can_show_real_image_video_audio_split() -> None:
    snapshot = build_kpi_snapshots(
        audio_count=2,
        media_count=7,
        image_count=4,
        video_count=3,
        missing_sources=0,
        job_count=0,
        completed_jobs=0,
        failed_jobs=0,
        active_tasks=(),
        visual_effect="none",
        transition="none",
        quick_mode="smart_auto",
    )["media"]
    assert snapshot.detail == "4 Bilder · 3 Videos · 2 Audio"


def test_queue_kpi_reports_waiting_and_completed_without_fake_values() -> None:
    snapshot = build_kpi_snapshots(
        audio_count=1,
        media_count=1,
        missing_sources=0,
        job_count=5,
        completed_jobs=2,
        failed_jobs=0,
        active_tasks=(),
        visual_effect="none",
        transition="none",
        quick_mode="smart_auto",
    )["queue"]
    assert snapshot.detail == "3 wartend · 2 abgeschlossen"


def test_dashboard_queue_has_real_status_filter_and_preview_controls() -> None:
    dashboard = (ROOT / "src" / "videobatch_fast" / "canonical_dashboard_mixin.py").read_text(encoding="utf-8")
    details = (ROOT / "src" / "videobatch_fast" / "canonical_dashboard_detail_mixin.py").read_text(encoding="utf-8")
    assert 'values=("Alle", "Wartend", "Fertig", "Fehler")' in dashboard
    assert 'status_filter != "Alle" and status != status_filter' in dashboard
    for label in ('text="−"', 'text="Einpassen"', 'text="+"', 'text="Vollbild"'):
        assert label in details
