from __future__ import annotations

import json
import os
import shlex
import shutil
import subprocess
import tempfile
import time
import uuid
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any, Callable, TYPE_CHECKING

if TYPE_CHECKING:
    from .updates import UpdateInstallResult

def _ensure_independent_starter(install_root: Path) -> Path:
    from .updates import _atomic_write

    """Provision an immutable-by-default rescue outside the replaceable tree.

    Existing, differing rescue files are NEVER overwritten: a mismatch blocks
    the update before the first directory exchange.
    """
    parent = install_root.parent
    source = Path(__file__).resolve().parents[2] / "scripts" / "local_update_rescue.py"
    if not source.is_file() or source.is_symlink():
        raise OSError("Unabhängiges Startprogramm fehlt; lokales Update blockiert.")
    controller = parent / f".{install_root.name}.independent_start.py"
    launcher = parent / f"{install_root.name}-SICHER-STARTEN.sh"
    controller_bytes = source.read_bytes()
    root_name = shlex.quote(install_root.name)
    rescue_name = shlex.quote(controller.name)
    wrapper_bytes = (
        "#!/usr/bin/env bash\n"
        "set -Eeuo pipefail\n"
        'BASE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"\n'
        f"APP={root_name}\n"
        f"HELPER={rescue_name}\n"
        'exec "${VIDEOBATCH_BOOTSTRAP_PYTHON:-python3}" "$BASE/$HELPER" "$BASE/$APP" "$@"\n'
    ).encode("utf-8")
    for path, contents in ((controller, controller_bytes), (launcher, wrapper_bytes)):
        if path.exists() or path.is_symlink():
            if path.is_symlink() or not path.is_file() or path.read_bytes() != contents:
                raise OSError(f"Externer Sicherheitsstarter widersprüchlich; nicht überschreiben: {path}")
            continue
        _atomic_write(path, contents, 0o700)
    # _atomic_write synchronizes the containing directory for new files.
    return launcher

