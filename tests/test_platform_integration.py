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


def _os_release(
    tmp_path: Path,
    *,
    distro: str = "ubuntu",
    version: str = "26.04",
    pretty_name: str | None = None,
) -> Path:
    path = tmp_path / "os-release"
    pretty = pretty_name or f"Ubuntu {version} LTS"
    path.write_text(
        f'ID={distro}\nID_LIKE=debian\nVERSION_ID="{version}"\nPRETTY_NAME="{pretty}"\n',
        encoding="utf-8",
    )
    return path


def _wayland_env() -> dict[str, str]:
    return {
        "XDG_SESSION_TYPE": "wayland",
        "WAYLAND_DISPLAY": "wayland-0",
        "XDG_CURRENT_DESKTOP": "KDE",
        "DESKTOP_SESSION": "plasmawayland",
    }


def test_kubuntu_2604_wayland_uses_native_qt_transport_without_xwayland(tmp_path: Path) -> None:
    platform = detect_desktop_platform(
        _wayland_env(),
        os_release_path=_os_release(tmp_path),
        which=_which("ffmpeg", "ffprobe", "wl-copy", "wl-paste", "xdg-open"),
    )
    assert platform.is_wayland is True
    assert platform.is_kde is True
    assert platform.is_kubuntu is True
    assert platform.distro_version == "26.04"
    assert platform.ui_transport == "wayland-native"
    assert platform.display == ""
    assert platform.warnings == ()
    validate_gui_environment(platform)


def test_real_kubuntu_2604_os_release_without_flavour_marker_is_accepted(tmp_path: Path) -> None:
    platform = detect_desktop_platform(
        _wayland_env(),
        os_release_path=_os_release(tmp_path),
        which=_which("ffmpeg", "ffprobe", "wl-copy", "wl-paste"),
    )
    assert platform.distro_id == "ubuntu"
    assert platform.distro_name == "Ubuntu 26.04 LTS"
    assert platform.is_kde is True
    assert platform.is_kubuntu is True
    validate_gui_environment(platform)


def test_ubuntu_2604_gnome_wayland_is_not_misidentified_as_kubuntu(tmp_path: Path) -> None:
    env = _wayland_env()
    env["XDG_CURRENT_DESKTOP"] = "ubuntu:GNOME"
    env["DESKTOP_SESSION"] = "ubuntu-wayland"
    platform = detect_desktop_platform(
        env,
        os_release_path=_os_release(tmp_path),
        which=_which("ffmpeg", "ffprobe", "wl-copy", "wl-paste"),
    )
    assert platform.is_kde is False
    assert platform.is_kubuntu is False
    with pytest.raises(PlatformCompatibilityError, match="Kubuntu 26.04"):
        validate_gui_environment(platform)


def test_non_ubuntu_kde_wayland_is_rejected(tmp_path: Path) -> None:
    platform = detect_desktop_platform(
        _wayland_env(),
        os_release_path=_os_release(
            tmp_path, distro="debian", version="13", pretty_name="Debian GNU/Linux 13"
        ),
        which=_which("ffmpeg", "ffprobe", "wl-copy", "wl-paste"),
    )
    assert platform.is_kde is True
    assert platform.is_kubuntu is False
    with pytest.raises(PlatformCompatibilityError, match="Kubuntu 26.04"):
        validate_gui_environment(platform)


def test_x11_is_rejected_even_when_display_exists(tmp_path: Path) -> None:
    platform = detect_desktop_platform(
        {
            "XDG_SESSION_TYPE": "x11",
            "DISPLAY": ":0",
            "XDG_CURRENT_DESKTOP": "KDE",
            "DESKTOP_SESSION": "plasma",
        },
        os_release_path=_os_release(tmp_path),
        which=_which("ffmpeg", "ffprobe", "xdg-open"),
    )
    assert platform.ui_transport == "unsupported"
    with pytest.raises(PlatformCompatibilityError, match="X11"):
        validate_gui_environment(platform)


def test_other_release_is_rejected(tmp_path: Path) -> None:
    platform = detect_desktop_platform(
        _wayland_env(),
        os_release_path=_os_release(tmp_path, version="24.04"),
        which=_which("ffmpeg", "ffprobe", "wl-copy", "wl-paste"),
    )
    with pytest.raises(PlatformCompatibilityError, match="Kubuntu 26.04"):
        validate_gui_environment(platform)


def test_missing_wayland_display_is_rejected(tmp_path: Path) -> None:
    env = _wayland_env()
    env.pop("WAYLAND_DISPLAY")
    platform = detect_desktop_platform(
        env,
        os_release_path=_os_release(tmp_path),
        which=_which("ffmpeg", "ffprobe", "wl-copy", "wl-paste"),
    )
    with pytest.raises(PlatformCompatibilityError, match="WAYLAND_DISPLAY"):
        validate_gui_environment(platform)


def test_prepare_writes_machine_readable_native_wayland_report(tmp_path: Path) -> None:
    report = tmp_path / "platform.json"
    platform = prepare_gui_environment(
        _wayland_env(),
        os_release_path=_os_release(tmp_path),
        which=_which("ffmpeg", "ffprobe", "wl-copy", "wl-paste", "xdg-open"),
        report_destination=report,
    )
    payload = json.loads(report.read_text(encoding="utf-8"))
    assert payload["ui_transport"] == "wayland-native"
    assert payload["is_wayland"] is True
    assert payload["display"] == ""
    assert platform.wayland_display == "wayland-0"
