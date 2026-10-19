from pathlib import Path

import pytest

from videobatch_fast.media_index_preferences import (
    load_exclusions, save_exclusions, validate_exclusions,
)


def test_excluded_project_folder_survives_restart(tmp_path: Path) -> None:
    roots = {"videos": tmp_path / "Videos", "downloads": tmp_path / "Downloads",
             "pictures": tmp_path / "Bilder"}
    project = roots["downloads"] / "Mein Projekt"
    project.mkdir(parents=True)
    target = tmp_path / "settings" / "excluded.json"
    result = save_exclusions([project, project], roots, target)
    assert result == (project,)
    assert load_exclusions(target) == (project,)
    assert project.is_dir()


def test_exclusions_reject_other_folders_and_entire_root(tmp_path: Path) -> None:
    roots = {"videos": tmp_path / "Videos", "downloads": tmp_path / "Downloads",
             "pictures": tmp_path / "Bilder"}
    for path in [tmp_path, tmp_path / "Downloads", Path("/etc"),
                 Path("relative/path")]:
        with pytest.raises(ValueError):
            validate_exclusions([path], roots)


def test_corrupt_exclusion_list_is_rejected(tmp_path: Path) -> None:
    target = tmp_path / "excluded.json"
    target.write_text("{invalid", encoding="utf-8")
    with pytest.raises(ValueError):
        load_exclusions(target)
    assert target.read_text(encoding="utf-8") == "{invalid"
