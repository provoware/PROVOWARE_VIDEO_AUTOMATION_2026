#!/usr/bin/env python3
from __future__ import annotations

import argparse
import fcntl
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

SCHEMA = 1


def fsync_dir(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(name, 0o600)
        os.replace(name, path)
        fsync_dir(path.parent)
    finally:
        try:
            os.unlink(name)
        except FileNotFoundError:
            pass


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def slot_from_current(root: Path) -> str | None:
    current = root / "current"
    if not current.is_symlink():
        return None
    target = os.readlink(current)
    normalized = Path(target)
    if normalized.is_absolute():
        try:
            normalized = normalized.relative_to(root)
        except ValueError:
            return None
    if normalized.as_posix() == "slots/A":
        return "A"
    if normalized.as_posix() == "slots/B":
        return "B"
    return None


def atomic_switch(root: Path, slot: str) -> None:
    if slot not in {"A", "B"}:
        raise RuntimeError("Ungültiger A/B-Slot.")
    target = root / "slots" / slot
    if not target.is_dir() or target.is_symlink():
        raise RuntimeError(f"Slot {slot} fehlt oder ist ungültig.")
    temp = root / f".current-{os.getpid()}-{time.time_ns()}"
    try:
        os.symlink(f"slots/{slot}", temp)
        os.replace(temp, root / "current")
        fsync_dir(root)
    finally:
        try:
            temp.unlink()
        except FileNotFoundError:
            pass


def append_history(state: dict[str, Any], event: dict[str, Any]) -> None:
    history = state.setdefault("history", [])
    if not isinstance(history, list):
        history = []
        state["history"] = history
    history.append({"utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), **event})
    del history[:-20]


def run_slot(root: Path, slot: str, args: list[str]) -> int:
    app_run = root / "slots" / slot / "AppRun"
    if not app_run.is_file() or not os.access(app_run, os.X_OK):
        return 72
    env = {
        **os.environ,
        "VIDEOBATCH_AB_SLOT": slot,
        "VIDEOBATCH_INSTALL_ROOT": str(root),
        "VIDEOBATCH_PORTABLE_LAUNCHER": str(Path.home() / ".local/bin/videobatch-fast"),
    }
    try:
        completed = subprocess.run([str(app_run), *args], cwd=app_run.parent, env=env, check=False)
    except OSError:
        return 73
    return int(completed.returncode)


def recover_or_launch(root: Path, args: list[str]) -> int:
    state_path = root / "installation_state.json"
    transaction_path = root / "pending_transaction.json"
    state = load_json(state_path)
    transaction = load_json(transaction_path)
    current = slot_from_current(root)

    if transaction:
        previous_value = transaction.get("previous_slot")
        previous = str(previous_value) if previous_value is not None else ""
        target = str(transaction.get("target_slot", ""))
        if target not in {"A", "B"} or previous not in {"", "A", "B"} or previous == target:
            return 74
        if previous and current == previous:
            # Der Stromausfall lag vor dem Umschalten. Der bekannte gute Slot bleibt aktiv.
            append_history(state, {"event": "transaction_not_switched", "target_slot": target})
            atomic_json(state_path, state)
            transaction_path.unlink(missing_ok=True)
            return run_slot(root, previous, args)
        if current != target:
            if previous:
                atomic_switch(root, previous)
                transaction_path.unlink(missing_ok=True)
                return run_slot(root, previous, args)
            transaction_path.unlink(missing_ok=True)
            return 76

        result = run_slot(root, target, args)
        if result == 0:
            target_state = transaction.get("target_state")
            if not isinstance(target_state, dict):
                return 75
            append_history(target_state, {
                "event": "boot_confirmed",
                "active_slot": target,
                "previous_slot": previous,
                "version": target_state.get("version"),
            })
            target_state["schema_version"] = 2
            target_state["active_slot"] = target
            target_state["previous_slot"] = previous or None
            target_state["pending_boot"] = False
            atomic_json(state_path, target_state)
            transaction_path.unlink(missing_ok=True)
            return 0

        # Erster echter Start ist fehlgeschlagen: atomar auf den letzten bestätigten Slot zurück.
        if previous:
            atomic_switch(root, previous)
            state["active_slot"] = previous
            state["previous_slot"] = target
            state["pending_boot"] = False
            append_history(state, {
                "event": "automatic_boot_rollback",
                "failed_slot": target,
                "restored_slot": previous,
                "failed_returncode": result,
            })
            atomic_json(state_path, state)
            transaction_path.unlink(missing_ok=True)
            fallback = run_slot(root, previous, args)
            return 0 if fallback == 0 else fallback
        # Erste Installation ohne bestätigten Rückfallslot: nicht als aktiv bestätigen.
        try:
            (root / "current").unlink(missing_ok=True)
            fsync_dir(root)
        except OSError:
            pass
        transaction_path.unlink(missing_ok=True)
        return result or 77

    if current not in {"A", "B"}:
        preferred = str(state.get("active_slot", ""))
        if preferred in {"A", "B"} and (root / "slots" / preferred / "AppRun").is_file():
            atomic_switch(root, preferred)
            current = preferred
        else:
            for candidate in ("A", "B"):
                if (root / "slots" / candidate / "AppRun").is_file():
                    atomic_switch(root, candidate)
                    current = candidate
                    break
    if current not in {"A", "B"}:
        return 76
    return run_slot(root, current, args)


def main() -> int:
    parser = argparse.ArgumentParser(description="VideoBatch A/B-Startcontroller")
    parser.add_argument("--install-root", type=Path, default=Path(os.environ.get("VIDEOBATCH_INSTALL_DIR", Path.home() / ".local/share/VideoBatchFast")))
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("arguments", nargs=argparse.REMAINDER)
    options = parser.parse_args()
    if options.self_test:
        print("AB_LAUNCHER_OK")
        return 0
    root = options.install_root.expanduser().resolve()
    arguments = list(options.arguments)
    if arguments[:1] == ["--"]:
        arguments = arguments[1:]
    root.mkdir(parents=True, exist_ok=True)
    lock_dir = root / "locks"
    lock_dir.mkdir(parents=True, exist_ok=True)
    with (lock_dir / "launch.lock").open("a+") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        return recover_or_launch(root, arguments)


if __name__ == "__main__":
    raise SystemExit(main())
