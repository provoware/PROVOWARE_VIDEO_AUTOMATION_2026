#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import os
import socket
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from toolchain_common import (
    ROOT,
    build_manifest,
    load_contract,
    publish_directory,
    safe_remove_tree,
    verify_wheelhouse,
    write_manifest,
    write_resolved_lock,
)

CI_ONLINE_MARKER = "VIDEOBATCH_CI_ALLOW_PUBLIC_PYPI"


def state_root() -> Path:
    return Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local/state")) / "VideoBatchFast"


def progress(step: int, total: int, message: str) -> None:
    print(f"[{step}/{total}] {message}", flush=True)


def ci_online_authorized() -> bool:
    """Allow non-interactive network access only inside explicitly opted-in GitHub Actions."""
    return (
        os.environ.get("GITHUB_ACTIONS", "").strip().lower() == "true"
        and os.environ.get(CI_ONLINE_MARKER, "").strip() == "1"
    )


def graphical_session_available() -> bool:
    return bool(os.environ.get("DISPLAY", "").strip() or os.environ.get("WAYLAND_DISPLAY", "").strip())


def ask_online_repair_buttons(index_url: str) -> bool:
    """Ask for one-shot online repair consent using buttons only.

    This function intentionally lives in the low-level downloader so every user
    path, including direct toolchain calls, reaches the same fail-closed gate
    before DNS resolution or package download starts.
    """
    if not graphical_session_available():
        print(
            "Online-Reparatur blockiert: Es ist keine grafische Sitzung für die erforderliche Button-Freigabe verfügbar.",
            file=sys.stderr,
        )
        return False
    try:
        import tkinter as tk
    except Exception as exc:
        print(f"Online-Reparatur blockiert: Grafischer Bestätigungsdialog ist nicht verfügbar ({exc}).", file=sys.stderr)
        return False

    decision = {"allowed": False}
    root = None
    try:
        root = tk.Tk()
        root.title("VideoBatch – Online-Reparatur")
        root.resizable(False, False)
        root.protocol("WM_DELETE_WINDOW", root.destroy)

        frame = tk.Frame(root, padx=24, pady=20)
        frame.grid(row=0, column=0, sticky="nsew")
        tk.Label(
            frame,
            text="Lokale Abhängigkeiten reichen nicht aus.",
            font=("Sans", 12, "bold"),
            anchor="w",
            justify="left",
        ).grid(row=0, column=0, columnspan=2, sticky="w")
        tk.Label(
            frame,
            text=(
                "VideoBatch kann die exakt festgelegten fehlenden Python-Pakete online laden, "
                "anschließend prüfen und lokal für Offline-Starts speichern.\n\n"
                f"Paketquelle: {index_url}\n"
                "Es werden keine Projekt- oder Mediendateien hochgeladen."
            ),
            wraplength=560,
            anchor="w",
            justify="left",
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(12, 20))

        def decline() -> None:
            decision["allowed"] = False
            root.destroy()

        def allow() -> None:
            decision["allowed"] = True
            root.destroy()

        offline = tk.Button(frame, text="Offline bleiben", command=decline, width=18)
        online = tk.Button(frame, text="Online reparieren", command=allow, width=18)
        offline.grid(row=2, column=0, padx=(0, 8), sticky="e")
        online.grid(row=2, column=1, padx=(8, 0), sticky="w")
        root.bind("<Escape>", lambda _event: decline())
        root.bind("<Return>", lambda _event: allow())
        online.focus_set()
        try:
            root.attributes("-topmost", True)
            root.after(350, lambda: root.winfo_exists() and root.attributes("-topmost", False))
        except tk.TclError:
            pass
        root.mainloop()
    except Exception as exc:
        print(f"Online-Reparatur blockiert: Bestätigungsdialog konnte nicht geöffnet werden ({exc}).", file=sys.stderr)
        return False
    finally:
        if root is not None:
            try:
                if root.winfo_exists():
                    root.destroy()
            except Exception:
                pass
    return bool(decision["allowed"])


def online_authorized(index_url: str) -> bool:
    if ci_online_authorized():
        return True
    allowed = ask_online_repair_buttons(index_url)
    if not allowed:
        print("Online-Reparatur nicht freigegeben; es findet kein DNS-/PyPI-Zugriff statt.", file=sys.stderr)
    return allowed


def preflight(index_url: str) -> list[str]:
    errors: list[str] = []
    pip_check = subprocess.run(
        [sys.executable, "-m", "pip", "--version"], cwd=ROOT, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False,
    )
    if pip_check.returncode:
        errors.append("pip fehlt; temporäre isolierte pip-Umgebung wird versucht")
    hosts = {"files.pythonhosted.org"}
    host = urlparse(index_url).hostname if index_url else "pypi.org"
    if host:
        hosts.add(host)
    for hostname in sorted(hosts):
        try:
            socket.getaddrinfo(hostname, 443, type=socket.SOCK_STREAM)
        except socket.gaierror as exc:
            errors.append(f"DNS-Auflösung fehlgeschlagen: {hostname} ({exc})")
    return errors


