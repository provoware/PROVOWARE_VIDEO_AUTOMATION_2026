from __future__ import annotations

import hashlib
import ctypes
import errno
import json
import shlex
import os
import shutil
import subprocess
import tempfile
import time
import zipfile
import uuid
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Callable

from .update_validation import UpdateCheck, read_manifest, safe_member, validate_update_package
from .safe_io import atomic_write_bytes, fsync_directory



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
    # Dieselbe geprüfte Fail-Closed-Grenze wie bei atomaren Dateischreibvorgängen.
    fsync_directory(path)


def _atomic_exchange_dirs(first: Path, second: Path) -> None:
    """Atomisch zwei vorhandene Verzeichnisse auf demselben Linux-Dateisystem tauschen.

    Anders als zwei aufeinanderfolgende os.replace-Aufrufe lässt RENAME_EXCHANGE
    den Installationsnamen auch bei abruptem Prozessende niemals unbesetzt.
    Auf nicht unterstützten Dateisystemen wird die Aktualisierung blockiert.
    """
    renameat2 = getattr(ctypes.CDLL(None, use_errno=True), "renameat2", None)
    if renameat2 is None:
        raise OSError(errno.ENOSYS, "Atomarer Linux-Verzeichnistausch nicht verfügbar")
    renameat2.argtypes = [
        ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint,
    ]
    renameat2.restype = ctypes.c_int
    at_fdcwd = -100
    rename_exchange = 2
    if renameat2(
        at_fdcwd, os.fsencode(first), at_fdcwd, os.fsencode(second), rename_exchange
    ) != 0:
        code = ctypes.get_errno()
        raise OSError(code, os.strerror(code), str(first))


def _ensure_independent_starter(install_root: Path) -> Path:
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


def _pending_update_path(install_root: Path) -> Path:
    return install_root.parent / f".{install_root.name}.update_pending.json"


def _remove_pending_update(journal: Path) -> None:
    journal.unlink(missing_ok=True)
    _fsync_directory(journal.parent)


def recover_interrupted_update(install_root: Path, *, failed_start: bool = False) -> bool:
    """Vor dem normalen GUI-Start eine unfertige lokale Installation zurückholen.

    Liefert True, wenn der bisherige bestätigte Programmordner wieder
    aktiviert wurde. Fehlen eindeutige Belege, wird nicht blind umbenannt.
    """
    install_root = Path(install_root).resolve()
    journal = _pending_update_path(install_root)
    if not journal.exists():
        return False
    if journal.is_symlink() or not journal.is_file():
        raise OSError("Update-Wiederanlaufdatei ist kein regulärer Eintrag.")
    record = json.loads(journal.read_text(encoding="utf-8"))
    if not isinstance(record, dict) or record.get("schema_version") != 1:
        raise ValueError("Update-Wiederanlaufdatei hat ein ungültiges Format.")
    if record.get("install_root") != str(install_root):
        raise ValueError("Update-Wiederanlaufdatei gehört zu einer anderen Installation.")
    candidate = Path(str(record.get("candidate", "")))
    backup = Path(str(record.get("backup", "")))
    parent = install_root.parent
    if (
        candidate.name != "candidate"
        or candidate.parent.parent != parent
        or not candidate.parent.name.startswith(".videobatch_update_")
        or backup.parent != parent
        or not backup.name.startswith(install_root.name + ".backup_")
    ):
        raise ValueError("Update-Wiederanlaufdatei enthält unzulässige Pfade.")
    phase = record.get("phase", "exchanging")
    if phase not in {"exchanging", "awaiting_first_start"}:
        raise ValueError("Update-Wiederanlaufdatei meldet eine unbekannte Phase.")
    old_id = (int(record["old_device"]), int(record["old_inode"]))
    if not install_root.is_dir() or install_root.is_symlink():
        raise OSError("Programmstartordner fehlt; keine automatische riskante Reparatur.")
    current = install_root.stat()
    if (current.st_dev, current.st_ino) == old_id:
        _remove_pending_update(journal)
        return False
    old_locations = []
    for location in (candidate, backup):
        if location.is_dir() and not location.is_symlink():
            info = location.stat()
            if (info.st_dev, info.st_ino) == old_id:
                old_locations.append(location)
    if phase == "awaiting_first_start" and not failed_start:
        # Ein aktivierter Kandidat darf zuerst EINMAL real starten.
        # Das Journal bleibt bis zur bestätigten Qt-Bereitschaft erhalten.
        if len(old_locations) != 1:
            raise OSError("Letzte bestätigte Installation ist nicht eindeutig gesichert.")
        return False
    for location in old_locations:
        if location.is_dir() and not location.is_symlink():
            info = location.stat()
            if (info.st_dev, info.st_ino) == old_id:
                _atomic_exchange_dirs(install_root, location)
                _fsync_directory(parent)
                _remove_pending_update(journal)
                return True
    raise OSError("Bisherige Installation nicht zweifelsfrei auffindbar; manuelle Diagnose nötig.")


