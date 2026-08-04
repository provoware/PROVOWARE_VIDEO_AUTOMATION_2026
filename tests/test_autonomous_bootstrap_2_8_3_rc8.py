from __future__ import annotations

import subprocess
import sys
import zipfile
from pathlib import Path
from unittest import mock

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import build_toolchain_wheelhouse as builder  # noqa: E402
import toolchain  # noqa: E402
import toolchain_common as common  # noqa: E402


def _wheel(path: Path, name: str, version: str) -> None:
    dist = name.replace("-", "_")
    metadata = f"Metadata-Version: 2.1\nName: {name}\nVersion: {version}\n"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(f"{dist}-{version}.dist-info/METADATA", metadata)


def _direct_wheels(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    contract = common.load_contract(ROOT)
    for name, version in common.expected_packages(contract).items():
        _wheel(path / f"{name.replace('-', '_')}-{version}-py3-none-any.whl", name, version)


def test_metadata_is_rebuilt_from_downloaded_wheels_without_user_input(tmp_path: Path) -> None:
    wheelhouse = tmp_path / "toolchain_wheelhouse"
    _direct_wheels(wheelhouse)
    contract = common.load_contract(ROOT)
    assert not (wheelhouse / common.MANIFEST_NAME).exists()
    manifest = common.rebuild_wheelhouse_metadata(wheelhouse, contract)
    assert manifest["wheel_count"] == len(common.expected_packages(contract))
    assert common.verify_wheelhouse(wheelhouse, contract) == []


def test_successful_builder_keeps_project_and_publishes_manifest(tmp_path: Path) -> None:
    output = tmp_path / "wheelhouse"

    def fake_run(command, **_kwargs):
        destination = Path(command[command.index("--dest") + 1])
        _direct_wheels(destination)
        return subprocess.CompletedProcess(command, 0, stdout="")

    argv = ["build_toolchain_wheelhouse.py", "--output", str(output), "--index-url", "https://pypi.org/simple"]
    with (
        mock.patch.object(sys, "argv", argv),
        mock.patch.dict("os.environ", {"VIDEOBATCH_ALLOW_PUBLIC_PYPI": "1"}, clear=True),
        mock.patch.object(builder, "preflight", return_value=[]),
        mock.patch.object(builder.subprocess, "run", side_effect=fake_run),
    ):
        assert builder.main() == 0
    assert (output / common.MANIFEST_NAME).is_file()
    assert (ROOT / "videobatch.sh").is_file()


def test_dangerous_cleanup_target_is_blocked(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        common.safe_remove_tree(ROOT, allowed_parent=ROOT.parent)
    assert ROOT.is_dir()


def test_previous_version_wheels_are_imported_automatically(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source = tmp_path / "old" / "toolchain_wheelhouse"
    target = tmp_path / "new" / "toolchain_wheelhouse"
    _direct_wheels(source)
    target.parent.mkdir(parents=True)
    contract = common.load_contract(ROOT)
    monkeypatch.setattr(toolchain, "wheelhouse_path", lambda _contract: target)
    monkeypatch.setattr(toolchain, "candidate_wheelhouses", lambda _contract: iter((target, source)))
    assert toolchain.recover_local_wheelhouse(contract) is True
    assert common.verify_wheelhouse(target, contract) == []


def test_launcher_is_noninteractive_and_visible() -> None:
    text = (ROOT / "videobatch.sh").read_text(encoding="utf-8")
    assert "--auto-repair" in text
    assert "scripts/bootstrap.py" in text
    assert "read -" not in text
    assert "input(" not in (ROOT / "scripts" / "toolchain.py").read_text(encoding="utf-8")
    assert "doctor" in text


def test_help_center_replaces_prototype_messages() -> None:
    dashboard = (ROOT / "src" / "videobatch_fast" / "ui_dashboard_project_mixin.py").read_text(encoding="utf-8")
    components = (ROOT / "src" / "videobatch_fast" / "ui_components.py").read_text(encoding="utf-8")
    texts = (ROOT / "resources" / "texts" / "application.json").read_text(encoding="utf-8")
    assert dashboard.count("command=self._show_help_center") >= 2
    assert "class HelpCenterDialog" in components
    assert 'text("help_center.solve_body")' in components
    assert "clipboard_append(self.status_value.get())" in components
    assert '"help_center.solve_tab": "Problem lösen"' in texts
