#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
from pathlib import Path
from typing import Any

MANIFEST_NAME = "PORTABLE_RUNTIME_MANIFEST.json"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def build_manifest(root: Path, *, metadata: dict[str, Any]) -> dict[str, Any]:
    files: list[dict[str, Any]] = []
    for path in sorted(item for item in root.rglob("*") if item.is_file() and item.name != MANIFEST_NAME):
        relative = path.relative_to(root).as_posix()
        files.append({
            "path": relative,
            "size": path.stat().st_size,
            "sha256": sha256_file(path),
            "mode": oct(path.stat().st_mode & 0o777),
        })
    return {"schema_version": 1, **metadata, "file_count": len(files), "files": files}


def write_manifest(root: Path, *, metadata: dict[str, Any]) -> Path:
    manifest = build_manifest(root, metadata=metadata)
    target = root / MANIFEST_NAME
    target.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.chmod(target, 0o644)
    return target


def verify_manifest(root: Path) -> list[str]:
    target = root / MANIFEST_NAME
    if not target.is_file() or target.is_symlink():
        return [f"{MANIFEST_NAME} fehlt oder ist ein Link."]
    try:
        manifest = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return [f"Portable Manifest ist unlesbar: {exc}"]
    errors: list[str] = []
    declared: set[str] = set()
    for item in manifest.get("files", []):
        relative = str(item.get("path", ""))
        if not relative or relative.startswith("/") or ".." in Path(relative).parts:
            errors.append(f"Ungültiger Pfad: {relative}")
            continue
        declared.add(relative)
        path = root / relative
        if not path.is_file() or path.is_symlink():
            errors.append(f"Datei fehlt oder ist ein Link: {relative}")
            continue
        if path.stat().st_size != int(item.get("size", -1)):
            errors.append(f"Dateigröße stimmt nicht: {relative}")
            continue
        if sha256_file(path) != str(item.get("sha256", "")):
            errors.append(f"Prüfsumme stimmt nicht: {relative}")
    actual = {path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file() and path.name != MANIFEST_NAME}
    extras = sorted(actual - declared)
    missing = sorted(declared - actual)
    if extras:
        errors.append(f"Nicht manifestierte Datei: {extras[0]}")
    if missing:
        errors.append(f"Manifestierte Datei fehlt: {missing[0]}")
    if manifest.get("file_count") != len(declared):
        errors.append("Dateianzahl im Manifest ist inkonsistent.")
    return errors


def runtime_smoke_test(appdir: Path, *, timeout: int = 120) -> tuple[bool, str]:
    app_run = appdir / "AppRun"
    if not app_run.is_file() or not os.access(app_run, os.X_OK):
        return False, "AppRun fehlt oder ist nicht ausführbar."
    env = {**os.environ, "VIDEOBATCH_PORTABLE_SMOKE_TEST": "1"}
    completed = subprocess.run(
        [str(app_run), "--portable-smoke-test"],
        cwd=appdir,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=timeout,
        check=False,
        errors="replace",
    )
    output = completed.stdout[-8000:]
    ok = completed.returncode == 0 and "PORTABLE_RUNTIME_OK" in output
    return ok, output


def main() -> int:
    parser = argparse.ArgumentParser(description="Prüft die eingebettete VideoBatch-Laufzeit.")
    parser.add_argument("--verify", type=Path)
    parser.add_argument("--smoke", type=Path)
    args = parser.parse_args()
    if args.verify:
        errors = verify_manifest(args.verify)
        if errors:
            print("PORTABLE_VERIFY_FAILED")
            for error in errors:
                print(error)
            return 1
        print("PORTABLE_VERIFY_OK")
    if args.smoke:
        ok, detail = runtime_smoke_test(args.smoke)
        print(detail, end="" if detail.endswith("\n") else "\n")
        if not ok:
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