def finish_local_update_first_start(install_root: Path, *, normal_ui_ready: bool) -> str:
    """Lokalen Update-Rückfall erst nach echtem Erststart endgültig freigeben.

    'confirmed': neuer Stand gestartet; Sicherung bleibt für Nutzer erhalten.
    'restored': Start gescheitert; alte Version ist wieder aktiv.
    'none': kein entsprechendes neues Update wartet auf die Bestätigung.
    """
    install_root = Path(install_root).resolve()
    journal = _pending_update_path(install_root)
    if not journal.exists():
        return "none"
    if journal.is_symlink() or not journal.is_file():
        raise OSError("Update-Journal ist kein regulärer Eintrag.")
    record = json.loads(journal.read_text(encoding="utf-8"))
    if not isinstance(record, dict) or record.get("phase") != "awaiting_first_start":
        raise ValueError("Update-Journal enthält keine ausstehende Erststart-Bestätigung.")
    if normal_ui_ready:
        # Wiederanlauf prüft erst Pfade, Gerätekennung und Sicherungs-Inode.
        recover_interrupted_update(install_root)
        if not journal.exists():
            # Der alte Stand war schon wieder aktiviert.
            return "none"
        _remove_pending_update(journal)
        return "confirmed"
    if recover_interrupted_update(install_root, failed_start=True):
        return "restored"
    return "none"


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
    backup = parent / f"{install_root.name}.backup_{time.strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex}"
    journal = _pending_update_path(install_root)
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
        test_script = candidate / "scripts/dev/test.sh"
        if not test_script.is_file():
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
        # An earlier backup is user data. Never delete or overwrite one for a
        # timestamp collision; a fresh opaque name is reserved for each update.
        if backup.exists() or backup.is_symlink():
            raise FileExistsError(f"Update-Sicherung bereits vorhanden: {backup}")
        if journal.exists() or journal.is_symlink():
            raise OSError("Vorherige Update-Transaktion nicht abgeschlossen; zuerst neu starten.")
        # The external launcher is installed BEFORE persisting a transaction.
        # A new broken STARTEN.sh or debug_launcher.py cannot disable recovery.
        _ensure_independent_starter(install_root)
        old_stat = install_root.stat()
        _write_report(journal, {
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
            _atomic_exchange_dirs(install_root, candidate)
            exchanged = True
            _fsync_directory(parent)
            # Erst nach dem Austausch wird die alte Version gesichert.
            # Bei SIGKILL davor liegt sie weiterhin im Arbeitsordner.
            os.replace(candidate, backup)
            _fsync_directory(parent)
            # Noch KEINE Bestätigung: erst der erste echte normale Qt-Start
            # beendet die Transaktion. Ein fehlerhafter Erststart fällt zurück.
            _write_report(journal, {
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
                    _atomic_exchange_dirs(install_root, old_location)
                    if old_location == backup:
                        # Hier liegt nach dem Rücktausch der fehlgeschlagene
                        # neue Kandidat, nicht die frühere Sicherung.
                        os.replace(backup, work / "failed_candidate")
                    _fsync_directory(parent)
            # Nach dokumentiertem Rückfall kann das Journal entfernt werden.
            if not exchanged or (install_root.exists() and install_root.stat().st_ino == old_stat.st_ino):
                _remove_pending_update(journal)
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
        # Bei einem unvollständigen Austausch muss die frühere Version im
        # temporären Kandidatenordner für den nächsten Start erhalten bleiben.
        if not journal.exists():
            shutil.rmtree(work, ignore_errors=True)
