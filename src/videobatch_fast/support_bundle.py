from __future__ import annotations

import hashlib
import json
import os
import platform
import stat
import sys
import tempfile
import time
import zipfile
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any, Iterable

from .preparation_assistant import PreparationCheck
from .versioning import build_label, version_info

PROJECT_ROOT = Path(__file__).resolve().parents[2]
_MAX_LOG_BYTES = 1_000_000
_MAX_DEBUG_REPORTS = 6
_DEBUG_SUFFIXES = {".txt", ".log", ".json"}


class SupportBundleError(RuntimeError):
    pass


def support_bundle_filename() -> str:
    stamp = time.strftime("%Y%m%d_%H%M%S")
    return f"VideoBatch_SafeMode_Diagnose_{stamp}.zip"


def _json_bytes(payload: Any) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode(
        "utf-8"
    )


def _read_limited(path: Path, maximum: int = _MAX_LOG_BYTES) -> bytes | None:
    if not path.is_file() or path.is_symlink():
        return None
    try:
        size = path.stat().st_size
        with path.open("rb") as handle:
            if size > maximum:
                handle.seek(max(0, size - maximum))
            data = handle.read(maximum)
    except OSError:
        return None
    prefix = b"[... gekuerzt; nur letzter Diagnoseabschnitt enthalten ...]\n" if size > maximum else b""
    return prefix + data


def _env_file(name: str) -> Path | None:
    value = os.environ.get(name, "").strip()
    return Path(value).expanduser() if value else None


def _live_checks(checks: Iterable[PreparationCheck]) -> list[dict[str, str]]:
    result: list[dict[str, str]] = []
    for check in checks:
        if is_dataclass(check):
            item = asdict(check)
        else:
            item = {
                "key": getattr(check, "key", ""),
                "status": getattr(check, "status", ""),
                "title": getattr(check, "title", ""),
                "detail": getattr(check, "detail", ""),
                "action": getattr(check, "action", ""),
            }
        result.append({key: str(value) for key, value in item.items()})
    return result


def _debug_directories() -> tuple[Path, ...]:
    candidates: list[Path] = []
    configured = os.environ.get("VIDEOBATCH_DEBUG_DIR", "").strip()
    if configured:
        candidates.append(Path(configured).expanduser())
    candidates.append(PROJECT_ROOT / "debugging")
    state_root = Path(
        os.environ.get("XDG_STATE_HOME", Path.home() / ".local/state")
    ).expanduser()
    candidates.append(state_root / "VideoBatchFast" / "debugging")
    unique: list[Path] = []
    for candidate in candidates:
        if candidate not in unique:
            unique.append(candidate)
    return tuple(unique)


def _latest_debug_reports() -> list[Path]:
    files: list[Path] = []
    for directory in _debug_directories():
        if not directory.is_dir() or directory.is_symlink():
            continue
        try:
            files.extend(
                item
                for item in directory.iterdir()
                if item.is_file() and not item.is_symlink() and item.suffix.lower() in _DEBUG_SUFFIXES
            )
        except OSError:
            continue
    unique = {str(path.resolve(strict=False)): path for path in files}
    ranked: list[tuple[float, Path]] = []
    for path in unique.values():
        try:
            ranked.append((path.stat().st_mtime, path))
        except OSError:
            continue
    ranked.sort(key=lambda item: item[0], reverse=True)
    return [path for _mtime, path in ranked[:_MAX_DEBUG_REPORTS]]


def _runtime_version_payload() -> dict[str, Any]:
    return {
        "build": build_label(),
        "version": version_info(),
        "python": sys.version.replace("\n", " "),
        "interpreter": sys.executable,
        "platform": platform.platform(),
        "machine": platform.machine(),
        "safe_mode": os.environ.get("VIDEOBATCH_SAFE_MODE", "0") == "1",
        "startup_status": os.environ.get("VIDEOBATCH_STARTUP_STATUS", ""),
    }


