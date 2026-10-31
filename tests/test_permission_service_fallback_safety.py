"""Fail-closed permission fallback tests for symlinked directories."""
from __future__ import annotations

from pathlib import Path

from videobatch_fast.permission_service import ensure_writable_directory


def test_fallback_symlink_does_not_redirect_writes(tmp_path: Path) -> None:
    external = tmp_path / "external"
    external.mkdir()
    fallback = tmp_path / "fallback"
    fallback.symlink_to(external, target_is_directory=True)
    requested = tmp_path / "original"
    requested.write_text("unveraendert", encoding="utf-8")

    result = ensure_writable_directory(requested, fallback)

    assert result.path == requested
    assert result.writable is False
    assert result.fallback_used is False
    assert "symbolischer Link" in result.message
    assert requested.read_text(encoding="utf-8") == "unveraendert"
    assert list(external.iterdir()) == []


def test_broken_fallback_symlink_is_rejected(tmp_path: Path) -> None:
    requested = tmp_path / "original"
    requested.write_text("geschuetzt", encoding="utf-8")
    fallback = tmp_path / "fallback"
    fallback.symlink_to(tmp_path / "missing", target_is_directory=True)

    result = ensure_writable_directory(requested, fallback)

    assert not result.writable
    assert fallback.is_symlink()
    assert not (tmp_path / "missing").exists()


def test_real_fallback_directory_remains_available(tmp_path: Path) -> None:
    requested = tmp_path / "original"
    requested.write_text("unveraendert", encoding="utf-8")
    fallback = tmp_path / "fallback"

    result = ensure_writable_directory(requested, fallback)

    assert result.writable
    assert result.fallback_used
    assert result.path == fallback
    assert fallback.is_dir()
    assert requested.read_text(encoding="utf-8") == "unveraendert"


def test_writable_requested_directory_ignores_fallback_link(tmp_path: Path) -> None:
    requested = tmp_path / "requested"
    requested.mkdir()
    fallback = tmp_path / "fallback"
    fallback.symlink_to(tmp_path / "missing", target_is_directory=True)

    result = ensure_writable_directory(requested, fallback)

    assert result.writable
    assert result.path == requested
    assert not result.fallback_used
