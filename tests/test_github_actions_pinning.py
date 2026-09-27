from __future__ import annotations

from pathlib import Path

from scripts.check_github_actions_pins import inspect_workflows

ROOT = Path(__file__).resolve().parents[1]


def test_repository_workflows_use_immutable_external_action_pins() -> None:
    assert inspect_workflows(ROOT / ".github" / "workflows") == []


def test_rejects_mutable_external_action_tag(tmp_path: Path) -> None:
    workflow = tmp_path / "ci.yml"
    workflow.write_text(
        "steps:\n  - uses: actions/checkout@v4\n",
        encoding="utf-8",
    )
    findings = inspect_workflows(tmp_path)
    assert len(findings) == 1
    assert findings[0].uses == "actions/checkout@v4"


def test_accepts_exact_sha_and_local_or_docker_uses(tmp_path: Path) -> None:
    workflow = tmp_path / "ci.yaml"
    workflow.write_text(
        "steps:\n"
        "  - uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262 # v4\n"
        "  - uses: ./.github/actions/local\n"
        "  - uses: docker://alpine:3.20\n",
        encoding="utf-8",
    )
    assert inspect_workflows(tmp_path) == []
