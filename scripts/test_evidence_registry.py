#!/usr/bin/env python3
"""Local, fail-closed reuse of small DEVELOPMENT tests. Never a release gate."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
import time
from importlib import metadata
from pathlib import Path

from project_file_index import ROOT, snapshot
from sha256_contract import digest_json
from test_dependency_scope import scoped_report

POLICY = ROOT / "registries/TEST_EVIDENCE_POLICY.json"


def sha(value: object) -> str:
    return digest_json(value)


def evidence_path() -> Path:
    base = os.environ.get("XDG_STATE_HOME", "")
    state = Path(base) if base and Path(base).is_absolute() else Path.home() / ".local/state"
    project_id = hashlib.sha256(str(ROOT.resolve()).encode()).hexdigest()[:12]
    return state / "videobatch" / "test_evidence" / f"{project_id}.json"


def git_identity() -> tuple[str, bool]:
    try:
        head = subprocess.run(
            ["git", "-C", str(ROOT), "rev-parse", "--verify", "HEAD"],
            capture_output=True, text=True, check=True, timeout=8,
        ).stdout.strip()
        status = subprocess.run(
            ["git", "-C", str(ROOT), "status", "--porcelain", "--untracked-files=all"],
            capture_output=True, text=True, check=True, timeout=8,
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return "", False
    return (head, not bool(status.strip())) if len(head) == 40 else ("", False)


def environment_digest() -> str:
    packages = sorted(
        (str(distribution.metadata.get("Name", "")).casefold(),
         distribution.version) for distribution in metadata.distributions()
    )
    return sha({
        "python": sys.version, "executable": sys.executable,
        "platform": platform.platform(), "machine": platform.machine(),
        "packages": packages,
        "environment": {key: os.environ.get(key, "") for key in (
            "QT_QPA_PLATFORM", "DISPLAY", "WAYLAND_DISPLAY",
            "XDG_CONFIG_HOME", "XDG_CACHE_HOME", "VIDEOBATCH_FFMPEG",
            "VIDEOBATCH_FFPROBE", "PYTHONPATH",
        )},
    })


def load_policy() -> dict:
    data = json.loads(POLICY.read_text(encoding="utf-8"))
    if data.get("schema_version") != 1 or data.get("mode") != "development_only":
        raise ValueError("Prüfregister besitzt eine unbekannte Sicherheitsregel")
    if not isinstance(data.get("tests"), dict):
        raise ValueError("Prüfregister enthält keine Testdefinitionen")
    return data


def current(test_id: str, policy: dict) -> dict:
    spec = policy["tests"].get(test_id)
    if not isinstance(spec, dict) or not spec.get("cacheable", False):
        raise ValueError(f"Nicht freigegebene oder nicht wiederverwendbare Prüfung: {test_id}")
    args = spec.get("argv", [])
    if not isinstance(args, list) or not args or args[0] != "{python}":
        raise ValueError("Nur explizite Python-Aufrufe aus dem Prüfregister sind zulässig")
    if any(not isinstance(value, str) or not value for value in args):
        raise ValueError("Prüfparameter sind ungültig")
    command = [sys.executable, *args[1:]]
    head, clean = git_identity()
    scope = scoped_report(test_id, snapshot())
    return {
        "test_id": test_id, "commit_sha": head,
        "clean_checkout": clean, "source_digest": scope["source_digest"],
        "scope_mode": scope["scope"],
        "environment_fingerprint": environment_digest(),
        "test_definition_digest": sha({"test": spec, "policy_version": policy["schema_version"]}),
        "command": command, "test_status": "not_run",
    }


def load_results() -> dict:
    try:
        value = json.loads(evidence_path().read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return {"schema_version": 1, "results": {}}
    if value.get("schema_version") != 1 or not isinstance(value.get("results"), dict):
        return {"schema_version": 1, "results": {}}
    return value


def matches(previous: object, latest: dict) -> bool:
    if not isinstance(previous, dict) or previous.get("test_status") != "passed":
        return False
    if not latest["clean_checkout"] or not latest["commit_sha"]:
        return False
    # Persisted results are not trusted merely because they say 'passed'.
    if previous.get("exit_code") != 0 or previous.get("reuse_allowed") is not True:
        return False
    if not isinstance(previous.get("completed_unix"), int) or previous["completed_unix"] <= 0:
        return False
    # Explicit scope allowlist; no release, security or CI gating is reused.
    mode = latest.get("scope_mode")
    if previous.get("scope_mode") != mode:
        return False
    if mode == "reviewed":
        policy = load_policy()
        allowed = policy.get("dependency_review", {}).get("approved_scopes", [])
        if latest.get("test_id") not in allowed:
            return False
    elif mode != "full_tree_fallback":
        return False
    keys = ("test_id", "commit_sha", "source_digest",
            "environment_fingerprint", "test_definition_digest", "command")
    return all(previous.get(key) == latest.get(key) for key in keys) and (
        previous.get("clean_checkout") is True
    )


def store(test_id: str, result: dict) -> None:
    value = load_results()
    value["results"][test_id] = result
    path = evidence_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    from tempfile import mkstemp
    fd, temporary = mkstemp(prefix=".test-evidence-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as output:
            json.dump(value, output, sort_keys=True, ensure_ascii=False, indent=2)
            output.write("\n")
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, path)
        descriptor = os.open(path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    finally:
        Path(temporary).unlink(missing_ok=True)


def execute(latest: dict, timeout: int) -> tuple[int, str]:
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONPATH"] = str(ROOT / "src") + (
        os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else ""
    )
    try:
        result = subprocess.run(
            latest["command"], cwd=ROOT, env=env,
            capture_output=True, text=True, errors="replace", timeout=timeout,
            check=False,
        )
        return result.returncode, (result.stdout + "\n" + result.stderr)[-3000:]
    except subprocess.TimeoutExpired:
        return 124, f"Prüfung nach {timeout} Sekunden zeitlich begrenzt."
    except OSError as exc:
        return 127, f"Prüfung konnte nicht gestartet werden: {exc}"


def run(test_id: str, reuse: bool) -> int:
    policy = load_policy()
    latest = current(test_id, policy)
    old = load_results()["results"].get(test_id)
    if reuse and matches(old, latest):
        print(f"REUSED · {test_id} · identischer sauberer Commit und identische Prüfumgebung")
        print("Keine Release- oder CI-Freigabe; nur wiederverwendeter lokaler Entwicklungstest.")
        return 0

    limit = int(policy["tests"][test_id].get("timeout_seconds", 120))
    if not 1 <= limit <= 900:
        raise ValueError("Zeitlimit außerhalb des zugelassenen Entwicklungsbereichs")
    code, log = execute(latest, limit)
    after = current(test_id, policy)
    stable = all(latest.get(key) == after.get(key) for key in (
        "commit_sha", "source_digest", "scope_mode", "environment_fingerprint",
        "test_definition_digest", "command", "clean_checkout",
    ))
    latest.update({
        "test_status": "passed" if code == 0 and stable else "stale" if not stable else "failed",
        "exit_code": code, "completed_unix": int(time.time()),
        "log_tail": log, "reuse_allowed": code == 0 and stable and latest["clean_checkout"],
    })
    store(test_id, latest)
    print(f"PRÜFSTATUS · {test_id}: {latest['test_status']} · Exit {code}")
    if log.strip():
        print(log)
    if not latest["clean_checkout"]:
        print("Arbeitskopie ist nicht sauber: Ergebnis bleibt dokumentiert, aber nicht wiederverwendbar.")
    return 0 if latest["test_status"] == "passed" else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Prüfregister: gezielte Tests, keine Stable-Freigabe")
    parser.add_argument("command", choices=["run", "check", "list"])
    parser.add_argument("test_id", nargs="?")
    parser.add_argument("--reuse", action="store_true", help="Nur identische saubere Prüfnachweise nutzen")
    args = parser.parse_args()
    try:
        policy = load_policy()
        if args.command == "list":
            for name, spec in sorted(policy["tests"].items()):
                print(f"{name}: {spec.get('purpose', '')}")
            return 0
        if not args.test_id:
            parser.error("Test-ID fehlt")
        if args.command == "run":
            return run(args.test_id, args.reuse)
        current_state = current(args.test_id, policy)
        valid = matches(load_results()["results"].get(args.test_id), current_state)
        print(f"STATUS {args.test_id}: {'REUSABLE' if valid else 'NEW_RUN_REQUIRED'}")
        return 0 if valid else 1
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        print(f"PRÜFREGISTER BLOCKIERT: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
