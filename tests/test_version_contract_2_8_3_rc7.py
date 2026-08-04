from __future__ import annotations

import shutil
import json
import re
from pathlib import Path

from scripts.validate_version_contract import validate

ROOT = Path(__file__).resolve().parents[1]


def test_current_version_contract_is_consistent() -> None:
    assert validate(ROOT) == []


def test_version_contract_detects_pyproject_drift(tmp_path: Path) -> None:
    for relative in (
        "VERSION.json", "pyproject.toml", "TOOLCHAIN_CONTRACT.json",
        "VISUAL_INSPECTION_MANIFEST.json", "QUALITY_ENVIRONMENT_STATUS.json",
    ):
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / relative, target)
    for relative in (
        "registries/UI_BLUEPRINT.json", "registries/UI_COMPONENT_REGISTRY.json",
        "registries/VISUAL_INSPECTION_REGISTRY.json", "registries/PLUGIN_APPROVAL_REGISTRY.json",
        "registries/VISUAL_REGRESSION_REGISTRY.json", "registries/VISUAL_APPROVAL_REGISTRY.json",
    ):
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / relative, target)
    pyproject = tmp_path / "pyproject.toml"
    text = pyproject.read_text()
    text = re.sub(r'(?m)^version\s*=\s*"[^"]+"', 'version = "0.0.0"', text, count=1)
    pyproject.write_text(text)
    errors = validate(tmp_path)
    assert any("pyproject.toml" in item for item in errors)


def test_unified_contract_id_uses_current_build() -> None:
    build = json.loads((ROOT / "VERSION.json").read_text(encoding="utf-8"))["build"]
    contract = (ROOT / "TOOLCHAIN_CONTRACT.json").read_text(encoding="utf-8")
    assert build in contract
