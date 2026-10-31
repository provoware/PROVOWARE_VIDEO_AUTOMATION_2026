"""Quarantine must not overwrite a competing target or unlink a replacement source."""
from __future__ import annotations
import errno
from pathlib import Path
from unittest.mock import patch

import pytest

from videobatch_fast.safe_io import SafeIoError, quarantine_file


def test_concurrent_target_creation_preserves_both_files(tmp_path: Path) -> None:
    source = tmp_path / "config.json"
    source.write_bytes(b"original")
    victim = tmp_path / "config.corrupt.20261031_100000.json"
    original = Path.exists

    def inject(path: Path) -> bool:
        found = original(path)
        if path == victim and not found and not original(victim):
            victim.write_bytes(b"foreign")
        return found

    with patch("videobatch_fast.safe_io.time.strftime", return_value="20261031_100000"), patch.object(Path, "exists", inject):
        quarantined = quarantine_file(source)
    assert quarantined is not None and quarantined != victim
    assert victim.read_bytes() == b"foreign"
    assert quarantined.read_bytes() == b"original"
    assert not source.exists()


def test_atomic_rename_moves_symlink_itself_not_target(tmp_path: Path) -> None:
    protected = tmp_path / "protected.txt"
    protected.write_bytes(b"protected")
    source = tmp_path / "bad.json"
    source.symlink_to(protected)
    moved = quarantine_file(source)
    assert moved is not None and moved.is_symlink()
    assert moved.readlink() == protected
    assert protected.read_bytes() == b"protected"
    assert not source.is_symlink()


def test_unsupported_atomic_rename_does_not_delete_source(tmp_path: Path) -> None:
    source = tmp_path / "bad.json"
    source.write_bytes(b"original")
    with patch("videobatch_fast.safe_io._rename_without_replacement", side_effect=OSError(errno.ENOTSUP, "unsupported")):
        with pytest.raises(SafeIoError):
            quarantine_file(source)
    assert source.read_bytes() == b"original"
    assert not list(tmp_path.glob("bad.corrupt.*.json"))


def test_source_replacement_before_atomic_rename_is_not_deleted(tmp_path: Path) -> None:
    source = tmp_path / "bad.json"
    source.write_bytes(b"old")
    def swap_then_fail(a: Path, b: Path) -> None:
        a.rename(tmp_path / "old-file")
        a.write_bytes(b"replacement")
        raise OSError(errno.EAGAIN, "simulated concurrent swap")
    with patch("videobatch_fast.safe_io._rename_without_replacement", side_effect=swap_then_fail):
        with pytest.raises(SafeIoError):
            quarantine_file(source)
    assert source.read_bytes() == b"replacement"
    assert (tmp_path / "old-file").read_bytes() == b"old"
