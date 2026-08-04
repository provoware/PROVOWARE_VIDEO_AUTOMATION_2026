from __future__ import annotations

import sys
import zipfile
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import build_toolchain_wheelhouse as builder  # noqa: E402
import toolchain_common as common  # noqa: E402


def _wheel(path: Path, name: str, version: str) -> None:
    dist = name.replace("-", "_")
    metadata = f"Metadata-Version: 2.1\nName: {name}\nVersion: {version}\n"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(f"{dist}-{version}.dist-info/METADATA", metadata)


def _complete_fake_wheelhouse(path: Path) -> None:
    contract = common.load_contract(ROOT)
    for name, version in common.expected_packages(contract).items():
        _wheel(path / f"{name.replace('-', '_')}-{version}-py3-none-any.whl", name, version)
    manifest = common.build_manifest(path)
    common.write_manifest(path, manifest)
    common.write_resolved_lock(path, manifest, contract)


def test_resolved_hash_lock_matches_manifest(tmp_path: Path) -> None:
    _complete_fake_wheelhouse(tmp_path)
    contract = common.load_contract(ROOT)
    assert common.verify_wheelhouse(tmp_path, contract) == []
    manifest = __import__("json").loads((tmp_path / common.MANIFEST_NAME).read_text())
    assert (tmp_path / common.RESOLVED_LOCK_NAME).read_text() == common.resolved_lock_text(manifest)


def test_tampered_resolved_hash_lock_is_rejected(tmp_path: Path) -> None:
    _complete_fake_wheelhouse(tmp_path)
    lock = tmp_path / common.RESOLVED_LOCK_NAME
    lock.write_text(lock.read_text() + "tampered\n")
    errors = common.verify_wheelhouse(tmp_path, common.load_contract(ROOT))
    assert any("Hash-Lockfile" in error for error in errors)


def test_low_level_online_index_requires_explicit_environment_consent(tmp_path: Path) -> None:
    argv = ["build_toolchain_wheelhouse.py", "--output", str(tmp_path), "--index-url", "https://pypi.org/simple"]
    with mock.patch.object(sys, "argv", argv), mock.patch.dict("os.environ", {}, clear=True):
        assert builder.main() == 4
