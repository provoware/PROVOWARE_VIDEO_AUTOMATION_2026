from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "kubuntu-main-comment-dispatch.yml"


def test_owner_dispatch_is_issue_and_owner_bound() -> None:
    source = WORKFLOW.read_text(encoding="utf-8")

    required_fragments = (
        "issue_comment:",
        "actions: write",
        "issues: write",
        "github.event.issue.number == 12",
        "github.event.comment.author_association == 'OWNER'",
        "github.event.comment.body == '/run-kubuntu-main'",
        "github.event.comment.body == '/run-kubuntu-cache-warmup'",
    )
    for fragment in required_fragments:
        assert fragment in source

    assert "pull_request_target:" not in source
    assert "repository_dispatch:" not in source


def test_dispatch_targets_only_approved_main_workflows() -> None:
    source = WORKFLOW.read_text(encoding="utf-8")

    assert "workflow=kubuntu-build-matrix.yml" in source
    assert "workflow=kubuntu-cache-warmup.yml" in source
    assert "-f report_issue=12" in source
    assert 'gh workflow run "$WORKFLOW"' in source
    assert "ref=main" in source
    assert '--ref "$REF"' in source
    assert "case \"$COMMAND\" in" in source
    assert "exit 64" in source


def test_dispatch_reports_run_id_without_failing_on_api_delay() -> None:
    source = WORKFLOW.read_text(encoding="utf-8")

    assert "gh run list" in source
    assert "--event workflow_dispatch" in source
    assert "databaseId,createdAt,status,url,headSha" in source
    assert "select(.createdAt >= $started)" in source
    assert "for attempt in $(seq 1 18)" in source
    assert "sleep 5" in source
    assert "Run nicht auffindbar" in source
    assert "exit 1" in source
    assert "gh issue comment 12" in source
    assert "Der Abnahmeworkflow validiert Base- und PR-Head-SHA" in source
