from __future__ import annotations

import importlib.util
from pathlib import Path

from videobatch_fast.startup_handshake import read_ready_marker, signal_ui_ready

ROOT = Path(__file__).resolve().parents[1]


def test_current_ready_marker_schema_is_readable(monkeypatch, tmp_path: Path) -> None:
    marker = tmp_path / "ui-ready.json"
    monkeypatch.setenv("VIDEOBATCH_UI_READY_FILE", str(marker))
    monkeypatch.setenv("VIDEOBATCH_SAFE_MODE", "0")
    monkeypatch.setenv("VIDEOBATCH_STARTUP_STATUS", "ready")

    written = signal_ui_ready()
    assert written == marker

    payload = read_ready_marker(marker)
    assert payload is not None
    assert payload["schema_version"] == 2
    assert payload["safe_mode"] is False
    assert payload["startup_status"] == "ready"


def test_bootstrap_uses_the_canonical_ready_marker_reader() -> None:
    source = (ROOT / "scripts/bootstrap.py").read_text(encoding="utf-8")
    assert "from videobatch_fast.startup_handshake import read_ready_marker" in source
    assert "payload = read_ready_marker(marker)" in source
    assert "def _read_ready_marker" not in source
    assert 'payload.get("schema_version") != 1' not in source


def test_debug_launcher_classifies_ready_timeout_as_error(monkeypatch, tmp_path: Path) -> None:
    path = ROOT / "scripts/debug_launcher.py"
    spec = importlib.util.spec_from_file_location("videobatch_debug_launcher_contract", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("debug_launcher.py konnte für den Vertragstest nicht geladen werden")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    calls: list[tuple[tuple[object, ...], dict[str, object]]] = []

    def record(*args, **kwargs) -> None:
        calls.append((args, kwargs))

    monkeypatch.setattr(module.RUNTIME, "verbose", record)
    log = tmp_path / "bootstrap.log"
    log.write_text("UI_READY TIMEOUT safe_mode=False\n", encoding="utf-8")

    module._stream_file(log, 0, prefix="BOOTSTRAP")

    assert len(calls) == 1
    args, kwargs = calls[0]
    assert args[0] == "Ein Startfehler wurde erkannt."
    assert args[1] == "UI_READY TIMEOUT safe_mode=False"
    assert kwargs["level"] == "FEHLER"
