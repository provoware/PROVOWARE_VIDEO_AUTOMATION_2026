from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from release_file_contract import included_release_file  # noqa: E402


def _touch(root: Path, relative: str) -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("x\n", encoding="utf-8")
    return path


def test_release_contract_excludes_backup_cache_bytecode_and_coverage(tmp_path: Path) -> None:
    excluded = (
        "Backup/A32.2_vor_A33/canonical_ui.py",
        "src/videobatch_fast/__pycache__/canonical_ui.cpython-312.pyc",
        ".pytest_cache/v/cache/nodeids",
        ".mypy_cache/state.json",
        ".ruff_cache/cache.bin",
        "coverage.json",
        "coverage.xml",
        "module.pyc",
    )
    for relative in excluded:
        path = _touch(tmp_path, relative)
        assert included_release_file(tmp_path, path) is False, relative

    normal = _touch(tmp_path, "src/videobatch_fast/canonical_ui.py")
    assert included_release_file(tmp_path, normal) is True


def test_iteration_39a_workflow_uses_locked_toolchain_and_manifest_packager() -> None:
    workflow = (ROOT / ".github/workflows/a33-consolidated-package.yml").read_text(
        encoding="utf-8"
    )
    assert "iteration/39a-a33-rebased-packaging-hygiene-20260904" in workflow
    assert "requirements-toolchain.lock" in workflow
    assert "python -m pip install --requirement requirements-toolchain.lock" in workflow
    assert "python -m pip install pytest" not in workflow
    assert "scripts/package_release.py" in workflow
    assert "scripts/verify_release_zip.py" in workflow
    assert "scripts/coverage_policy.py coverage.json 80 65" in workflow
    assert 'zip -qr "$ZIP" .' not in workflow


def test_iteration_39a_workflow_preserves_subprocess_import_isolation() -> None:
    workflow = (ROOT / ".github/workflows/a33-consolidated-package.yml").read_text(
        encoding="utf-8"
    )
    assert "PYTHONPATH: ${{ github.workspace }}/src\n" in workflow
    assert "PYTHONPATH: ${{ github.workspace }}/src:${{ github.workspace }}/scripts" not in workflow


def test_toolchain_lock_pins_pytest_and_pytest_cov() -> None:
    lock = (ROOT / "requirements-toolchain.lock").read_text(encoding="utf-8")
    assert "pytest==9.0.2" in lock
    assert "pytest-cov==7.0.0" in lock
    assert "coverage==7.13.3" in lock
