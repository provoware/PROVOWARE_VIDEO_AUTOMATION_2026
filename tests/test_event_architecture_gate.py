from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parents[1]
SCRIPT = ROOT / "scripts" / "check_event_architecture.py"


def _run(source_root: Path, output: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--source-root", str(source_root), "--output", str(output)],
        text=True,
        capture_output=True,
        check=False,
    )


def test_gate_rejects_direct_event_tuple(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "bad.py").write_text(
        'def publish(self, payload):\n    self.events.put(("job_started", payload))\n',
        encoding="utf-8",
    )
    output = tmp_path / "report.json"
    result = _run(source, output)
    report = json.loads(output.read_text(encoding="utf-8"))

    assert result.returncode == 1
    assert report["findings"][0]["code"] == "ARCH_LEGACY_EVENT_TUPLE"


def test_gate_allows_explicit_legacy_adapter(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "legacy_producer.py").write_text(
        'def publish(self, payload):\n    self.events.put_legacy("job_started", payload)\n',
        encoding="utf-8",
    )
    output = tmp_path / "report.json"
    result = _run(source, output)

    assert result.returncode == 0
    assert json.loads(output.read_text(encoding="utf-8"))["findings"] == []


def test_gate_rejects_legacy_factory_bypass(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "bypass.py").write_text(
        'def publish(AppEvent, payload):\n    return AppEvent.from_legacy("job_started", payload)\n',
        encoding="utf-8",
    )
    output = tmp_path / "report.json"
    result = _run(source, output)
    codes = {item["code"] for item in json.loads(output.read_text(encoding="utf-8"))["findings"]}

    assert result.returncode == 1
    assert "ARCH_LEGACY_ADAPTER_BYPASS" in codes


def test_current_source_tree_has_no_uncontrolled_legacy_events(tmp_path: Path) -> None:
    output = tmp_path / "report.json"
    result = _run(ROOT / "src" / "videobatch_fast", output)

    assert result.returncode == 0, result.stdout + result.stderr
