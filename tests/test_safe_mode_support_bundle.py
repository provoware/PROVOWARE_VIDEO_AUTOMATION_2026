from __future__ import annotations

import hashlib
import json
import stat
import zipfile
from pathlib import Path

import pytest

from videobatch_fast.preparation_assistant import PreparationCheck
from videobatch_fast import support_bundle

ROOT = Path(__file__).resolve().parents[1]


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _prepare_evidence(monkeypatch, tmp_path: Path, *, normal_failed: bool = False):
    project = tmp_path / "project"
    project.mkdir()
    (project / "VERSION.json").write_text(
        '{"version":"2.8.3","build":"2.8.3-test"}\n', encoding="utf-8"
    )
    (project / "RELEASE_MANIFEST.json").write_text(
        '{"schema_version":1,"build":"2.8.3-test"}\n', encoding="utf-8"
    )
    startup = tmp_path / "latest.json"
    startup.write_text('{"status":"degraded","steps":[]}\n', encoding="utf-8")
    application = tmp_path / "application_safe.log"
    application.write_text("SAFE APPLICATION LOG\n", encoding="utf-8")
    bootstrap = tmp_path / "bootstrap.log"
    lines = ["SYSTEM RUNTIME FALLBACK VERIFIED"]
    if normal_failed:
        lines.append("NORMAL START FAILED: UI wurde vor Bereitschaft beendet")
    lines.append(f"APPLICATION ATTEMPT safe_mode=True log={application}")
    bootstrap.write_text("\n".join(lines) + "\n", encoding="utf-8")
    debug_dir = tmp_path / "debugging"
    debug_dir.mkdir()
    debug_report = debug_dir / "ABSTURZ_test.txt"
    debug_report.write_text("DEBUG REPORT\n", encoding="utf-8")

    monkeypatch.setattr(support_bundle, "PROJECT_ROOT", project)
    monkeypatch.setenv("VIDEOBATCH_SAFE_MODE", "1")
    monkeypatch.setenv("VIDEOBATCH_STARTUP_STATUS", "degraded")
    monkeypatch.setenv("VIDEOBATCH_BOOTSTRAP_LOG", str(bootstrap))
    monkeypatch.setenv("VIDEOBATCH_STARTUP_REPORT", str(startup))
    monkeypatch.setenv("VIDEOBATCH_DEBUG_DIR", str(debug_dir))
    monkeypatch.delenv("VIDEOBATCH_APPLICATION_LOG", raising=False)
    monkeypatch.delenv("VIDEOBATCH_SAFE_MODE_REASON", raising=False)
    monkeypatch.delenv("VIDEOBATCH_SAFE_MODE_REASON_CODE", raising=False)
    return bootstrap, startup, application, debug_report


def test_safe_mode_bundle_is_read_only_and_preserves_sources(monkeypatch, tmp_path: Path) -> None:
    sources = _prepare_evidence(monkeypatch, tmp_path)
    before = {path: _sha(path) for path in sources}
    checks = [
        PreparationCheck("audio", "error", "Audiodateien", "Noch keine Audiodatei", "add_audio"),
        PreparationCheck("output", "ok", "Ausgabeordner", "/tmp"),
    ]

    target = tmp_path / "VideoBatch_SafeMode_Diagnose.zip"
    written = support_bundle.export_safe_mode_support_bundle(
        target,
        checks=checks,
        context={"Projekt": "Sicherer Start", "Safe-Mode": True},
    )

    assert written == target
    assert target.is_file()
    assert not (target.stat().st_mode & stat.S_IWUSR)
    assert {path: _sha(path) for path in sources} == before

    with zipfile.ZipFile(target) as archive:
        names = set(archive.namelist())
        assert "safe_mode/cause.json" in names
        assert "startup/latest.json" in names
        assert "startup/live_preparation_checks.json" in names
        assert "logs/bootstrap.log" in names
        assert "logs/application.log" in names
        assert any(name.startswith("logs/debug/") for name in names)
        assert "version/VERSION.json" in names
        assert "version/RELEASE_MANIFEST.json" in names
        assert "version/runtime.json" in names
        assert "manifest.json" in names

        cause = json.loads(archive.read("safe_mode/cause.json"))
        assert cause["reason_code"] == "runtime_fallback"
        assert cause["active"] is True

        live = json.loads(archive.read("startup/live_preparation_checks.json"))
        assert live[0]["status"] == "error"
        manifest = json.loads(archive.read("manifest.json"))
        assert manifest["read_only"] is True
        manifest_paths = {item["path"] for item in manifest["files"]}
        assert "logs/bootstrap.log" in manifest_paths

        for info in archive.infolist():
            if info.is_dir():
                continue
            mode = info.external_attr >> 16
            assert mode & stat.S_IRUSR
            assert not mode & stat.S_IWUSR


def test_normal_start_failure_wins_over_runtime_fallback(monkeypatch, tmp_path: Path) -> None:
    _prepare_evidence(monkeypatch, tmp_path, normal_failed=True)
    target = tmp_path / "diagnose.zip"
    support_bundle.export_safe_mode_support_bundle(target)
    with zipfile.ZipFile(target) as archive:
        cause = json.loads(archive.read("safe_mode/cause.json"))
    assert cause["reason_code"] == "normal_start_failed"
    assert "UI wurde vor Bereitschaft beendet" in cause["reason"]


def test_export_is_rejected_outside_safe_mode(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("VIDEOBATCH_SAFE_MODE", "0")
    with pytest.raises(support_bundle.SupportBundleError):
        support_bundle.export_safe_mode_support_bundle(tmp_path / "diagnose.zip")


def test_safe_mode_button_is_conditional_and_uses_existing_debug_surface() -> None:
    source = (ROOT / "src/videobatch_fast/canonical_debug_mixin.py").read_text(encoding="utf-8")
    assert "if self.safe_mode:" in source
    assert "Diagnose exportieren" in source
    assert "export_safe_mode_support_bundle" in source
    assert "_build_safe_mode_support_export" in source
