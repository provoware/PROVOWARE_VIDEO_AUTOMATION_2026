from __future__ import annotations

import json
import re
from pathlib import Path

EXPECTED_QUALITY = {
    "bandit": "1.9.4",
    "coverage": "7.13.3",
    "mypy": "2.3.0",
    "pip-audit": "2.10.1",
    "pytest": "9.0.2",
    "pytest-cov": "7.0.0",
    "ruff": "0.16.1",
}


def root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_quality_versions_are_exact_in_unified_contract() -> None:
    contract = json.loads((root() / "TOOLCHAIN_CONTRACT.json").read_text(encoding="utf-8"))
    actual = {name.lower(): version for name, version in contract["packages"]["quality"].items()}
    assert contract["release_target"] == json.loads((root() / "VERSION.json").read_text(encoding="utf-8"))["build"]
    assert actual == EXPECTED_QUALITY
    assert contract["policy"]["fail_closed"] is True
    assert contract["policy"]["stable_requires_all_tools"] is True


def test_quality_lock_contains_each_exact_version_once() -> None:
    text = (root() / "requirements-quality.lock").read_text(encoding="utf-8")
    for name, version in EXPECTED_QUALITY.items():
        matches = re.findall(rf"(?mi)^{re.escape(name)}=={re.escape(version)}(?:\s|$)", text)
        assert len(matches) == 1


def test_release_paths_use_unified_toolchain_fail_closed() -> None:
    for filename in ("quality.sh", "test.sh", "stable_release.sh"):
        text = (root() / filename).read_text(encoding="utf-8")
        assert "scripts/toolchain.py" in text
        assert "path --scope quality" in text or filename == "stable_release.sh"
