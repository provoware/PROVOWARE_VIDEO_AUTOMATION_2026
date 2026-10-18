from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from sha256_contract import dependency_digest, digest_json, file_sha256
import test_dependency_scope


def test_file_hash_changes_when_content_changes(tmp_path):
    path = tmp_path / "example.txt"
    path.write_text("eins", encoding="utf-8")
    a = file_sha256(path)
    path.write_text("zwei", encoding="utf-8")
    assert file_sha256(path) != a


def test_symlinks_are_not_trusted(tmp_path):
    import pytest
    original = tmp_path / "actual"
    original.write_text("hello")
    link = tmp_path / "link"
    link.symlink_to(original)
    with pytest.raises(ValueError):
        file_sha256(link)


def test_sorted_dependency_digest_and_path_change():
    import pytest
    aa, bb = "a" * 64, "b" * 64
    files = {"one.py": {"sha256": aa}, "two.py": {"sha256": bb}}
    a = dependency_digest(files, ["one.py", "two.py"])
    assert a == dependency_digest(files, ["two.py", "one.py"])
    assert a != dependency_digest({"renamed.py": {"sha256": aa}, "two.py": {"sha256": bb}},
                                  ["renamed.py", "two.py"])
    with pytest.raises(ValueError):
        dependency_digest(files, ["one.py", "missing.py"])
    with pytest.raises(ValueError):
        dependency_digest(files, ["../one.py"])


def test_unreviewed_scope_uses_entire_inventory():
    files = {"one.py": {"sha256": "a" * 64},
             "docs/help.md": {"sha256": "b" * 64}}
    report = test_dependency_scope.scoped_report("file_index", files)
    assert report["scope"] == "full_tree_fallback"
    assert report["dependency_count"] == 2
    assert report["cache_optimization_enabled"] is False
    modified = {**files, "docs/help.md": {"sha256": "c" * 64}}
    assert report["source_digest"] != test_dependency_scope.scoped_report(
        "file_index", modified)["source_digest"]