def _safe_mode_payload(context: dict[str, Any] | None) -> dict[str, Any]:
    return {
        "active": True,
        "reason_code": os.environ.get("VIDEOBATCH_SAFE_MODE_REASON_CODE", "unknown"),
        "reason": os.environ.get(
            "VIDEOBATCH_SAFE_MODE_REASON",
            "Safe Mode wurde aktiviert; der genaue Ausloeser wurde vom Starter nicht uebergeben.",
        ),
        "startup_status": os.environ.get("VIDEOBATCH_STARTUP_STATUS", ""),
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "context": context or {},
    }


def _collect_entries(
    *, checks: Iterable[PreparationCheck], context: dict[str, Any] | None
) -> dict[str, bytes]:
    entries: dict[str, bytes] = {
        "README.txt": (
            "VideoBatch Fast · Safe-Mode-Diagnosepaket\n"
            "Dieses Archiv wurde lokal erzeugt und nicht automatisch versendet.\n"
            "Die Quelldateien wurden ausschliesslich gelesen und nicht veraendert.\n"
            "Das ZIP und seine enthaltenen Dateien werden als read-only markiert.\n"
            "Hinweis: Diagnoseprotokolle koennen lokale Datei- und Ordnerpfade enthalten.\n"
        ).encode("utf-8"),
        "safe_mode/cause.json": _json_bytes(_safe_mode_payload(context)),
        "startup/live_preparation_checks.json": _json_bytes(_live_checks(checks)),
        "version/runtime.json": _json_bytes(_runtime_version_payload()),
    }

    version_file = PROJECT_ROOT / "VERSION.json"
    version_data = _read_limited(version_file, maximum=250_000)
    if version_data is not None:
        entries["version/VERSION.json"] = version_data

    release_manifest = PROJECT_ROOT / "RELEASE_MANIFEST.json"
    manifest_data = _read_limited(release_manifest, maximum=500_000)
    if manifest_data is not None:
        entries["version/RELEASE_MANIFEST.json"] = manifest_data

    for env_name, archive_name in (
        ("VIDEOBATCH_STARTUP_REPORT", "startup/latest.json"),
        ("VIDEOBATCH_BOOTSTRAP_LOG", "logs/bootstrap.log"),
        ("VIDEOBATCH_APPLICATION_LOG", "logs/application.log"),
    ):
        path = _env_file(env_name)
        data = _read_limited(path) if path is not None else None
        if data is not None:
            entries[archive_name] = data

    used_names: set[str] = set()
    for index, path in enumerate(_latest_debug_reports(), start=1):
        data = _read_limited(path)
        if data is None:
            continue
        base = path.name
        archive_name = f"logs/debug/{index:02d}_{base}"
        while archive_name in used_names:
            archive_name = f"logs/debug/{index:02d}_{path.stem}_{len(used_names)}{path.suffix}"
        used_names.add(archive_name)
        entries[archive_name] = data

    return entries


def _manifest(entries: dict[str, bytes]) -> bytes:
    payload = {
        "schema_version": 1,
        "read_only": True,
        "files": [
            {
                "path": name,
                "size": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
            }
            for name, data in sorted(entries.items())
        ],
    }
    return _json_bytes(payload)


def _write_member(archive: zipfile.ZipFile, name: str, data: bytes) -> None:
    info = zipfile.ZipInfo(name, time.localtime()[:6])
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = (stat.S_IFREG | 0o444) << 16
    archive.writestr(info, data)


def export_safe_mode_support_bundle(
    target: Path | str,
    *,
    checks: Iterable[PreparationCheck] = (),
    context: dict[str, Any] | None = None,
) -> Path:
    if os.environ.get("VIDEOBATCH_SAFE_MODE", "0") != "1":
        raise SupportBundleError("Der Safe-Mode-Diagnoseexport ist nur im sicheren Startmodus verfuegbar.")

    destination = Path(target).expanduser()
    destination.parent.mkdir(parents=True, exist_ok=True)
    entries = _collect_entries(checks=checks, context=context)
    entries["manifest.json"] = _manifest(entries)

    fd, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent
    )
    os.close(fd)
    temporary = Path(temporary_name)
    try:
        with zipfile.ZipFile(temporary, "w") as archive:
            for name, data in sorted(entries.items()):
                _write_member(archive, name, data)
        with temporary.open("rb") as handle:
            os.fsync(handle.fileno())
        os.replace(temporary, destination)
        try:
            destination.chmod(0o444)
        except OSError:
            pass
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    return destination
