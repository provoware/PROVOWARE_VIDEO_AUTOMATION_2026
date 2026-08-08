from __future__ import annotations

import hashlib
import importlib.util
import json
import stat
import sys
import zipfile
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[1]


def load_planner() -> ModuleType:
    path = ROOT / "scripts" / "plan_q1_16_reconciliation.py"
    spec = importlib.util.spec_from_file_location("plan_q1_16_reconciliation", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Planner kann nicht geladen werden: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def write_scope(path: Path, added: list[str], modified: list[str]) -> None:
    path.write_text(json.dumps({"added": added, "modified": modified}), encoding="utf-8")


def test_build_plan_is_read_only_and_classifies_changes(tmp_path: Path) -> None:
    module = load_planner()
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "m.txt").write_text("old", encoding="utf-8")
    scope = tmp_path / "scope.json"
    write_scope(scope, ["a.txt"], ["m.txt"])
    archive = tmp_path / "candidate.zip"
    with zipfile.ZipFile(archive, "w") as handle:
        handle.writestr("candidate/a.txt", "new")
        handle.writestr("candidate/m.txt", "new-modified")
    module.EXPECTED_SHA256 = hashlib.sha256(archive.read_bytes()).hexdigest()

    plan = module.build_plan(archive, repo, scope)

    assert plan["counts"] == {"add": 1, "review-modified": 1}
    assert plan["apply_allowed"] is False
    assert not (repo / "a.txt").exists()
    assert (repo / "m.txt").read_text(encoding="utf-8") == "old"


def test_archive_path_traversal_is_rejected(tmp_path: Path) -> None:
    module = load_planner()
    archive = tmp_path / "bad.zip"
    with zipfile.ZipFile(archive, "w") as handle:
        handle.writestr("../outside.txt", "x")
    with zipfile.ZipFile(archive) as handle:
        try:
            module.normalized_members(handle)
        except ValueError as exc:
            assert "unsafe archive path" in str(exc)
        else:
            raise AssertionError("path traversal was accepted")


def test_archive_symlink_is_rejected(tmp_path: Path) -> None:
    module = load_planner()
    archive = tmp_path / "link.zip"
    info = zipfile.ZipInfo("link")
    info.create_system = 3
    info.external_attr = (stat.S_IFLNK | 0o777) << 16
    with zipfile.ZipFile(archive, "w") as handle:
        handle.writestr(info, "target")
    with zipfile.ZipFile(archive) as handle:
        try:
            module.normalized_members(handle)
        except ValueError as exc:
            assert "symlink" in str(exc)
        else:
            raise AssertionError("symlink entry was accepted")


def test_missing_scoped_file_blocks_plan(tmp_path: Path) -> None:
    module = load_planner()
    repo = tmp_path / "repo"
    repo.mkdir()
    scope = tmp_path / "scope.json"
    write_scope(scope, ["a.txt"], ["m.txt"])
    archive = tmp_path / "candidate.zip"
    with zipfile.ZipFile(archive, "w") as handle:
        handle.writestr("a.txt", "x")
    module.EXPECTED_SHA256 = hashlib.sha256(archive.read_bytes()).hexdigest()

    try:
        module.build_plan(archive, repo, scope)
    except ValueError as exc:
        assert "misses scoped files" in str(exc)
    else:
        raise AssertionError("incomplete archive was accepted")


def test_repository_scope_matches_q1_16_report_contract() -> None:
    value = json.loads((ROOT / "Q1_16_IMPORT_SCOPE.json").read_text(encoding="utf-8"))
    assert len(value["added"]) == 19
    assert len(value["modified"]) == 12
    assert not set(value["added"]) & set(value["modified"])
    assert value["policy"]["automatic_overwrite"] is False
    assert value["policy"]["allow_deletions"] is False
    assert value["policy"]["preserve_pr74_changes"] is True
