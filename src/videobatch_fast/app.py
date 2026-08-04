from __future__ import annotations

import argparse

from .instance_lock import ApplicationLock, InstanceAlreadyRunning, request_existing_instance_focus
from .startup_handshake import signal_ui_ready
from .ui import run_app
from .versioning import build_label


def main() -> int:
    parser = argparse.ArgumentParser(description="provoware - videoautomation - 2026")
    parser.add_argument("--version", action="store_true")
    args = parser.parse_args()
    if args.version:
        print(f"provoware - videoautomation - 2026 · {build_label()}")
        return 0
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
