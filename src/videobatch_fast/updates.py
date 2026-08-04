from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import time
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Callable

from .update_validation import UpdateCheck, read_manifest, safe_member, validate_update_package
from .safe_io import atomic_write_bytes



@dataclass(frozen=True, slots=True)
class UpdateInstallResult:
    success: bool
    version: str
    message: str
    backup: str = ""
    report: str = ""


def _safe_candidate_target(candidate: Path, relative: PurePosixPath) -> Path:
    target = candidate.joinpath(*relative.parts)
    parent = target.parent
    while parent != candidate.parent:
        if parent.is_symlink():
            raise OSError(f"Update-Ziel liegt unter einem symbolischen Link: {relative}")
        if parent == candidate:
            break
        parent = parent.parent
    if target.is_symlink():
        raise OSError(f"Update-Ziel ist ein symbolischer Link: {relative}")
    resolved_parent = target.parent.resolve()
    if resolved_parent != candidate and candidate not in resolved_parent.parents:
        raise OSError(f"Update-Ziel verlässt den Kandidaten: {relative}")
    return target


def _atomic_write(path: Path, data: bytes, mode: int) -> None:
    atomic_write_bytes(path, data, mode=mode)


def _release_manifest_snapshot(root: Path) -> dict[str, str]:
    manifest_path = root / "RELEASE_MANIFEST.json"
    if not manifest_path.is_file():
        raise OSError("Kandidat enthält kein RELEASE_MANIFEST.json.")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    items = manifest.get("files", [])
    if not isinstance(items, list):
        raise OSError("Release-Manifest enthält keine gültige Dateiliste.")
    snapshot: dict[str, str] = {}
    for item in items:
        relative = PurePosixPath(str(item.get("path", "")))
        if not safe_member(str(relative)):
            raise OSError(f"Release-Manifest enthält unsicheren Pfad: {relative}")
        path = root.joinpath(*relative.parts)
        if not path.is_file() or path.is_symlink():
            raise OSError(f"Release-Datei fehlt oder ist ein Link: {relative}")
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != str(item.get("sha256", "")):
            raise OSError(f"Release-Datei stimmt nicht mit Manifest überein: {relative}")
        snapshot[str(relative)] = digest
    if int(manifest.get("file_count", -1)) != len(snapshot):
        raise OSError("Release-Manifest-Dateizahl stimmt nicht.")
    return snapshot



_TREE_EXCLUDED_PARTS = {"__pycache__", ".git", ".pytest_cache", ".venv", "visual_actual", "quarantine", "keys", "diagnostics", "actual", "diff"}
_TREE_EXCLUDED_SUFFIXES = {".pyc", ".pyo", ".pvak", ".coverage"}