def resolve_pip_runner() -> tuple[list[str], Path | None]:
    """Return a working pip command without requiring system-wide python3-pip.

    Ubuntu/Kubuntu can provide ``venv`` without exposing ``pip`` as a system
    module. In that case we create a short-lived bootstrap venv and use only
    its pip for downloading the exact locked wheels.
    """
    if importlib.util.find_spec("pip") is not None:
        return [sys.executable, "-m", "pip"], None

    parent = Path(tempfile.gettempdir()) / "VideoBatchFast" / "bootstrap"
    parent.mkdir(parents=True, exist_ok=True)
    bootstrap = Path(tempfile.mkdtemp(prefix="pip-", dir=parent))
    created = subprocess.run(
        [sys.executable, "-m", "venv", str(bootstrap)],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    if created.returncode:
        detail = (created.stdout or "").strip()[-3000:]
        safe_remove_tree(bootstrap, allowed_parent=parent)
        suffix = f"\n{detail}" if detail else ""
        raise RuntimeError(
            "Weder System-pip noch eine temporäre pip-Umgebung sind verfügbar. "
            "Auf Kubuntu/Ubuntu fehlt sehr wahrscheinlich python3-venv. "
            "Installierbares Systempaket: python3-venv." + suffix
        )

    python = bootstrap / "bin" / "python"
    verify = subprocess.run(
        [str(python), "-m", "pip", "--version"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    if verify.returncode:
        detail = (verify.stdout or "").strip()[-3000:]
        safe_remove_tree(bootstrap, allowed_parent=parent)
        suffix = f"\n{detail}" if detail else ""
        raise RuntimeError(
            "Die temporäre pip-Umgebung wurde erstellt, enthält aber kein funktionsfähiges pip."
            + suffix
        )
    return [str(python), "-m", "pip"], bootstrap


def write_log(output: str | None) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    candidates = (
        state_root() / "toolchain",
        Path(tempfile.gettempdir()) / "VideoBatchFast" / "toolchain",
    )
    last_error: OSError | None = None
    for target in candidates:
        try:
            target.mkdir(parents=True, exist_ok=True)
            path = target / f"wheelhouse-download-{stamp}.log"
            path.write_text(output or "(keine Prozessausgabe)\n", encoding="utf-8", errors="replace")
            return path
        except OSError as exc:
            last_error = exc
    fallback = Path(tempfile.gettempdir()) / f"videobatch-wheelhouse-{stamp}.log"
    try:
        fallback.write_text(output or "(keine Prozessausgabe)\n", encoding="utf-8", errors="replace")
        return fallback
    except OSError:
        if last_error is not None:
            print(f"! Downloadprotokoll konnte nicht gespeichert werden: {last_error}", file=sys.stderr)
        return Path(os.devnull)


def publish(staging: Path, output: Path) -> None:
    """Kompatibler, sicherer Einstieg für ältere Tests und Werkzeuge."""
    publish_directory(staging, output)


def main() -> int:
    parser = argparse.ArgumentParser(description="Baut das einheitliche Offline-Wheelhouse atomar auf.")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--index-url", default="")
    parser.add_argument("--scope", choices=("runtime", "all"), default="all")
    args = parser.parse_args()

    contract = load_contract()
    index_url = args.index_url or str(contract["policy"]["public_index"])
    if not online_authorized(index_url):
        return 4

    output = (args.output or ROOT / contract["paths"]["wheelhouse"]).resolve(strict=False)
    output.parent.mkdir(parents=True, exist_ok=True)
    staging: Path | None = None

    progress(1, 5, "Internet- und Python-Voraussetzungen prüfen")
    errors = preflight(index_url)
    fatal_errors = [error for error in errors if not error.startswith("pip fehlt")]
    for error in errors:
        marker = "!" if error.startswith("pip fehlt") else "✕"
        print(f"{marker} {error}", file=sys.stderr)
    if fatal_errors:
        print("Automatische Vorbereitung konnte keine Paketquelle erreichen.", file=sys.stderr)
        return 5

    bootstrap_pip: Path | None = None
    try:
        try:
            pip_command, bootstrap_pip = resolve_pip_runner()
        except RuntimeError as exc:
            print(f"✕ {exc}", file=sys.stderr)
            return 7
        staging = Path(tempfile.mkdtemp(prefix=f".{output.name}.build-", dir=output.parent))
        lock_key = "runtime_lock" if args.scope == "runtime" else "unified_lock"
        lock = ROOT / contract["paths"][lock_key]
        progress(2, 5, "Exakt gesperrte Pakete laden")
        command = [
            *pip_command, "download",
            "--disable-pip-version-check", "--progress-bar", "off", "--quiet",
            "--only-binary=:all:", "--dest", str(staging),
            "--requirement", str(lock), "--index-url", index_url,
        ]
        completed = subprocess.run(
            command, cwd=ROOT, text=True, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, check=False,
        )
        log = write_log(completed.stdout)
        if completed.returncode:
            print(f"✕ Paketdownload fehlgeschlagen. Detailprotokoll: {log}", file=sys.stderr)
            print((completed.stdout or "(keine Prozessausgabe)")[-3000:], file=sys.stderr)
            return completed.returncode

        progress(3, 5, "Wheel-Dateien identifizieren und hashen")
        manifest = build_manifest(staging)
        write_manifest(staging, manifest)
        write_resolved_lock(staging, manifest, contract)

        progress(4, 5, "Manifest, Versionen und Prüfsummen verifizieren")
        verification = verify_wheelhouse(staging, contract, scope=args.scope)
        if verification:
            for error in verification:
                print(f"✕ {error}", file=sys.stderr)
            return 6

        progress(5, 5, "Geprüftes Wheelhouse atomar veröffentlichen")
        publish_directory(staging, output)
        staging = None
        print(f"✓ Einheits-Wheelhouse bereit: {manifest['wheel_count']} Wheels")
        print(f"  Speicherort: {output}")
        print(f"  Downloadprotokoll: {log}")
        return 0
    finally:
        if staging is not None and staging.exists():
            safe_remove_tree(staging, allowed_parent=output.parent)
        if bootstrap_pip is not None and bootstrap_pip.exists():
            safe_remove_tree(bootstrap_pip, allowed_parent=bootstrap_pip.parent)


if __name__ == "__main__":
    raise SystemExit(main())
