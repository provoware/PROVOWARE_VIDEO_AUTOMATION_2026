from __future__ import annotations

import argparse
import sys

from .canonical_ui import run_app
from .instance_lock import ApplicationLock, InstanceAlreadyRunning, request_existing_instance_focus
from .platform_integration import PlatformCompatibilityError, prepare_gui_environment
from .startup_handshake import signal_ui_ready
from .versioning import build_label


def _platform_preflight() -> bool:
    try:
        platform = prepare_gui_environment()
    except PlatformCompatibilityError as exc:
        print(
            "VideoBatch konnte die grafische Sitzung nicht freigeben.\n"
            f"Grund: {exc}\n"
            "Kubuntu 26.04 / Wayland: Führen Sie "
            "'python3 scripts/kubuntu_26_04_wayland_check.py' aus.",
            file=sys.stderr,
        )
        return False

    warning_text = " | ".join(platform.warnings)
    if warning_text:
        print(
            f"VideoBatch Plattformhinweis: {warning_text}",
            file=sys.stderr,
        )
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="provoware - videoautomation - 2026")
    parser.add_argument("--version", action="store_true")
    args = parser.parse_args()
    if args.version:
        print(f"provoware - videoautomation - 2026 · {build_label()}")
        return 0
    if not _platform_preflight():
        return 2
    try:
        with ApplicationLock():
            run_app()
    except InstanceAlreadyRunning:
        request_existing_instance_focus()
        signal_ui_ready(existing_instance=True)
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
