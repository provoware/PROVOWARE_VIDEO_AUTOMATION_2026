from __future__ import annotations

import json
from pathlib import Path

import pytest

from videobatch_fast.platform_integration import (
    PlatformCompatibilityError,
    detect_desktop_platform,
    prepare_gui_environment,
    validate_gui_environment,
)


def _which(*available: str):
    known = set(available)
    return lambda name: f"/usr/bin/{name}" if name in known else None


def _os_release(tmp_path: Path, *, distro: str = "kubuntu", version: str = "26.04") -> Path:
    path = tmp_path / "os-release"
    path.write_text(
        f'ID={distro}\nVERSION_ID="{version}"\nPRETTY_NAME="Kubuntu {version} LTS"\n',
        encoding="utf-8",
    )
    return path


def test_kubuntu_2604_wayland_detects_xwayland_transport(tmp_path: Path) -> None:
    platform = detect_desktop_platform(
        {
            "XDG_SESSION_TYPE": "wayland",
            "WAYLAND_DISPLAY": "wayland-0",
            "DISPLAY": ":1",
            "XDG_CURRENT_DESKTOP": "KDE",
            "DESKTOP_SESSION": "plasma",
        },
        os_release_path=_os_release(tmp_path),
        which=_which("ffmpeg", "ffprobe", "wl-copy", "wl-paste", "xdg-open", "Xwayland"),
    )
    assert platform.is_wayland is True
    assert platform.is_kde is True
    assert platform.is_kubuntu is True
    assert platform.distro_version == "26.04"
    assert platform.tkinter_transport == "xwayland"
    assert platform.warnings == ()
    validate_gui_environment(platform)


def test_wayland_without_display_fails_before_tk(tmp_path: Path) -> None:
    platform = detect_desktop_platform(
        {"XDG_SESSION_TYPE": "wayland", "WAYLAND_DISPLAY": "wayland-0"},
        os_release_path=_os_release(tmp_path),
        which=_which("wl-copy", "wl-paste", "Xwayland"),
    )
    assert platform.tkinter_transport == "unavailable"
    with pytest.raises(PlatformCompatibilityError, match="DISPLAY"):
        validate_gui_environment(platform)


def test_x11_remains_supported(tmp_path: Path) -> None:
    platform = detect_desktop_platform(
        {"XDG_SESSION_TYPE": "x11", "DISPLAY": ":0", "XDG_CURRENT_DESKTOP": "KDE"},
        os_release_path=_os_release(tmp_path, version="24.04"),
        which=_which("ffmpeg", "ffprobe", "xdg-open"),
    )
    assert platform.is_wayland is False
    assert platform.tkinter_transport == "x11"
    validate_gui_environment(platform)


def test_prepare_writes_machine_readable_report(tmp_path: Path) -> None:
    report = tmp_path / "platform.json"
    platform = prepare_gui_environment(
        {"XDG_SESSION_TYPE": "x11", "DISPLAY": ":99"},
        os_release_path=_os_release(tmp_path, distro="ubuntu", version="24.04"),
        which=_which("ffmpeg"),
        report_destination=report,
    )
    payload = json.loads(report.read_text(encoding="utf-8"))
    assert payload["tkinter_transport"] == "x11"
    assert payload["is_wayland"] is False
    assert platform.display == ":99"
