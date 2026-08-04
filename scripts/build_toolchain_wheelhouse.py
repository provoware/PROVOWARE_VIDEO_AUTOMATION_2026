#!/usr/bin/env python3
from __future__ import annotations

import argparse
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


def state_root() -> Path:
    return Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local/state")) / "VideoBatchFast"


def progress(step: int, total: int, message: str) -> None:
    print(f"[{step}/{total}] {message}", flush=True)


def preflight(index_url: str) -> list[str]:
    errors: list[str] = []
    pip_check = subprocess.run(
        [sys.executable, "-m", "pip", "--version"], cwd=ROOT, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False,
    )
    if pip_check.returncode:
        errors.append("pip fehlt. Kubuntu: sudo apt install python3-pip python3-venv")
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
    if os.environ.get("VIDEOBATCH_ALLOW_PUBLIC_PYPI") != "1":
        print("Online-Bezug blockiert: Start muss über ./videobatch.sh erfolgen.", file=sys.stderr)
        return 4

    contract = load_contract()
    index_url = args.index_url or str(contract["policy"]["public_index"])
    output = (args.output or ROOT / contract["paths"]["wheelhouse"]).resolve(strict=False)
    output.parent.mkdir(parents=True, exist_ok=True)
    staging: Path | None = None

    progress(1, 5, "Internet- und Python-Voraussetzungen prüfen")
    errors = preflight(index_url)
    if errors:
        for error in errors:
            print(f"✕ {error}", file=sys.stderr)
        print("Automatische Vorbereitung konnte keine Paketquelle erreichen.", file=sys.stderr)
        return 5

    try:
        staging = Path(tempfile.mkdtemp(prefix=f".{output.name}.build-", dir=output.parent))
        lock_key = "runtime_lock" if args.scope == "runtime" else "unified_lock"
        lock = ROOT / contract["paths"][lock_key]
        progress(2, 5, "Exakt gesperrte Pakete laden")
        command = [
            sys.executable, "-m", "pip", "download",
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


if __name__ == "__main__":
    raise SystemExit(main())