def apply_update_package(
    package: Path,
    install_root: Path,
    current_version: str,
    progress: Callable[[str, str], None] | None = None,
    timeout: int = 240,
    *,
    _backend: Any,
) -> UpdateInstallResult:
    """Install a local update through immutable candidate verification and atomic swap."""
    progress = progress or (lambda phase, detail: None)
    check = _backend.validate_update_package(package, current_version)
    if not check.valid:
        return _backend.UpdateInstallResult(False, check.version, check.message)
    install_root = Path(install_root).resolve()
    parent = install_root.parent
    if not install_root.is_dir() or install_root.is_symlink():
        return _backend.UpdateInstallResult(False, check.version, "Installationsordner wurde nicht gefunden oder ist ein Link.")
    work = Path(tempfile.mkdtemp(prefix=".videobatch_update_", dir=parent))
    candidate = work / "candidate"
    from .paths import state_dir

    report_dir = state_dir() / "updates"
    report_path = report_dir / f"update_{time.strftime('%Y%m%d_%H%M%S')}.json"
    backup = parent / f"{install_root.name}.backup_{time.strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex}"
    journal = _backend._pending_update_path(install_root)
    activated = False
    try:
        progress("prepare", "Kandidat wird aus der bestehenden Installation erzeugt.")
        shutil.copytree(install_root, candidate, symlinks=True)
        _apply_files(package, candidate, _backend)

        progress("integrity", "Release-Manifest und Kandidat werden vor dem Selbsttest verglichen.")
        before = _backend._release_manifest_snapshot(candidate)
        tree_before = _backend._candidate_tree_snapshot(candidate)
        test_script = candidate / "scripts/dev/test.sh"
        if not test_script.is_file():
            test_script = candidate / "test.sh"  # Signed legacy packages retain their original entrypoint.
        if not test_script.is_file():
            return _backend.UpdateInstallResult(False, check.version, "Kandidat enthält kein test.sh.", report=str(report_path))
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
            after = _backend._release_manifest_snapshot(candidate)
            tree_after = _backend._candidate_tree_snapshot(candidate)
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
            _backend._write_report(report_path, report)
            return _backend.UpdateInstallResult(
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
        _backend._write_report(report_path, report)
        if result.returncode != 0:
            return _backend.UpdateInstallResult(False, check.version, "Kandidat hat den Selbsttest nicht bestanden.", report=str(report_path))
        if not unchanged:
            return _backend.UpdateInstallResult(False, check.version, "Selbsttest hat manifestierte Kandidatendateien verändert.", report=str(report_path))

        progress("activate", "Unveränderter geprüfter Kandidat wird atomisch aktiviert.")
        # An earlier backup is user data. Never delete or overwrite one for a
        # timestamp collision; a fresh opaque name is reserved for each update.
        if os.path.lexists(backup):
            raise FileExistsError(f"Update-Sicherung bereits vorhanden: {backup}")
        if journal.exists() or journal.is_symlink():
            raise OSError("Vorherige Update-Transaktion nicht abgeschlossen; zuerst neu starten.")
        # The external launcher is installed BEFORE persisting a transaction.
        # A new broken STARTEN.sh or debug_launcher.py cannot disable recovery.
        _backend._ensure_independent_starter(install_root)
        old_stat = install_root.stat()
        _backend._write_report(journal, {
            "schema_version": 1,
            "install_root": str(install_root),
            "candidate": str(candidate),
            "backup": str(backup),
            "old_device": old_stat.st_dev,
            "old_inode": old_stat.st_ino,
        })
        # _write_report nutzt atomar schreibende safe_io-Routine
        # und synchronisiert den übergeordneten Ordner bereits selbst.
        exchanged = False
        try:
            # Der alte Programmordner bleibt während des gesamten Wechsels
            # jederzeit unter einem Namen erreichbar. Beide Seiten liegen
            # auf demselben Datenträger; kein nicht-atomarer Zwischenzustand.
            _backend._atomic_exchange_dirs(install_root, candidate)
            exchanged = True
            _backend._fsync_directory(parent)
            # Erst nach dem Austausch wird die alte Version gesichert.
            # Bei SIGKILL davor liegt sie weiterhin im Arbeitsordner.
            os.replace(candidate, backup)
            _backend._fsync_directory(parent)
            # Noch KEINE Bestätigung: erst der erste echte normale Qt-Start
            # beendet die Transaktion. Ein fehlerhafter Erststart fällt zurück.
            _backend._write_report(journal, {
                "schema_version": 1,
                "phase": "awaiting_first_start",
                "install_root": str(install_root),
                "candidate": str(candidate),
                "backup": str(backup),
                "old_device": old_stat.st_dev,
                "old_inode": old_stat.st_ino,
            })
            activated = True
        except Exception:
            if exchanged:
                old_location = backup if backup.exists() else candidate
                if old_location.exists() and not old_location.is_symlink():
                    _backend._atomic_exchange_dirs(install_root, old_location)
                    if old_location == backup:
                        # Hier liegt nach dem Rücktausch der fehlgeschlagene
                        # neue Kandidat, nicht die frühere Sicherung.
                        os.replace(backup, work / "failed_candidate")
                    _backend._fsync_directory(parent)
            # Nach dokumentiertem Rückfall kann das Journal entfernt werden.
            if not exchanged or (install_root.exists() and install_root.stat().st_ino == old_stat.st_ino):
                _backend._remove_pending_update(journal)
            raise
        return _backend.UpdateInstallResult(
            True,
            check.version,
            "Update wurde unverändert geprüft, installiert und kann nach einem Neustart verwendet werden.",
            backup=str(backup),
            report=str(report_path),
        )
    except subprocess.TimeoutExpired:
        return _backend.UpdateInstallResult(False, check.version, "Der Update-Selbsttest hat das Zeitlimit überschritten.", report=str(report_path))
    except Exception as exc:
        if activated and backup.exists() and not install_root.exists():
            os.replace(backup, install_root)
        return _backend.UpdateInstallResult(
            False,
            check.version,
            f"Updateinstallation fehlgeschlagen: {exc}",
            backup=str(backup) if backup.exists() else "",
            report=str(report_path),
        )
    finally:
        # Bei einem unvollständigen Austausch muss die frühere Version im
        # temporären Kandidatenordner für den nächsten Start erhalten bleiben.
        if not journal.exists():
            shutil.rmtree(work, ignore_errors=True)


def _apply_files(package: Path, candidate: Path, _backend: Any) -> None:
    with zipfile.ZipFile(package) as archive:
        manifest = _backend.read_manifest(archive)
        for item in manifest["files"]:
            relative = PurePosixPath(str(item["path"]))
            target = _backend._safe_candidate_target(candidate, relative)
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
            _backend._atomic_write(target, archive.read(str(relative)), mode & 0o777)
