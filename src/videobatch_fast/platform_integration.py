from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable, Mapping


class PlatformCompatibilityError(RuntimeError):
    """Raised when the current desktop is outside the supported Qt/Wayland target."""


@dataclass(frozen=True)
class DesktopPlatform:
    session_type: str
    wayland_display: str
    display: str
    current_desktop: str
    desktop_session: str
    distro_id: str
    distro_version: str
    distro_name: str
    is_wayland: bool
    is_kde: bool
    is_kubuntu: bool
    ui_transport: str
    capabilities: dict[str, bool]
    warnings: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _read_os_release(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return values
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key] = value.strip().strip('"').strip("'")
    return values


def detect_desktop_platform(
    environ: Mapping[str, str] | None = None,
    *,
    os_release_path: Path = Path("/etc/os-release"),
    which: Callable[[str], str | None] = shutil.which,
) -> DesktopPlatform:
    env = os.environ if environ is None else environ
    release = _read_os_release(os_release_path)

    session_type = env.get("XDG_SESSION_TYPE", "").strip().lower()
    wayland_display = env.get("WAYLAND_DISPLAY", "").strip()
    display = env.get("DISPLAY", "").strip()
    current_desktop = env.get("XDG_CURRENT_DESKTOP", "").strip()
    desktop_session = env.get("DESKTOP_SESSION", "").strip()

    is_wayland = session_type == "wayland" or bool(wayland_display)
    desktop_tokens = f"{current_desktop}:{desktop_session}".lower()
    is_kde = "kde" in desktop_tokens or "plasma" in desktop_tokens
    distro_id = release.get("ID", "").lower()
    distro_name = release.get("PRETTY_NAME", release.get("NAME", ""))
    distro_version = release.get("VERSION_ID", "")
    distro_tokens = ":".join(
        (
            distro_id,
            distro_name.lower(),
            release.get("VARIANT", "").lower(),
            release.get("VARIANT_ID", "").lower(),
        )
    )
    is_kubuntu = "kubuntu" in distro_tokens

    capabilities = {
        "ffmpeg": which("ffmpeg") is not None,
        "ffprobe": which("ffprobe") is not None,
        "wl_copy": which("wl-copy") is not None,
        "wl_paste": which("wl-paste") is not None,
        "xdg_open": which("xdg-open") is not None,
        "notify_send": which("notify-send") is not None,
        "kdialog": which("kdialog") is not None,
    }

    warnings: list[str] = []
    if is_wayland and (not capabilities["wl_copy"] or not capabilities["wl_paste"]):
        warnings.append(
            "wl-clipboard fehlt. Die Oberfläche startet weiter, native Zwischenablagefunktionen sind aber eingeschränkt."
        )
    if is_wayland and not wayland_display:
        warnings.append(
            "Wayland wurde erkannt, aber WAYLAND_DISPLAY fehlt. Ein nativer Qt-Wayland-Start ist so nicht möglich."
        )

    return DesktopPlatform(
        session_type=session_type or "unknown",
        wayland_display=wayland_display,
        display=display,
        current_desktop=current_desktop,
        desktop_session=desktop_session,
        distro_id=distro_id,
        distro_version=distro_version,
        distro_name=distro_name,
        is_wayland=is_wayland,
        is_kde=is_kde,
        is_kubuntu=is_kubuntu,
        ui_transport="wayland-native" if is_wayland and wayland_display else "unsupported",
        capabilities=capabilities,
        warnings=tuple(warnings),
    )


def validate_gui_environment(platform: DesktopPlatform) -> None:
    if not platform.is_kubuntu or not platform.distro_version.startswith("26.04"):
        raise PlatformCompatibilityError(
            "Diese VideoBatch-Ausbaustufe unterstützt ausschließlich Kubuntu 26.04 LTS."
        )
    if not platform.is_kde:
        raise PlatformCompatibilityError(
            "KDE Plasma wurde nicht erkannt. Zielsystem ist Kubuntu 26.04 mit Plasma."
        )
    if not platform.is_wayland:
        raise PlatformCompatibilityError(
            "Keine Wayland-Sitzung erkannt. X11 gehört nicht mehr zum unterstützten Zielpfad."
        )
    if not platform.wayland_display:
        raise PlatformCompatibilityError(
            "Wayland ist aktiv, aber WAYLAND_DISPLAY fehlt. Bitte neu in die Plasma-Wayland-Sitzung anmelden."
        )


def _state_dir(environ: Mapping[str, str] | None = None) -> Path:
    env = os.environ if environ is None else environ
    base = Path(env.get("XDG_STATE_HOME", str(Path.home() / ".local/state"))).expanduser()
    return base / "VideoBatchFast" / "startup"


def write_platform_report(
    platform: DesktopPlatform,
    *,
    environ: Mapping[str, str] | None = None,
    destination: Path | None = None,
) -> Path:
    target = destination or (_state_dir(environ) / "platform.json")
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(target.suffix + ".tmp")
    temporary.write_text(
        json.dumps(platform.to_dict(), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(target)
    return target


def prepare_gui_environment(
    environ: Mapping[str, str] | None = None,
    *,
    os_release_path: Path = Path("/etc/os-release"),
    which: Callable[[str], str | None] = shutil.which,
    report_destination: Path | None = None,
) -> DesktopPlatform:
    platform = detect_desktop_platform(
        environ,
        os_release_path=os_release_path,
        which=which,
    )
    write_platform_report(platform, environ=environ, destination=report_destination)
    validate_gui_environment(platform)
    return platform


def copy_text(text: str, platform: DesktopPlatform) -> bool:
    """Copy text through the native Wayland clipboard helper without shell interpolation."""
    if platform.is_wayland and platform.capabilities.get("wl_copy"):
        try:
            subprocess.run(
                ["wl-copy", "--type", "text/plain;charset=utf-8"],
                input=text,
                text=True,
                timeout=5,
                check=True,
            )
            return True
        except (OSError, subprocess.SubprocessError):
            return False
    return False


def open_path(path: str | Path, platform: DesktopPlatform) -> bool:
    if not platform.capabilities.get("xdg_open"):
        return False
    try:
        subprocess.Popen(
            ["xdg-open", str(Path(path).expanduser())],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        return True
    except OSError:
        return False
