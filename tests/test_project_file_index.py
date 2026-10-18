from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

MODULE = Path(__file__).resolve().parents[1] / "scripts" / "project_file_index.py"
sys.path.insert(0, str(MODULE.parent))
spec = importlib.util.spec_from_file_location("project_file_index", MODULE)
assert spec and spec.loader
index = importlib.util.module_from_spec(spec)
spec.loader.exec_module(index)


def test_file_changes_and_rename() -> None:
    before = {"old.txt": {"sha256": "same"}, "keep.py": {"sha256": "1"}}
    after = {"new.txt": {"sha256": "same"}, "keep.py": {"sha256": "2"}}
    result = index.changes(before, after)
    assert result["renamed"] == [{"from": "old.txt", "to": "new.txt"}]
    assert result["modified"] == ["keep.py"]


def test_docs_only_never_authorizes_release_skip() -> None:
    result = index.choose_tests({"added": ["docs/howto.md"], "deleted": [],
                                 "modified": [], "renamed": []})
    assert result["suggested"] == ["--docs"]
    assert result["mandatory_release_checks_skippable"] is False


def test_contract_requires_stronger_checks() -> None:
    result = index.choose_tests({"added": [], "deleted": [],
                                 "modified": ["VERSION.json"], "renamed": []})
    assert "--local" in result["suggested"]


def test_source_change_never_treated_as_docs_only() -> None:
    result = index.choose_tests({"added": ["src/videobatch_fast/runner.py"],
                                 "deleted": [], "modified": [], "renamed": []})
    assert result["suggested"] == ["--core"]
