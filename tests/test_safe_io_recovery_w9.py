from __future__ import annotations

import os
import time
from pathlib import Path

import pytest

from videobatch_fast.safe_io import SafeIoError, atomic_write_text, cleanup_atomic_tempfiles, exclusive_file_lock


def test_dead_pid_atomic_temp_is_removed_before_next_write(tmp_path: Path):
    target = tmp_path / "state.json"
    target.write_text("old", encoding="utf-8")
    stale = tmp_path / f".{target.name}.99999999.dead.tmp"
    stale.write_text("partial", encoding="utf-8")
    atomic_write_text(target, "new")
    assert target.read_text(encoding="utf-8") == "new"
    assert not stale.exists()


def test_live_pid_atomic_temp_is_never_removed(tmp_path: Path):
    target = tmp_path / "state.json"
    live = tmp_path / f".{target.name}.{os.getpid()}.active.tmp"
    live.write_text("active", encoding="utf-8")
    assert cleanup_atomic_tempfiles(target, legacy_min_age_seconds=0) == []
    assert live.exists()


def test_legacy_temp_obeys_safety_age(tmp_path: Path):
    target = tmp_path / "state.json"
    legacy = tmp_path / f".{target.name}.legacy.tmp"
    legacy.write_text("partial", encoding="utf-8")
    assert cleanup_atomic_tempfiles(target, legacy_min_age_seconds=60) == []
    old = time.time() - 120
    os.utime(legacy, (old, old))
    assert cleanup_atomic_tempfiles(target, legacy_min_age_seconds=60) == [legacy]
    assert not legacy.exists()


def test_file_lock_times_out_instead_of_waiting_forever(tmp_path: Path):
    lock = tmp_path / "state.lock"
    with exclusive_file_lock(lock):
        with pytest.raises(SafeIoError, match="Zeitlimit"):
            with exclusive_file_lock(lock, timeout_seconds=0.03, poll_seconds=0.005):
                pass
