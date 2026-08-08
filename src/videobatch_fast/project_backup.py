from __future__ import annotations

import hashlib
import json
import os
import re
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .paths import state_dir
from .safe_io import SafeIoError, atomic_commit_file, atomic_write_bytes, exclusive_file_lock
from .transaction_store import TransactionError, transactional_write_json
from .project_state import PROJECT_SCHEMA_VERSION


class ProjectBackupError(RuntimeError):
    pass


MAX_PROJECT_STATE_BYTES = 16 * 1024 * 1024
MAX_MANIFEST_BYTES = 64 * 1024
DEFAULT_BACKUP_RETENTION = 30


@dataclass(frozen=True)
class ProjectBackupRecord:
    path: Path
    created_at: str
    source: Path
    sha256: str
    size_bytes: int


def project_backup_directory() -> Path:
    directory = state_dir() / "backups" / "projects"
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def _safe_stem(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", value.strip()).strip("._")
    return cleaned[:80] or "projekt"


def _history_path(directory: Path) -> Path:
    return directory / "history.json"


def _history_meta_path(directory: Path) -> Path:
    return directory / "history.meta.json"


def _history_digest(items: list[dict[str, object]]) -> str:
    payload = json.dumps(items, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _lock_path(directory: Path) -> Path:
    return directory / ".project-backup.lock"


def _read_history(directory: Path) -> list[dict[str, object]]:
    path = _history_path(directory)
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if not isinstance(value, list):
        return []
    items = [item for item in value if isinstance(item, dict)]
    meta_path = _history_meta_path(directory)
    if meta_path.exists():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            if (
                not isinstance(meta, dict)
                or int(meta.get("schema_version", 0) or 0) != 1
                or int(meta.get("count", -1)) != len(items)
                or str(meta.get("history_sha256", "")) != _history_digest(items)
            ):
                return []
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            return []
    return items


def _write_history(directory: Path, items: list[dict[str, object]]) -> None:
    canonical = items[:50]
    meta = {
        "schema_version": 1,
        "count": len(canonical),
        "history_sha256": _history_digest(canonical),
    }
    try:
        transactional_write_json(
            directory,
            {
                _history_path(directory): canonical,
                _history_meta_path(directory): meta,
            },
        )
    except (OSError, SafeIoError, TransactionError) as exc:
        raise ProjectBackupError("Die Backuphistorie konnte nicht transaktional gespeichert werden.") from exc


def _create_project_backup_locked(project_file: Path) -> ProjectBackupRecord:
    source = Path(project_file).expanduser().resolve()
    if not source.is_file():
        raise ProjectBackupError("Die aktuelle Projektdatei ist nicht erreichbar.")
    try:
        payload = source.read_bytes()
        if len(payload) > MAX_PROJECT_STATE_BYTES:
            raise ProjectBackupError("Die Projektdatei überschreitet das sichere Sicherungslimit von 16 MiB.")
        project_payload = json.loads(payload.decode("utf-8"))
        if not isinstance(project_payload, dict):
            raise ProjectBackupError("Die Projektdatei enthält kein gültiges VideoBatch-Projektobjekt.")
    except ProjectBackupError:
        raise
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ProjectBackupError("Die Projektdatei ist nicht als gültiges UTF-8-JSON lesbar.") from exc

    directory = project_backup_directory()
    now = datetime.now(timezone.utc)
    timestamp = now.strftime("%Y%m%dT%H%M%S_%fZ")
    target = directory / f"{_safe_stem(source.stem)}_{timestamp}.vbfast-backup.zip"
    digest = hashlib.sha256(payload).hexdigest()
    manifest = {
        "schema_version": 1,
        "created_at": now.isoformat(timespec="seconds"),
        "source_name": source.name,
        "source_sha256": digest,
        "source_size_bytes": len(payload),
        "project_schema_version": int(project_payload.get("schema_version", PROJECT_SCHEMA_VERSION) or PROJECT_SCHEMA_VERSION),
        "scope": "project_state_only",
    }
    temporary = target.with_name(f".{target.name}.{os.getpid()}.tmp")
    try:
        with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr(source.name, payload)
            archive.writestr(
                "backup_manifest.json",
                json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8"),
            )
        with zipfile.ZipFile(temporary, "r") as archive:
            if archive.testzip() is not None:
                raise ProjectBackupError("Die erzeugte Sicherung ist beschädigt.")
            restored = archive.read(source.name)
            if hashlib.sha256(restored).hexdigest() != digest:
                raise ProjectBackupError("Die Sicherung stimmt nicht mit der Projektdatei überein.")
        atomic_commit_file(temporary, target)
    except (OSError, SafeIoError, zipfile.BadZipFile) as exc:
        temporary.unlink(missing_ok=True)
        raise ProjectBackupError("Die Projektsicherung konnte nicht sicher erstellt werden.") from exc
    finally:
        temporary.unlink(missing_ok=True)

    history = _read_history(directory)
    history.insert(
        0,
        {
            "path": str(target),
            "created_at": manifest["created_at"],
            "source": str(source),
            "sha256": digest,
            "size_bytes": target.stat().st_size,
        },
    )
    _write_history(directory, history)
    try:
        _prune_project_backups_locked(directory, keep=DEFAULT_BACKUP_RETENTION)
    except ProjectBackupError:
        # The newly verified backup remains valid even if housekeeping fails.
        pass
    return ProjectBackupRecord(
        path=target,
        created_at=str(manifest["created_at"]),
        source=source,
        sha256=digest,
        size_bytes=target.stat().st_size,
    )



def create_project_backup(project_file: Path) -> ProjectBackupRecord:
    directory = project_backup_directory()
    try:
        with exclusive_file_lock(_lock_path(directory), timeout_seconds=10.0):
            return _create_project_backup_locked(project_file)
    except SafeIoError as exc:
        raise ProjectBackupError("Die Projektsicherung ist durch einen parallelen Sicherungsvorgang blockiert.") from exc


def verify_project_backup(path: Path | str) -> dict[str, object]:
    backup = Path(path).expanduser()
    try:
        with zipfile.ZipFile(backup, "r") as archive:
            if archive.testzip() is not None:
                raise ProjectBackupError("Die Projektsicherung enthält beschädigte ZIP-Daten.")
            member_names = archive.namelist()
            if len(member_names) != len(set(member_names)):
                raise ProjectBackupError("Die Projektsicherung enthält doppelte ZIP-Einträge.")
            names = set(member_names)
            if "backup_manifest.json" not in names:
                raise ProjectBackupError("Der Sicherung fehlt das Manifest.")
            manifest_info = archive.getinfo("backup_manifest.json")
            if manifest_info.file_size > MAX_MANIFEST_BYTES:
                raise ProjectBackupError("Das Sicherungsmanifest ist ungewöhnlich groß und wurde aus Sicherheitsgründen abgewiesen.")
            manifest = json.loads(archive.read("backup_manifest.json").decode("utf-8"))
            if not isinstance(manifest, dict) or manifest.get("scope") != "project_state_only":
                raise ProjectBackupError("Der Sicherungsvertrag ist ungültig.")
            if int(manifest.get("schema_version", -1)) != 1:
                raise ProjectBackupError("Die Manifest-Schemaversion der Projektsicherung wird nicht unterstützt.")
            source_name = str(manifest.get("source_name", ""))
            expected = str(manifest.get("source_sha256", ""))
            if not source_name or source_name not in names or not expected:
                raise ProjectBackupError("Die Sicherung enthält keine gültige Projektdatei.")
            if names != {"backup_manifest.json", source_name}:
                raise ProjectBackupError("Die Projektsicherung enthält unerwartete Zusatzdateien.")
            source_info = archive.getinfo(source_name)
            if source_info.file_size > MAX_PROJECT_STATE_BYTES:
                raise ProjectBackupError("Die Projektdatei der Sicherung überschreitet das sichere Größenlimit.")
            payload = archive.read(source_name)
            if hashlib.sha256(payload).hexdigest() != expected:
                raise ProjectBackupError("Die Projektdatei der Sicherung stimmt nicht mit dem Manifest überein.")
            project_payload = json.loads(payload.decode("utf-8"))
            if not isinstance(project_payload, dict):
                raise ProjectBackupError("Die Sicherung enthält kein gültiges VideoBatch-Projektobjekt.")
            if int(manifest.get("source_size_bytes", -1)) != len(payload):
                raise ProjectBackupError("Die Projektgröße der Sicherung stimmt nicht mit dem Manifest überein.")
            schema = int(project_payload.get("schema_version", PROJECT_SCHEMA_VERSION) or PROJECT_SCHEMA_VERSION)
            declared_schema = int(manifest.get("project_schema_version", schema) or schema)
            if declared_schema != schema:
                raise ProjectBackupError("Die Projektschemaversion stimmt nicht mit dem Sicherungsmanifest überein.")
            return manifest
    except ProjectBackupError:
        raise
    except (OSError, zipfile.BadZipFile, UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError) as exc:
        raise ProjectBackupError("Die Projektsicherung ist nicht vollständig lesbar oder verifizierbar.") from exc


def restore_project_backup(backup_path: Path | str, target: Path | str, *, overwrite: bool = False) -> Path:
    backup = Path(backup_path).expanduser()
    destination = Path(target).expanduser()
    if destination.exists() and not overwrite:
        raise ProjectBackupError("Die Ziel-Projektdatei existiert bereits; Überschreiben wurde nicht freigegeben.")
    manifest = verify_project_backup(backup)
    source_name = str(manifest["source_name"])
    with zipfile.ZipFile(backup, "r") as archive:
        payload = archive.read(source_name)
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        atomic_write_bytes(destination, payload)
    except (OSError, SafeIoError) as exc:
        raise ProjectBackupError("Die Projektsicherung konnte nicht atomar wiederhergestellt werden.") from exc
    return destination



def _record_from_verified_backup(path: Path, manifest: dict[str, object]) -> ProjectBackupRecord:
    return ProjectBackupRecord(
        path=path,
        created_at=str(manifest.get("created_at", "")),
        source=Path(str(manifest.get("source_name", "projekt.vbfast.json"))),
        sha256=str(manifest.get("source_sha256", "")),
        size_bytes=path.stat().st_size,
    )


def _verified_backup_records(directory: Path) -> dict[Path, ProjectBackupRecord]:
    """Discover valid archives directly so history loss cannot hide recoverable backups."""
    records: dict[Path, ProjectBackupRecord] = {}
    for path in directory.glob("*.vbfast-backup.zip"):
        try:
            resolved = path.resolve()
            manifest = verify_project_backup(resolved)
            records[resolved] = _record_from_verified_backup(resolved, manifest)
        except (OSError, ProjectBackupError, TypeError, ValueError):
            continue
    return records


def _reconciled_backup_records(directory: Path) -> list[ProjectBackupRecord]:
    discovered = _verified_backup_records(directory)
    ordered: list[ProjectBackupRecord] = []
    seen: set[Path] = set()
    for item in _read_history(directory):
        try:
            path = Path(str(item["path"])).expanduser().resolve()
            record = discovered.get(path)
            if record is None or record.sha256 != str(item["sha256"]):
                continue
            ordered.append(
                ProjectBackupRecord(
                    path=record.path,
                    created_at=str(item.get("created_at", record.created_at)),
                    source=Path(str(item.get("source", record.source))),
                    sha256=record.sha256,
                    size_bytes=record.size_bytes,
                )
            )
            seen.add(path)
        except (KeyError, TypeError, ValueError, OSError):
            continue
    orphans = [record for path, record in discovered.items() if path not in seen]
    ordered.extend(orphans)
    # Manifest timestamps plus the microsecond filename are authoritative after a crash.
    # Sorting the merged set prevents a newly committed orphan from appearing behind stale history.
    ordered.sort(key=lambda item: (item.created_at, item.path.name), reverse=True)
    return ordered


def _history_items(records: list[ProjectBackupRecord]) -> list[dict[str, object]]:
    return [
        {
            "path": str(record.path),
            "created_at": record.created_at,
            "source": str(record.source),
            "sha256": record.sha256,
            "size_bytes": record.size_bytes,
        }
        for record in records
    ]


def _prune_project_backups_locked(directory: Path, *, keep: int = DEFAULT_BACKUP_RETENTION) -> list[Path]:
    """Rotate only verified VideoBatch-owned backups; caller owns the backup lock."""
    keep_count = max(1, int(keep))
    records = _reconciled_backup_records(directory)
    kept = records[:keep_count]
    removed: list[Path] = []
    for record in records[keep_count:]:
        try:
            record.path.unlink()
            removed.append(record.path)
        except FileNotFoundError:
            continue
        except OSError as exc:
            raise ProjectBackupError(f"Alte Projektsicherung konnte nicht sicher rotiert werden: {record.path}") from exc
    if removed:
        try:
            from .safe_io import fsync_directory
            fsync_directory(directory)
        except SafeIoError as exc:
            raise ProjectBackupError("Die Backup-Rotation konnte nicht dauerhaft synchronisiert werden.") from exc
    _write_history(directory, _history_items(kept))
    return removed


def prune_project_backups(*, keep: int = DEFAULT_BACKUP_RETENTION) -> list[Path]:
    directory = project_backup_directory()
    try:
        with exclusive_file_lock(_lock_path(directory), timeout_seconds=10.0):
            return _prune_project_backups_locked(directory, keep=keep)
    except SafeIoError as exc:
        raise ProjectBackupError("Die Backup-Rotation ist durch einen parallelen Sicherungsvorgang blockiert.") from exc


def list_project_backups(*, limit: int = 50) -> list[ProjectBackupRecord]:
    """Return verified backups and serialize self-healing against backup mutations."""
    directory = project_backup_directory()
    try:
        with exclusive_file_lock(_lock_path(directory), timeout_seconds=2.0):
            records = _reconciled_backup_records(directory)
            limit_count = max(0, int(limit))
            selected = records[:limit_count]
            canonical_history = _history_items(records[:50])
            if _read_history(directory) != canonical_history:
                try:
                    _write_history(directory, canonical_history)
                except ProjectBackupError:
                    pass
            return selected
    except SafeIoError as exc:
        raise ProjectBackupError("Die Backuphistorie ist vorübergehend durch einen parallelen Vorgang gesperrt.") from exc


def latest_project_backup() -> ProjectBackupRecord | None:
    records = list_project_backups(limit=1)
    return records[0] if records else None


def rebuild_project_backup_history(directory: Path | str | None = None) -> list[ProjectBackupRecord]:
    """Rebuild history/meta only from independently verified backup archives."""
    target_dir = Path(directory).expanduser() if directory is not None else project_backup_directory()
    target_dir.mkdir(parents=True, exist_ok=True)
    try:
        with exclusive_file_lock(_lock_path(target_dir), timeout_seconds=10.0):
            records = _reconciled_backup_records(target_dir)
            _write_history(target_dir, _history_items(records[:50]))
            return records
    except SafeIoError as exc:
        raise ProjectBackupError("Die Backuphistorie ist für den Wiederaufbau durch einen parallelen Vorgang gesperrt.") from exc
