from __future__ import annotations

import sys
from pathlib import Path
from unittest import mock

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

import toolchain  # noqa: E402
from toolchain_common import load_contract  # noqa: E402
from videobatch_fast.ffmpeg_capabilities import _parse_encoders  # noqa: E402
from videobatch_fast.validation import validate_runtime  # noqa: E402


def test_ffmpeg_encoder_parser_accepts_real_world_capability_flags() -> None:
    output = """
 Encoders:
  V....D libx264              H.264
  A....D aac                  AAC
  S..... srt                  SubRip subtitle
"""
    assert _parse_encoders(output) == frozenset({"libx264", "aac", "srt"})


def test_startup_codec_failure_is_visible_but_not_start_blocking() -> None:
    with (
        mock.patch("videobatch_fast.validation.ffmpeg_path", return_value="/usr/bin/ffmpeg"),
        mock.patch("videobatch_fast.validation.ffprobe_path", return_value="/usr/bin/ffprobe"),
        mock.patch("videobatch_fast.validation.validate_quick_modes", return_value=[]),
        mock.patch("videobatch_fast.validation.read_ffmpeg_capabilities") as capabilities,
        mock.patch("videobatch_fast.validation.encoder_smoke_test", return_value=(False, "probe failed")),
    ):
        capabilities.return_value.error = ""
        issues = validate_runtime(startup=True)
        strict = validate_runtime()
    aac = next(issue for issue in issues if issue.code == "FFMPEG_AAC_MISSING")
    strict_aac = next(issue for issue in strict if issue.code == "FFMPEG_AAC_MISSING")
    assert aac.blocking is False
    assert strict_aac.blocking is True


def test_runtime_and_quality_environments_are_content_addressed_and_separate(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    contract = load_contract(ROOT)
    runtime = toolchain.environment_path(contract, "runtime")
    quality = toolchain.environment_path(contract, "quality")
    assert runtime != quality
    assert runtime.parent == quality.parent
    assert runtime.name.startswith("runtime-py")
    assert quality.name.startswith("quality-py")
    assert ROOT not in runtime.parents


def test_missing_quality_package_is_reported_without_traceback(monkeypatch: pytest.MonkeyPatch) -> None:
    contract = load_contract(ROOT)
    monkeypatch.setattr(toolchain, "expected_packages", lambda _contract, _scope: {"package-that-does-not-exist-vb": "1.0"})
    with pytest.raises(RuntimeError, match="Pflichtpakete fehlen") as error:
        toolchain.installed_versions(Path(sys.executable), contract, "quality")
    assert "Traceback" not in str(error.value)


def test_launcher_uses_predictive_bootstrap_and_does_not_require_ffmpeg_to_open_ui() -> None:
    launcher = (ROOT / "videobatch.sh").read_text(encoding="utf-8")
    bootstrap = (SCRIPTS / "bootstrap.py").read_text(encoding="utf-8")
    assert 'scripts/debug_launcher.py' in launcher
    assert 'scripts/bootstrap.py' in (SCRIPTS / 'debug_launcher.py').read_text(encoding='utf-8')
    assert 'command -v "$tool"' not in launcher
    assert '"prepare", "--scope", "runtime"' in bootstrap
    assert '"prepare", "--scope", "quality"' not in bootstrap
    assert "subprocess.Popen" in bootstrap
    assert "VIDEOBATCH_UI_READY_FILE" in bootstrap
    assert "os.execve" not in bootstrap


def test_installation_is_created_at_final_content_addressed_path() -> None:
    source = (SCRIPTS / "toolchain.py").read_text(encoding="utf-8")
    assert "venv after creation breaks absolute console-script shebangs" in source
    assert "venv.EnvBuilder" in source
    assert "os.replace(staging, target)" not in source


def test_double_click_and_menu_launchers_are_shipped() -> None:
    assert (ROOT / "STARTEN.sh").is_file()
    assert (ROOT / "VideoBatch-Fast.desktop").is_file()
    assert "Terminal=false" in (ROOT / "VideoBatch-Fast.desktop").read_text(encoding="utf-8")


def test_startup_contract_prevents_future_start_blocker_regressions() -> None:
    import json
    contract = json.loads((ROOT / "STARTUP_CONTRACT.json").read_text(encoding="utf-8"))
    policy = contract["policy"]
    assert policy["interactive_questions_forbidden"] is True
    assert policy["quality_tools_must_not_block_application_start"] is True
    assert policy["ffmpeg_codec_listing_must_not_block_application_start"] is True
    assert policy["real_encoder_smoke_test_is_authoritative"] is True
    assert policy["runtime_environment_must_not_be_moved_after_creation"] is True
    assert policy["maximum_automatic_repair_attempts"] == 2
