from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "check_release_literal_hygiene.py"
SPEC = importlib.util.spec_from_file_location("release_literal_hygiene", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def make_repo(tmp_path: Path) -> Path:
    (tmp_path / "VERSION.json").write_text(
        json.dumps({"build": "2.8.3-rc24"}),
        encoding="utf-8",
    )
    (tmp_path / "pyproject.toml").write_text(
        'version = "2.8.3rc24"\n',
        encoding="utf-8",
    )
    (tmp_path / "scripts").mkdir()
    (tmp_path / "src" / "videobatch_fast").mkdir(parents=True)
    (tmp_path / "docs").mkdir()
    return tmp_path


def test_blocks_stale_release_and_concrete_artifact(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    (root / "scripts" / "build.sh").write_text(
        'RUN="VideoBatch_Fast_2.8.3-rc14-portable.run"\n',
        encoding="utf-8",
    )

    violations, counters = MODULE.scan_repository(root)

    assert counters["release_sensitive_files"] == 1
    assert {(item.kind, item.literal) for item in violations} == {
        ("release_identifier", "2.8.3-rc14"),
        ("artifact_filename", "VideoBatch_Fast_2.8.3-rc14-portable.run"),
    }


def test_blocks_current_release_when_hardcoded_in_runtime_code(
    tmp_path: Path,
) -> None:
    root = make_repo(tmp_path)
    (root / "src" / "videobatch_fast" / "release.py").write_text(
        'CURRENT = "2.8.3-rc24"\n',
        encoding="utf-8",
    )

    violations, _ = MODULE.scan_repository(root)

    assert len(violations) == 1
    assert violations[0].kind == "release_identifier"
    assert violations[0].path == "src/videobatch_fast/release.py"


def test_allows_authoritative_metadata_history_and_reasoned_exception(
    tmp_path: Path,
) -> None:
    root = make_repo(tmp_path)
    (root / "docs" / "history.md").write_text(
        "Historischer Kandidat 2.8.3-rc14\n",
        encoding="utf-8",
    )
    (root / "scripts" / "compatibility.py").write_text(
        'LEGACY = "2.8.3-rc14"  # release-literal: allow['
        "Migrationstest für alte Projektdateien]\n",
        encoding="utf-8",
    )

    violations, _ = MODULE.scan_repository(root)

    assert violations == []
