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


def test_pillow_13_contract_matches_python_support_and_locks() -> None:
    import tomllib
    from PIL import __version__ as pillow_version

    contract = common.load_contract(ROOT)
    assert contract["packages"]["runtime"]["Pillow"] == "13.0.0"
    assert common.read_exact_lock(ROOT / "config/requirements/requirements.lock")["pillow"] == "13.0.0"
    assert common.read_exact_lock(ROOT / "config/requirements/requirements-toolchain.lock")["pillow"] == "13.0.0"
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    assert project["requires-python"] == ">=3.11"
    assert "Pillow==13.0.0" in project["dependencies"]
    assert pillow_version == "13.0.0"


def test_pillow_13_png_preview_and_thumbnail_roundtrip() -> None:
    from io import BytesIO

    from PIL import Image, ImageOps

    source = Image.new("RGBA", (16, 12), (20, 70, 120, 160))
    stream = BytesIO()
    source.save(stream, format="PNG")
    stream.seek(0)
    with Image.open(stream) as restored:
        restored.load()
        assert restored.mode == "RGBA"
        assert restored.size == (16, 12)
        assert restored.getpixel((0, 0)) == (20, 70, 120, 160)
        reduced = ImageOps.contain(restored, (8, 8), method=Image.Resampling.LANCZOS)
        assert reduced.size == (8, 6)


def test_pillow_13_jpeg_encode_decode_roundtrip() -> None:
    from io import BytesIO

    from PIL import Image

    source = Image.new("RGB", (12, 8), (30, 100, 180))
    stream = BytesIO()
    source.save(stream, format="JPEG", quality=92)
    stream.seek(0)
    with Image.open(stream) as restored:
        restored.load()
        assert restored.format == "JPEG"
        assert restored.mode == "RGB"
        assert restored.size == source.size
