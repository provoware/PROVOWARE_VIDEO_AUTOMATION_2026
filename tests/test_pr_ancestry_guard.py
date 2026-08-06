from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "check_pr_ancestry.py"
SPEC = importlib.util.spec_from_file_location("check_pr_ancestry", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def git(repo: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=repo,
        text=True,
        capture_output=True,
        check=True,
    )
    return completed.stdout.strip()


def commit(repo: Path, message: str) -> str:
    git(repo, "add", "-A")
    git(repo, "commit", "-m", message)
    return git(repo, "rev-parse", "HEAD")


def repository(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "-b", "main")
    git(repo, "config", "user.name", "Test")
    git(repo, "config", "user.email", "test@example.invalid")
    (repo / "src").mkdir()
    (repo / "src" / "product.py").write_text("VALUE = 1\n", encoding="utf-8")
    commit(repo, "initial")
    return repo


def evaluate(repo: Path, base: str, head: str, monkeypatch) -> dict[str, object]:
    monkeypatch.setattr(MODULE, "ROOT", repo)
    return MODULE.evaluate(base, head)


def violation_codes(report: dict[str, object]) -> set[str]:
    return {item["code"] for item in report["violations"]}


def test_current_branch_passes(tmp_path: Path, monkeypatch) -> None:
    repo = repository(tmp_path)
    base = git(repo, "rev-parse", "HEAD")
    git(repo, "switch", "-c", "feature")
    (repo / "README.md").write_text("feature\n", encoding="utf-8")
    head = commit(repo, "feature")

    report = evaluate(repo, base, head, monkeypatch)

    assert report["status"] == "passed"
    assert report["base_is_ancestor"] is True


def test_branch_behind_main_is_blocked(tmp_path: Path, monkeypatch) -> None:
    repo = repository(tmp_path)
    fork = git(repo, "rev-parse", "HEAD")
    git(repo, "switch", "-c", "feature", fork)
    (repo / "README.md").write_text("feature\n", encoding="utf-8")
    head = commit(repo, "feature")
    git(repo, "switch", "main")
    (repo / "src" / "product.py").write_text("VALUE = 2\n", encoding="utf-8")
    base = commit(repo, "main advances")

    report = evaluate(repo, base, head, monkeypatch)

    assert report["status"] == "failed"
    assert "BASE_NOT_ANCESTOR" in violation_codes(report)


def test_patch_already_in_base_is_blocked(tmp_path: Path, monkeypatch) -> None:
    repo = repository(tmp_path)
    fork = git(repo, "rev-parse", "HEAD")
    git(repo, "switch", "-c", "feature", fork)
    (repo / "README.md").write_text("same patch\n", encoding="utf-8")
    duplicate = commit(repo, "duplicate patch")
    git(repo, "switch", "main")
    (repo / "README.md").write_text("same patch\n", encoding="utf-8")
    base = commit(repo, "patch already merged")
    git(repo, "switch", "feature")
    git(repo, "merge", "--no-edit", "main")
    head = git(repo, "rev-parse", "HEAD")

    report = evaluate(repo, base, head, monkeypatch)

    assert report["status"] == "failed"
    assert "PATCH_ALREADY_IN_BASE" in violation_codes(report)
    duplicate_violations = [
        item for item in report["violations"] if item["code"] == "PATCH_ALREADY_IN_BASE"
    ]
    assert duplicate in duplicate_violations[0]["commits"]


def test_historical_product_rollback_is_blocked(tmp_path: Path, monkeypatch) -> None:
    repo = repository(tmp_path)
    old_value = (repo / "src" / "product.py").read_text(encoding="utf-8")
    (repo / "src" / "product.py").write_text("VALUE = 2\n", encoding="utf-8")
    base = commit(repo, "new product version")
    git(repo, "switch", "-c", "feature")
    (repo / "src" / "product.py").write_text(old_value, encoding="utf-8")
    head = commit(repo, "restore old product")

    report = evaluate(repo, base, head, monkeypatch)

    assert report["status"] == "failed"
    assert "HISTORICAL_BLOB_ROLLBACK" in violation_codes(report)
