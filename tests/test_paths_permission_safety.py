from pathlib import Path

import pytest
from videobatch_fast import paths


def test_user_directory_is_not_renamed_after_write_failure(tmp_path: Path, monkeypatch) -> None:
    target = tmp_path / "userdata"
    target.mkdir()
    original = target / "valuable.txt"
    original.write_bytes(b"nicht verlieren")
    real_probe = paths._probe_directory

    def simulate_read_only_directory(directory: Path) -> None:
        if (directory / "valuable.txt").exists():
            raise PermissionError("simulierter fehlender Schreibzugriff")
        real_probe(directory)

    monkeypatch.setattr(paths, "_probe_directory", simulate_read_only_directory)
    with pytest.raises(PermissionError, match="nicht verschoben"):
        paths._prepare_directory(target)
    assert original.read_bytes() == b"nicht verlieren"
    assert sorted(tmp_path.iterdir()) == [target]


def test_file_conflict_is_not_silently_moved(tmp_path: Path) -> None:
    target = tmp_path / "userdata"
    target.write_bytes(b"mein Original")
    with pytest.raises(PermissionError, match="nicht verschoben"):
        paths._prepare_directory(target)
    assert target.read_bytes() == b"mein Original"
    assert sorted(tmp_path.iterdir()) == [target]


def test_directory_setup_still_creates_writable_new_directory(tmp_path: Path) -> None:
    target = tmp_path / "neu" / "userdata"
    paths._prepare_directory(target)
    assert target.is_dir()
    assert list(target.iterdir()) == []


def test_broken_symlink_is_not_relocated(tmp_path: Path) -> None:
    target = tmp_path / "userdata"
    target.symlink_to(tmp_path / "missing", target_is_directory=True)
    with pytest.raises(PermissionError, match="nicht verschoben"):
        paths._prepare_directory(target)
    assert target.is_symlink()
    assert target.readlink() == tmp_path / "missing"
    assert sorted(tmp_path.iterdir()) == [target]


def test_write_failure_is_not_retried_after_directory_move(tmp_path: Path, monkeypatch) -> None:
    target = tmp_path / "userdata"
    target.mkdir()
    calls = []

    def failing_probe(directory: Path) -> None:
        calls.append(directory)
        raise PermissionError("simulierter Fehler")

    monkeypatch.setattr(paths, "_probe_directory", failing_probe)
    with pytest.raises(PermissionError, match="nicht verschoben"):
        paths._prepare_directory(target)
    assert calls == [target]
    assert target.is_dir()
    assert sorted(tmp_path.iterdir()) == [target]


def test_existing_writable_directory_keeps_contents(tmp_path: Path) -> None:
    target = tmp_path / "userdata"
    target.mkdir()
    keep = target / "keep.txt"
    keep.write_bytes(b"unveraendert")
    paths._prepare_directory(target)
    assert keep.read_bytes() == b"unveraendert"
    assert list(target.iterdir()) == [keep]
