from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "kubuntu-main-comment-dispatch.yml"


def test_main_matrix_comment_dispatch_is_owner_only_and_target_bound() -> None:
    source = WORKFLOW.read_text(encoding="utf-8")

    required_fragments = (
        "issue_comment:",
        "actions: write",
        "github.event.issue.number == 12",
        "github.event.comment.body == '/run-kubuntu-main'",
        "github.event.comment.author_association == 'OWNER'",
        "gh workflow run kubuntu-build-matrix.yml",
        "--ref main",
        "-f report_issue=12",
    )
    for fragment in required_fragments:
        assert fragment in source

    assert "pull_request_target:" not in source
    assert "repository_dispatch:" not in source
