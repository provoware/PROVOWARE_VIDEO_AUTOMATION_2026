from __future__ import annotations

import json
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import toolchain_common as common  # noqa: E402

RUNTIME = {
    "cffi": "2.0.0",
    "cryptography": "50.0.0",
    "pillow": "12.3.0",
    "pycparser": "3.0",
}
QUALITY = {
    "bandit": "1.9.4",
    "coverage": "7.13.3",
    "mypy": "2.3.0",
    "pip-audit": "2.10.1",
    "pytest": "9.0.2",
    "pytest-cov": "7.0.0",
    "ruff": "0.16.1",
}
ALL = {**RUNTIME, **QUALITY}


def _wheel(path: Path, name: str, version: str) -> None:
    dist = name.replace("-", "_")
    metadata = f"Metadata-Version: 2.1\nName: {name}\nVersion: {version}\n"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(f"{dist}-{version}.dist-info/METADATA", metadata)


def _fake_wheelhouse(path: Path, *, root: Path = ROOT) -> dict[str, object]:
    for name, version in ALL.items():
        _wheel(path / f"{name.replace('-', '_')}-{version}-py3-none-any.whl", name, version)
    old_root = common.ROOT
    try:
        common.ROOT = root
        manifest = common.build_manifest(path, root=root)
    finally:
        common.ROOT = old_root
    common.write_manifest(path, manifest)
    common.write_resolved_lock(path, manifest, common.load_contract(root))
    return manifest


def test_unified_contract_matches_all_exact_locks() -> None:
    contract = common.load_contract(ROOT)
    assert contract["release_target"] == json.loads((ROOT / "VERSION.json").read_text(encoding="utf-8"))["build"]
    assert common.expected_packages(contract, "runtime") == RUNTIME
    assert common.expected_packages(contract, "quality") == QUALITY
    assert common.expected_packages(contract, "all") == ALL
    assert common.read_exact_lock(ROOT / "requirements-toolchain.lock") == ALL


def test_only_one_canonical_contract_and_wheelhouse_exist() -> None:
    assert (ROOT / "TOOLCHAIN_CONTRACT.json").is_file()
    assert (ROOT / "toolchain_wheelhouse").is_dir()
    assert not (ROOT / "QUALITY_TOOLCHAIN_CONTRACT.json").exists()
    assert not (ROOT / "RUNTIME_ENVIRONMENT_CONTRACT.json").exists()
    assert not (ROOT / "quality_wheelhouse").exists()
    assert not (ROOT / "runtime_wheelhouse").exists()


def test_fake_unified_wheelhouse_verifies_and_detects_tampering(tmp_path: Path) -> None:
    wheelhouse = tmp_path / "toolchain_wheelhouse"
    wheelhouse.mkdir()
    _fake_wheelhouse(wheelhouse)
    contract = common.load_contract(ROOT)
    assert common.verify_wheelhouse(wheelhouse, contract) == []
    first = next(wheelhouse.glob("*.whl"))
    first.write_bytes(first.read_bytes() + b"tampered")
    errors = common.verify_wheelhouse(wheelhouse, contract)
    assert any("Wheelgröße" in error or "Prüfsumme" in error for error in errors)


def test_orchestrator_verifies_without_legacy_modules(tmp_path: Path) -> None:
    project = tmp_path / "project"
    scripts = project / "scripts"
    wheelhouse = project / "toolchain_wheelhouse"
    scripts.mkdir(parents=True)
    wheelhouse.mkdir()
    for filename in ("toolchain.py", "toolchain_common.py"):
        shutil.copy2(SCRIPTS / filename, scripts / filename)
    for filename in (
        "TOOLCHAIN_CONTRACT.json", "VERSION.json", "requirements.lock",
        "requirements-quality.lock", "requirements-toolchain.lock",
    ):
        shutil.copy2(ROOT / filename, project / filename)
    assert not (scripts / "quality_toolchain.py").exists()
    assert not (scripts / "runtime_toolchain.py").exists()
    _fake_wheelhouse(wheelhouse, root=project)
    completed = subprocess.run(
        [sys.executable, str(scripts / "toolchain.py"), "verify"],
        cwd=project, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False,
    )
    assert completed.returncode == 0, completed.stdout
    assert "TOOLCHAIN_WHEELHOUSE_VERIFIED=11" in completed.stdout


def test_single_entrypoint_and_compatibility_wrappers_are_bound() -> None:
    entry = (ROOT / "videobatch.sh").read_text(encoding="utf-8")
    assert "scripts/toolchain.py" in entry
    assert "scripts/debug_launcher.py" in entry
    assert "scripts/bootstrap.py" in (ROOT / "scripts" / "debug_launcher.py").read_text(encoding="utf-8")
    assert "toolchain_python" in entry
    for filename in ("start.sh", "setup.sh"):
        assert "videobatch.sh" in (ROOT / filename).read_text(encoding="utf-8")
    assert "--scope runtime" in (ROOT / "runtime-toolchain.sh").read_text(encoding="utf-8")
    assert "--scope quality" in (ROOT / "quality-toolchain.sh").read_text(encoding="utf-8")