def _candidate_tree_snapshot(root: Path) -> dict[str, str]:
    snapshot: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.is_symlink():
            continue
        relative = path.relative_to(root)
        if any(part in _TREE_EXCLUDED_PARTS for part in relative.parts) or path.suffix in _TREE_EXCLUDED_SUFFIXES:
            continue
        snapshot[relative.as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return snapshot

def _write_report(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    _atomic_write(path, (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8"), 0o600)


def _fsync_directory(path: Path) -> None:
    try:
        fd = os.open(path, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    except OSError:
        pass


def apply_update_package(
    package: Path,
    install_root: Path,
    current_version: str,
    progress: Callable[[str, str], None] | None = None,
    timeout: int = 240,
) -> UpdateInstallResult:
    """Install a local update through immutable candidate verification and atomic swap."""
    progress = progress or (lambda phase, detail: None)
    check = validate_update_package(package, current_version)
    if not check.valid:
        return UpdateInstallResult(False, check.version, check.message)
    install_root = Path(install_root).resolve()
    parent = install_root.parent
    if not install_root.is_dir() or install_root.is_symlink():
        return UpdateInstallResult(False, check.version, "Installationsordner wurde nicht gefunden oder ist ein Link.")
    work = Path(tempfile.mkdtemp(prefix=".videobatch_update_", dir=parent))
    candidate = work / "candidate"
    from .paths import state_dir

    report_dir = state_dir() / "updates"
    report_path = report_dir / f"update_{time.strftime('%Y%m%d_%H%M%S')}.json"
    backup = parent / f"{install_root.name}.backup_{time.strftime('%Y%m%d_%H%M%S')}"
    activated = False
    try:
        progress("prepare", "Kandidat wird aus der bestehenden Installation erzeugt.")
        shutil.copytree(install_root, candidate, symlinks=True)
        with zipfile.ZipFile(package) as archive:
            manifest = read_manifest(archive)
            for item in manifest["files"]:
                relative = PurePosixPath(str(item["path"]))
                target = _safe_candidate_target(candidate, relative)
                operation = str(item["operation"])
                if operation == "delete":
                    if target.is_dir():
                        raise OSError(f"Update darf keine Verzeichnisse rekursiv löschen: {relative}")
                    target.unlink(missing_ok=True)
                    continue
                mode_text = str(item.get("mode", "0o644"))
                try:
                    mode = int(mode_text, 8) if mode_text.startswith("0o") else int(mode_text)
                except ValueError:
                    mode = 0o644
                _atomic_write(target, archive.read(str(relative)), mode & 0o777)

        progress("integrity", "Release-Manifest und Kandidat werden vor dem Selbsttest verglichen.")
        before = _release_manifest_snapshot(candidate)
        tree_before = _candidate_tree_snapshot(candidate)
        test_script = candidate / "test.sh"
        if not test_script.is_file():
            return UpdateInstallResult(False, check.version, "Kandidat enthält kein test.sh.", report=str(report_path))
        env = {
            **os.environ,
            "PYTHONPATH": str(candidate / "src"),
            "PYTHONDONTWRITEBYTECODE": "1",
            "VIDEOBATCH_EXTERNAL_QUALITY_MODE": "auto",
        }
        progress("self_test", "Kandidat wird vollständig und schreibgeschützt geprüft.")
        result = subprocess.run(
            ["bash", str(test_script)],
            cwd=candidate,
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
            errors="replace",
        )
        try:
            after = _release_manifest_snapshot(candidate)
            tree_after = _candidate_tree_snapshot(candidate)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            report = {
                "schema_version": 2,
                "version": check.version,
                "returncode": result.returncode,
                "candidate_unchanged": False,
                "integrity_error": str(exc),
                "stdout": result.stdout[-20_000:],
                "stderr": result.stderr[-20_000:],
            }
            _write_report(report_path, report)
            return UpdateInstallResult(
                False,
                check.version,
                "Selbsttest hat manifestierte Kandidatendateien verändert.",
                report=str(report_path),
            )
        unchanged = before == after and tree_before == tree_after
        report = {
            "schema_version": 2,
            "version": check.version,
            "returncode": result.returncode,
            "candidate_unchanged": unchanged,
            "manifest_files": len(after),
            "tree_files_before": len(tree_before),
            "tree_files_after": len(tree_after),
            "stdout": result.stdout[-20_000:],
            "stderr": result.stderr[-20_000:],
        }
        _write_report(report_path, report)
        if result.returncode != 0:
            return UpdateInstallResult(False, check.version, "Kandidat hat den Selbsttest nicht bestanden.", report=str(report_path))
        if not unchanged:
            return UpdateInstallResult(False, check.version, "Selbsttest hat manifestierte Kandidatendateien verändert.", report=str(report_path))

        progress("activate", "Unveränderter geprüfter Kandidat wird atomisch aktiviert.")
        if backup.exists():
            shutil.rmtree(backup)
        os.replace(install_root, backup)
        try:
            os.replace(candidate, install_root)
            _fsync_directory(parent)
            activated = True
        except Exception:
            os.replace(backup, install_root)
            _fsync_directory(parent)
            raise
        return UpdateInstallResult(
            True,
            check.version,
            "Update wurde unverändert geprüft, installiert und kann nach einem Neustart verwendet werden.",
            backup=str(backup),
            report=str(report_path),
        )
    except subprocess.TimeoutExpired:
        return UpdateInstallResult(False, check.version, "Der Update-Selbsttest hat das Zeitlimit überschritten.", report=str(report_path))
    except Exception as exc:
        if activated and backup.exists() and not install_root.exists():
            os.replace(backup, install_root)
        return UpdateInstallResult(
            False,
            check.version,
            f"Updateinstallation fehlgeschlagen: {exc}",
            backup=str(backup) if backup.exists() else "",
            report=str(report_path),
        )
    finally:
        shutil.rmtree(work, ignore_errors=True)
