"""No speculative test skips; preserve immutable final/safety gates."""
from __future__ import annotations

import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "plan_quality_checks.py"
SPEC = importlib.util.spec_from_file_location("plan_quality_checks", SCRIPT)
assert SPEC and SPEC.loader
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


def decisions(paths: list[str], final: bool = False) -> dict[str, str]:
    return {x["id"]: x["decision"] for x in module.plan(paths, final=final)["suites"]}


def test_docs_only_skips_unchanged_media_without_bypassing_contracts() -> None:
    flags = decisions(["docs/HELP.md"])
    assert flags["docs"] == "required"
    assert flags["media"] == "not_affected"
    assert flags["structure"] == "required"
    assert flags["release_contract"] == "required"


def test_ffmpeg_change_always_requires_core_and_media() -> None:
    flags = decisions(["src/videobatch_fast/runner.py"])
    assert flags["core"] == "required"
    assert flags["media"] == "required"


def test_release_all_required_and_never_reused() -> None:
    report = module.plan(["docs/guide.md"], final=True)
    assert all(row["decision"] == "required" for row in report["suites"])
    assert not next(x for x in report["suites"] if x["id"] == "real_long_render")["reusable"]


def test_unknown_path_triggers_full_plan() -> None:
    flags = decisions(["unclassified/unknown/secret.py"])
    assert all(x == "required" for x in flags.values())


def test_evidence_must_match_all_context_and_be_verified() -> None:
    args = dict(commit="a"*40, suite="docs", suite_digest="b"*64,
                inputs_digest="c"*64, environment="kubuntu-26.04-py3.12")
    evidence = dict(args, status="success", verified=True)
    assert module.evidence_matches(evidence, **args)
    evidence["commit"] = "stale"
    assert not module.evidence_matches(evidence, **args)
    evidence.update(args, verified=False)
    assert not module.evidence_matches(evidence, **args)


def test_registry_ids_are_unique() -> None:
    data = module.load_registry()
    assert len(data["suites"]) == len({x["id"] for x in data["suites"]})
