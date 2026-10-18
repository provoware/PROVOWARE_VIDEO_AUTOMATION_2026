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

def test_invalid_dependency_inputs_and_renames_fail_closed():
    import pytest
    for bad in ("../escape.py", "/absolute.py", "./relative.py"):
        with pytest.raises(ValueError):
            dependency_digest({bad: {"sha256": "a" * 64}}, [bad])
    with pytest.raises(ValueError):
        dependency_digest({"x.py": {"sha256": "wrong"}}, ["x.py"])
    with pytest.raises(ValueError):
        dependency_digest({}, [])


def test_mutation_detected_between_file_statistics(tmp_path, monkeypatch):
    from types import SimpleNamespace
    import pytest
    p = tmp_path / "dynamic.txt"
    p.write_text("value")
    original = Path.stat
    count = [0]
    def fake_stat(self, *args, **kwargs):
        info = original(self, *args, **kwargs)
        if self == p:
            count[0] += 1
            if count[0] == 3:
                return SimpleNamespace(
                    st_size=info.st_size + 1,
                    st_mtime_ns=info.st_mtime_ns,
                    st_ctime_ns=info.st_ctime_ns,
                    st_ino=info.st_ino, st_dev=info.st_dev)
        return info
    monkeypatch.setattr(Path, "stat", fake_stat)
    with pytest.raises(ValueError, match="verändert"):
        file_sha256(p)


def test_review_is_advisory_until_indirect_inputs_verified():
    import json
    policy = json.loads(test_dependency_scope.POLICY.read_text(encoding="utf-8"))
    assert policy["dependency_review"]["automatic_scoped_reuse"] is False
    assert policy["tests"]["file_index"]["dependencies_reviewed"] is True
    assert all(not s["dependencies_reviewed"] for name, s in policy["tests"].items() if name != "file_index")
    assert all(s["dependency_candidates"] for s in policy["tests"].values())


def test_import_audit_does_not_approve_unresolved_graph():
    report = test_dependency_scope.python_import_audit("file_index")
    assert "scripts/project_file_index.py" in report["discovered_paths"]
    assert "scripts/sha256_contract.py" in report["discovered_paths"]
    assert not report["complete"]
    assert not report["scope_reuse_approved"]
