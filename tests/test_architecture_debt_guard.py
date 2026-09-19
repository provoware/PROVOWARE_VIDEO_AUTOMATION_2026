from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "registries" / "CODE_QUALITY_REGISTRY.json"
SRC = ROOT / "src"


def _policy() -> dict:
    return json.loads(REGISTRY.read_text(encoding="utf-8"))["python"]


def test_architecture_debt_baseline_covers_every_oversized_source_file() -> None:
    policy = _policy()
    limit = int(policy["source_line_limit"])
    ceilings = {
        str(path): int(value)
        for path, value in policy["legacy_source_line_ceilings"].items()
    }

    assert limit == 250
    oversized: dict[str, int] = {}
    for path in SRC.rglob("*.py"):
        relative = path.relative_to(ROOT).as_posix()
        lines = len(path.read_text(encoding="utf-8").splitlines())
        if lines > limit:
            oversized[relative] = lines
            assert relative in ceilings, f"{relative} mit {lines} Zeilen fehlt in der Debt-Baseline"
            assert lines <= ceilings[relative], (
                f"{relative} ist von {ceilings[relative]} auf {lines} Zeilen gewachsen"
            )

    assert set(ceilings) == set(oversized)


def test_architecture_debt_targets_are_explicit_and_stricter_than_legacy() -> None:
    policy = _policy()
    assert int(policy["function_line_target"]) == 30
    assert int(policy["class_method_target"]) == 24
    assert all(
        int(ceiling) > int(policy["source_line_limit"])
        for ceiling in policy["legacy_source_line_ceilings"].values()
    )


def test_internal_quality_gate_enforces_no_growth_semantics() -> None:
    source = (ROOT / "scripts" / "internal_quality_gate.py").read_text(encoding="utf-8")
    for token in (
        "_source_line_ceiling",
        "FILE_DEBT_GREW",
        "DEBT_BASELINE_REDUNDANT",
        "DEBT_BASELINE_ORPHAN",
        '"architecture_debt_files"',
        '"long_functions"',
        '"large_classes"',
    ):
        assert token in source
