#!/usr/bin/env python3
from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import re
import shlex
import stat
import shutil
import ssl
import subprocess
import textwrap
import sys
import tarfile
import tempfile
import time
import urllib.parse
import urllib.request
from pathlib import Path, PurePosixPath
from typing import Any, Iterable

def _sha256_bootstrap(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _contract_record(manifest: dict[str, Any]) -> dict[str, Any] | None:
    components = manifest.get("components")
    if not isinstance(components, dict):
        return None
    for component in components.values():
        if not isinstance(component, dict):
            continue
        files = component.get("files")
        if not isinstance(files, list):
            continue
        for record in files:
            if isinstance(record, dict) and record.get("path") == "usr/app/scripts/ab_contract.py":
                return record
    return None


def _bootstrap_contract_module() -> None:
    """Repair the RC15→RC16 controller bridge without trusting arbitrary files.

    RC15 knew only ``ab_installer.py`` and ``ab_launcher.py``. During the first
    online upgrade it can therefore publish the RC16 controller without the new
    contract module. The missing module is copied only from an installed A/B slot
    whose closed slot manifest contains the exact expected SHA-256 and size.
    Both slots are checked so a later application rollback keeps the newest
    compatible controller operational.
    """
    own = Path(__file__).resolve().with_name("ab_contract.py")
    if own.is_file() and not own.is_symlink():
        return
    resolved = Path(__file__).resolve()
    try:
        root = resolved.parents[3]
    except IndexError as exc:
        raise ModuleNotFoundError("ab_contract") from exc
    candidates: list[tuple[int, Path]] = []
    for slot in ("A", "B"):
        manifest_path = root / "slot_manifests" / f"{slot}.json"
        candidate = root / "slots" / slot / "usr" / "app" / "scripts" / "ab_contract.py"
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            continue
        if not isinstance(manifest, dict) or not candidate.is_file() or candidate.is_symlink():
            continue
        record = _contract_record(manifest)
        if not record:
            continue
        try:
            expected_size = int(record["size"]); expected_hash = str(record["sha256"])
            sequence = int(manifest.get("release_sequence", 0))
        except (KeyError, TypeError, ValueError):
            continue
        if candidate.stat().st_size != expected_size or _sha256_bootstrap(candidate) != expected_hash:
            continue
        candidates.append((sequence, candidate))
    if not candidates:
        raise ModuleNotFoundError("ab_contract")
    source = max(candidates, key=lambda item: item[0])[1]
    own.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".ab_contract.", dir=own.parent)
    try:
        with os.fdopen(fd, "wb") as handle, source.open("rb") as source_handle:
            shutil.copyfileobj(source_handle, handle)
            handle.flush(); os.fsync(handle.fileno())
        os.chmod(temporary, 0o644)
        os.replace(temporary, own)
        fsync_fd = os.open(own.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(fsync_fd)
        finally:
            os.close(fsync_fd)
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass


try:
    from ab_contract import (
        COMPONENTS, ContractError, key_id, safe_relative, validate_channel_index,
        validate_manifest as validate_manifest_contract, validate_slot_snapshot,
        version_tuple as contract_version_tuple,
    )
except ModuleNotFoundError:
    sys.dont_write_bytecode = True
    _bootstrap_contract_module()
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from ab_contract import (
        COMPONENTS, ContractError, key_id, safe_relative, validate_channel_index,
        validate_manifest as validate_manifest_contract, validate_slot_snapshot,
        version_tuple as contract_version_tuple,
    )

MAX_INDEX_BYTES = 2 * 1024 * 1024
MAX_MANIFEST_BYTES = 16 * 1024 * 1024
SLOTS = ("A", "B")
MIN_FREE_BYTES = 256 * 1024 * 1024
DISK_SAFETY_NUMERATOR = 125
DISK_SAFETY_DENOMINATOR = 100


class InstallError(RuntimeError):
    def __init__(self, message: str, code: int = 1) -> None:
        super().__init__(message)
        self.code = code


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def fsync_dir(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def atomic_json(path: Path, payload: dict[str, Any], mode: int = 0o600) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(name, mode)
        os.replace(name, path)
        fsync_dir(path.parent)
    finally:
        try:
            os.unlink(name)
        except FileNotFoundError:
            pass


def atomic_text(path: Path, text: str, mode: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(name, mode)
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


def ensure_command(name: str) -> None:
    if shutil.which(name) is None:
        raise InstallError(f"Benötigtes Systemwerkzeug fehlt: {name}", 10)


def verify_raw_signature(file: Path, signature: Path, public_key: Path) -> None:
    if not file.is_file() or file.is_symlink() or not signature.is_file() or signature.is_symlink():
        raise InstallError(f"Signaturmaterial fehlt: {file.name}", 12)
    completed = subprocess.run(
        ["openssl", "pkeyutl", "-verify", "-pubin", "-inkey", str(public_key), "-rawin", "-in", str(file), "-sigfile", str(signature)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if completed.returncode:
        raise InstallError(f"Ed25519-Signatur ist ungültig: {file.name}", 13)


def origin(url: str) -> tuple[str, str, int | None]:
    parsed = urllib.parse.urlparse(url)
    return parsed.scheme.lower(), (parsed.hostname or "").lower(), parsed.port


def safe_url(base: str, value: str) -> str:
    if not value:
        raise InstallError("Downloadadresse fehlt.", 31)
    url = urllib.parse.urljoin(base, value)
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in {"https", "file"}:
        raise InstallError(f"Unsicheres oder nicht unterstütztes Downloadprotokoll: {parsed.scheme or 'leer'}", 31)
    base_parsed = urllib.parse.urlparse(base)
    if base_parsed.scheme == "https" and origin(url) != origin(base):
        raise InstallError("Kanaldateien dürfen ohne neuen signierten Vertrauensvertrag nicht auf einen anderen Host umleiten.", 31)
    if parsed.username or parsed.password or parsed.fragment:
        raise InstallError("Downloadadresse enthält unzulässige Zugangsdaten oder Fragmente.", 31)
    return url


def download(url: str, target: Path, maximum: int) -> None:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in {"https", "file"}:
        raise InstallError("Nur HTTPS- und lokale file://-Quellen sind zugelassen.", 31)
    target.parent.mkdir(parents=True, exist_ok=True)
    context = ssl.create_default_context()
    request = urllib.request.Request(url, headers={"User-Agent": "VideoBatchFast-AB-Updater/2", "Accept": "application/octet-stream, application/json"})
    try:
        with urllib.request.urlopen(request, timeout=45, context=context) as response:
            final_url = response.geturl()
            final = urllib.parse.urlparse(final_url)
            if parsed.scheme == "https" and (final.scheme != "https" or origin(final_url) != origin(url)):
                raise InstallError("Unsichere oder hostübergreifende Weiterleitung wurde blockiert.", 32)
            length = response.headers.get("Content-Length")
            if length:
                try:
                    announced = int(length)
                except ValueError as exc:
                    raise InstallError("Server meldet eine ungültige Dateigröße.", 33) from exc
                if announced < 0 or announced > maximum:
                    raise InstallError("Download überschreitet die erlaubte Größe.", 33)
            fd, name = tempfile.mkstemp(prefix=f".{target.name}.", dir=target.parent)
            total = 0
            try:
                with os.fdopen(fd, "wb") as handle:
                    while True:
                        block = response.read(1024 * 1024)
                        if not block:
                            break
                        total += len(block)
                        if total > maximum:
                            raise InstallError("Download überschreitet die erlaubte Größe.", 33)
                        handle.write(block)
                    handle.flush()
                    os.fsync(handle.fileno())
                if total == 0:
                    raise InstallError("Download ist leer.", 33)
                os.chmod(name, 0o600)
                os.replace(name, target)
                fsync_dir(target.parent)
            finally:
                try:
                    os.unlink(name)
                except FileNotFoundError:
                    pass
    except InstallError:
        raise
    except Exception as exc:
        raise InstallError(f"Download fehlgeschlagen: {url} · {exc}", 34) from exc


def version_tuple(value: str) -> tuple[int, int, int, int]:
    try:
        return contract_version_tuple(value)
    except ContractError:
        return (0, 0, 0, 0)


def validate_manifest(manifest: dict[str, Any], public_key: Path | None = None) -> None:
    try:
        validate_manifest_contract(manifest, expected_key_id=key_id(public_key) if public_key else None)
    except ContractError as exc:
        raise InstallError(str(exc), 20) from exc


def load_source(options: argparse.Namespace, cache: Path, public_key: Path) -> tuple[dict[str, Any], Path, str]:
    trusted_key_id = key_id(public_key)
    if not options.online:
        manifest_path = options.bundle_root / "INSTALLER_MANIFEST.json"
        signature_path = options.bundle_root / "INSTALLER_MANIFEST.ed25519"
        verify_raw_signature(manifest_path, signature_path, public_key)
        manifest = load_json(manifest_path)
        validate_manifest(manifest, public_key)
        return manifest, options.bundle_root, manifest_path.as_uri()

    if not options.index_url:
        raise InstallError("Für Online-Updates fehlt --index-url.", 30)
    index_path = cache / "channel-index.json"
    index_sig = cache / "channel-index.ed25519"
    download(options.index_url, index_path, MAX_INDEX_BYTES)
    download(safe_url(options.index_url, options.index_signature_url or "channel-index.ed25519"), index_sig, 4096)
    verify_raw_signature(index_path, index_sig, public_key)
    index = load_json(index_path)
    try:
        validate_channel_index(index, expected_key_id=trusted_key_id)
    except ContractError as exc:
        raise InstallError(str(exc), 35) from exc
    channel = index["channels"].get(options.channel)
    if not isinstance(channel, dict) or not channel.get("available"):
        raise InstallError(f"Updatekanal ist nicht verfügbar: {options.channel}", 35)
    manifest_url = safe_url(options.index_url, str(channel.get("manifest_url", "")))
    signature_url = safe_url(options.index_url, str(channel.get("manifest_signature_url", "")))
    release_root = cache / f"release-{channel.get('release_sequence', 'unknown')}"
    release_root.mkdir(parents=True, exist_ok=True)
    manifest_path = release_root / "INSTALLER_MANIFEST.json"
    signature_path = release_root / "INSTALLER_MANIFEST.ed25519"
    download(manifest_url, manifest_path, MAX_MANIFEST_BYTES)
    download(signature_url, signature_path, 4096)
    verify_raw_signature(manifest_path, signature_path, public_key)
    if manifest_path.stat().st_size != int(channel.get("manifest_size", -1)) or sha256(manifest_path) != str(channel.get("manifest_sha256", "")):
        raise InstallError("Manifest stimmt nicht mit dem signierten Channel-Index überein.", 35)
    manifest = load_json(manifest_path)
    validate_manifest(manifest, public_key)
    if str(manifest.get("version")) != str(channel.get("version")) or int(manifest.get("release_sequence")) != int(channel.get("release_sequence")):
        raise InstallError("Channel-Index und Release-Manifest widersprechen sich.", 35)
    manifest["_online_manifest_url"] = manifest_url
    manifest["_channel_generation"] = int(index["generation"])
    manifest["_channel_index_sha256"] = sha256(index_path)
    manifest["_channel_expires_utc"] = str(index["expires_utc"])
    return manifest, release_root, manifest_url


def current_slot(root: Path) -> str | None:
    link = root / "current"
    if not link.is_symlink():
        return None
    target = Path(os.readlink(link))
    if target.as_posix() == "slots/A":
        return "A"
    if target.as_posix() == "slots/B":
        return "B"
    return None


def safe_remove(path: Path, root: Path) -> None:
    resolved_root = root.resolve()
    try:
        parent = path.parent.resolve()
    except FileNotFoundError:
        parent = path.parent
    if parent != resolved_root and resolved_root not in parent.parents:
        raise InstallError(f"Löschschutz blockiert Pfad außerhalb des Installationsbereichs: {path}", 40)
    if path.is_symlink() or path.is_file():
        path.unlink(missing_ok=True)
    elif path.is_dir():
        shutil.rmtree(path)


def copy_slot(source: Path, target: Path) -> None:
    if target.exists() or target.is_symlink():
        raise InstallError("Staging-Ziel existiert bereits.", 41)
    completed = subprocess.run(["cp", "-a", "--reflink=auto", str(source), str(target)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)
    if completed.returncode:
        shutil.copytree(source, target, symlinks=False)


def safe_extract(archive: Path, target: Path, part: dict[str, Any]) -> None:
    expected_members = int(part.get("member_count", -1))
    expected_unpacked = int(part.get("unpacked_bytes", -1))
    with tarfile.open(archive, "r:*") as bundle:
        members = bundle.getmembers()
        if len(members) != expected_members:
            raise InstallError(f"Teilpaket enthält eine unerwartete Anzahl Einträge: {archive.name}", 42)
        seen: set[str] = set()
        unpacked = 0
        for member in members:
            name = member.name
            pure = PurePosixPath(name)
            if name in seen or name.startswith("/") or ".." in pure.parts or "." in pure.parts:
                raise InstallError(f"Unsicherer oder doppelter Archiveintrag: {archive.name}:{name}", 42)
            seen.add(name)
            if member.issym() or member.islnk() or member.isdev() or member.isfifo() or not (member.isfile() or member.isdir()):
                raise InstallError(f"Nicht zugelassener Archiveintrag: {archive.name}:{name}", 42)
            if member.mode & (stat.S_ISUID | stat.S_ISGID | stat.S_ISVTX):
                raise InstallError(f"Unsicherer Dateimodus im Teilpaket: {archive.name}:{name}", 42)
            if member.isfile():
                unpacked += int(member.size)
            if unpacked > expected_unpacked:
                raise InstallError(f"Teilpaket überschreitet die signierte Entpackgröße: {archive.name}", 42)
        if unpacked != expected_unpacked:
            raise InstallError(f"Entpackgröße stimmt nicht mit dem signierten Vertrag überein: {archive.name}", 42)
        bundle.extractall(target, members=members, filter="data")


def verify_file(path: Path, record: dict[str, Any]) -> None:
    if not path.is_file() or path.is_symlink():
        raise InstallError(f"Datei fehlt oder ist ein Link: {record.get('path')}", 43)
    if path.stat().st_size != int(record.get("size", -1)) or sha256(path) != str(record.get("sha256", "")):
        raise InstallError(f"Dateiprüfung fehlgeschlagen: {record.get('path')}", 43)
    expected_mode = int(str(record.get("mode", "0o644")), 8)
    if path.stat().st_mode & 0o777 != expected_mode:
        os.chmod(path, expected_mode)


def tree_hash(records: Iterable[dict[str, Any]]) -> str:
    digest = hashlib.sha256()
    for record in sorted(records, key=lambda item: str(item["path"])):
        digest.update(f"{record['path']}\0{record['mode']}\0{record['size']}\0{record['sha256']}\n".encode())
    return digest.hexdigest()


def verify_component(slot: Path, component: dict[str, Any]) -> None:
    records = component.get("files", [])
    for record in records:
        verify_file(slot / str(record["path"]), record)
    if tree_hash(records) != str(component.get("tree_sha256", "")):
        raise InstallError("Komponentenbaum stimmt nicht mit dem signierten Vertrag überein.", 43)
    install_path = str(component.get("install_path", "."))
    if install_path != ".":
        root = slot / install_path
        actual = {path.relative_to(slot).as_posix() for path in root.rglob("*") if path.is_file() and not path.is_symlink()} if root.is_dir() else set()
        expected = {str(record["path"]) for record in records}
        extras = actual - expected
        missing = expected - actual
        if extras or missing:
            detail = sorted(extras or missing)[0]
            raise InstallError(f"Komponente enthält unerwartete oder fehlende Datei: {detail}", 43)


def expected_slot_files(manifest: dict[str, Any]) -> set[str]:
    return {
        str(record["path"])
        for component_id in manifest["update_order"]
        for record in manifest["components"][component_id]["files"]
    }


def verify_slot(slot: Path, manifest: dict[str, Any]) -> None:
    if not slot.is_dir() or slot.is_symlink():
        raise InstallError("Slot fehlt oder ist ein symbolischer Link.", 43)
    expected = expected_slot_files(manifest)
    actual: set[str] = set()
    for path in slot.rglob("*"):
        relative = path.relative_to(slot).as_posix()
        if path.is_symlink():
            raise InstallError(f"Symbolischer Link im Anwendungsslot ist nicht zugelassen: {relative}", 43)
        mode = path.lstat().st_mode
        if stat.S_ISREG(mode):
            actual.add(relative)
        elif not stat.S_ISDIR(mode):
            raise InstallError(f"Spezialdatei im Anwendungsslot ist nicht zugelassen: {relative}", 43)
    extras = actual - expected
    missing = expected - actual
    if extras or missing:
        detail = sorted(extras or missing)[0]
        kind = "unerwartet" if extras else "fehlend"
        raise InstallError(f"Vollständiger Slot enthält eine {kind}e Datei: {detail}", 43)
    for component_id in manifest["update_order"]:
        verify_component(slot, manifest["components"][component_id])
    app_run = slot / "AppRun"
    if not app_run.is_file() or not os.access(app_run, os.X_OK):
        raise InstallError("AppRun fehlt oder ist nicht ausführbar.", 44)
    for command, marker in (("--portable-verify", "PORTABLE_VERIFY_OK"), ("--portable-smoke-test", "PORTABLE_RUNTIME_OK")):
        completed = subprocess.run([str(app_run), command], cwd=slot, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=180, check=False, errors="replace")
        if completed.returncode or marker not in completed.stdout:
            raise InstallError(f"Slot-Selbsttest fehlgeschlagen: {command}\n{completed.stdout[-2000:]}", 44)


def fsync_tree(root: Path) -> None:
    files: list[Path] = []
    directories: list[Path] = []
    for path in root.rglob("*"):
        if path.is_symlink():
            raise InstallError(f"Symlink kann nicht dauerhaft synchronisiert werden: {path}", 43)
        if path.is_file():
            files.append(path)
        elif path.is_dir():
            directories.append(path)
    for path in files:
        descriptor = os.open(path, os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    for path in sorted(directories, key=lambda item: len(item.parts), reverse=True):
        fsync_dir(path)
    fsync_dir(root)


def slot_size_bytes(manifest: dict[str, Any]) -> int:
    return sum(int(record["size"]) for component in manifest["components"].values() for record in component["files"])


def preflight_disk_space(root: Path, cache: Path, manifest: dict[str, Any], changed: list[str]) -> None:
    candidate = slot_size_bytes(manifest)
    downloads = sum(int(part["size"]) for part in manifest["parts"] if str(part["component"]) in changed)
    root_required = max(MIN_FREE_BYTES, candidate * DISK_SAFETY_NUMERATOR // DISK_SAFETY_DENOMINATOR)
    cache_required = max(64 * 1024 * 1024, downloads * DISK_SAFETY_NUMERATOR // DISK_SAFETY_DENOMINATOR)
    if shutil.disk_usage(root).free < root_required:
        raise InstallError(f"Zu wenig freier Speicher für den vollständigen inaktiven Slot. Benötigt werden mindestens {root_required / 1024**3:.2f} GiB.", 47)
    if shutil.disk_usage(cache).free < cache_required:
        raise InstallError(f"Zu wenig freier Speicher für die signierten Updatepakete. Benötigt werden mindestens {cache_required / 1024**2:.0f} MiB.", 47)


def download_required_parts(manifest: dict[str, Any], source_root: Path, manifest_url: str, changed: set[str], public_key: Path) -> Path:
    parts_dir = source_root / "parts"
    parts_dir.mkdir(parents=True, exist_ok=True)
    online = bool(manifest.get("_online_manifest_url"))
    for part in manifest["parts"]:
        if str(part["component"]) not in changed:
            continue
        file = parts_dir / str(part["file"])
        signature = parts_dir / str(part.get("signature_file", f"{part['file']}.ed25519"))
        if online:
            part_url = safe_url(manifest_url, str(part.get("url", f"parts/{part['file']}")))
            signature_url = safe_url(manifest_url, str(part.get("signature_url", f"parts/{signature.name}")))
            download(part_url, file, int(manifest["maximum_part_bytes"]))
            download(signature_url, signature, 4096)
        if not file.is_file() or file.is_symlink() or file.stat().st_size != int(part["size"]) or file.stat().st_size > int(manifest["maximum_part_bytes"]) or sha256(file) != str(part["sha256"]):
            raise InstallError(f"Teilpaket ist ungültig: {part['file']}", 45)
        verify_raw_signature(file, signature, public_key)
    return parts_dir


def install_controller(source_root: Path, public_key: Path, root: Path, version: str) -> None:
    source_installer = source_root / "scripts" / "ab_installer.py"
    source_launcher = source_root / "scripts" / "ab_launcher.py"
    source_contract = source_root / "scripts" / "ab_contract.py"
    for path in (source_installer, source_launcher, source_contract, public_key):
        if not path.is_file() or path.is_symlink():
            raise InstallError(f"Controllerdatei fehlt: {path.name}", 50)
    versions = root / "controller" / "versions"
    versions.mkdir(parents=True, exist_ok=True)
    target = versions / version
    stage = versions / f".{version}.stage-{os.getpid()}"
    safe_remove(stage, root) if stage.exists() else None
    stage.mkdir()
    for source in (source_installer, source_launcher, source_contract, public_key):
        shutil.copy2(source, stage / source.name)
    os.chmod(stage / "ab_installer.py", 0o755)
    os.chmod(stage / "ab_launcher.py", 0o755)
    subprocess.run([sys.executable, "-m", "py_compile", str(stage / "ab_installer.py"), str(stage / "ab_launcher.py"), str(stage / "ab_contract.py")], check=True)
    completed = subprocess.run([sys.executable, str(stage / "ab_launcher.py"), "--self-test"], text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
    if completed.returncode or "AB_LAUNCHER_OK" not in completed.stdout:
        raise InstallError("Neuer Startcontroller hat seinen Selbsttest nicht bestanden.", 50)
    if target.exists():
        safe_remove(target, root)
    os.replace(stage, target)
    controller = root / "controller"
    current_link = controller / "current"
    previous_link = controller / "previous"
    old_target = os.readlink(current_link) if current_link.is_symlink() else None
    temp = controller / f".current-{os.getpid()}"
    os.symlink(f"versions/{version}", temp)
    os.replace(temp, current_link)
    if old_target and old_target != f"versions/{version}":
        temp_prev = controller / f".previous-{os.getpid()}"
        os.symlink(old_target, temp_prev)
        os.replace(temp_prev, previous_link)
    fsync_dir(controller)


def install_user_wrappers(root: Path, index_url: str | None, channel: str) -> None:
    bin_dir = _prepare_optional_user_directory(Path.home() / ".local/bin", root / "user-launchers" / "bin")
    app_dir = _prepare_optional_user_directory(Path.home() / ".local/share/applications", root / "user-launchers" / "applications")
    launch = bin_dir / "videobatch-fast"
    atomic_text(
        launch,
        "#!/usr/bin/env bash\nset -u\n"
        f"ROOT={shlex.quote(str(root))}\n"
        "for CTRL in \"$ROOT/controller/current/ab_launcher.py\" \"$ROOT/controller/previous/ab_launcher.py\"; do\n"
        "  [[ -f \"$CTRL\" ]] || continue\n"
        "  python3 \"$CTRL\" --install-root \"$ROOT\" -- \"$@\"; RC=$?\n"
        "  [[ $RC -lt 70 || $RC -gt 79 ]] && exit $RC\n"
        "done\nexit 76\n",
        0o755,
    )
    update = bin_dir / "videobatch-update"
    online_args = ""
    if index_url:
        online_args = f" --online --channel={shlex.quote(channel)} --index-url={shlex.quote(index_url)}"
    atomic_text(
        update,
        "#!/usr/bin/env bash\nset -Eeuo pipefail\n"
        f"ROOT={shlex.quote(str(root))}\n"
        "CTRL=\"$ROOT/controller/current/ab_installer.py\"\n"
        "[[ -f \"$CTRL\" ]] || CTRL=\"$ROOT/controller/previous/ab_installer.py\"\n"
        f"exec python3 \"$CTRL\" --bundle-root \"$(dirname \"$CTRL\")\" --install-root \"$ROOT\"{online_args} \"$@\"\n",
        0o755,
    )
    desktop = app_dir / "videobatch-fast.desktop"
    escaped_exec = str(launch).replace("\\", "\\\\").replace('"', '\\"')
    atomic_text(
        desktop,
        "[Desktop Entry]\nType=Application\nName=VideoBatch Fast\nComment=VideoBatch starten\n"
        f"Exec=\"{escaped_exec}\"\nTerminal=false\nCategories=AudioVideo;Video;\nStartupNotify=true\n",
        0o644,
    )


def plan_changes(manifest: dict[str, Any], state: dict[str, Any], force: bool) -> tuple[list[str], list[str]]:
    old = state.get("components", {}) if isinstance(state.get("components"), dict) else {}
    changed: list[str] = []
    unchanged: list[str] = []
    for component_id in manifest["update_order"]:
        component = manifest["components"][component_id]
        same = old.get(component_id, {}).get("tree_sha256") == component.get("tree_sha256")
        if same and not force:
            unchanged.append(component_id)
        elif component.get("included"):
            changed.append(component_id)
        else:
            raise InstallError(f"Release benötigt Komponente {component_id}, liefert sie aber nicht und der installierte Hash passt nicht.", 46)
    return changed, unchanged


def prepare_slot(root: Path, manifest: dict[str, Any], parts_dir: Path, changed: list[str], active: str | None, target: str, run_id: str) -> Path:
    slots = root / "slots"
    slots.mkdir(parents=True, exist_ok=True)
    stage = slots / f".{target}.stage-{run_id}"
    if stage.exists():
        safe_remove(stage, root)
    if active:
        copy_slot(slots / active, stage)
    else:
        stage.mkdir()
    old_manifest = load_json(root / "slot_manifests" / f"{active}.json") if active else {}
    for component_id in manifest["update_order"]:
        if component_id not in changed:
            continue
        component = manifest["components"][component_id]
        install_path = str(component["install_path"])
        if install_path == ".":
            old_component = old_manifest.get("components", {}).get(component_id, {}) if old_manifest else {}
            paths = {str(item.get("path")) for item in old_component.get("files", [])} | {str(item.get("path")) for item in component.get("files", [])}
            for relative in sorted(paths, reverse=True):
                if relative:
                    safe_remove(stage / relative, stage)
        else:
            safe_remove(stage / install_path, stage)
        for part in sorted((item for item in manifest["parts"] if item["component"] == component_id), key=lambda item: int(item["number"])):
            safe_extract(parts_dir / str(part["file"]), stage, part)
    verify_slot(stage, manifest)
    fsync_tree(stage)
    return stage



class Tee:
    def __init__(self, *targets: Any) -> None:
        self.targets = targets

    def write(self, value: str) -> int:
        for target in self.targets:
            target.write(value)
            target.flush()
        return len(value)

    def flush(self) -> None:
        for target in self.targets:
            target.flush()


def parse_options() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Signierter VideoBatch A/B-Komponenteninstaller")
    parser.add_argument("--bundle-root", type=Path, required=True)
    parser.add_argument("--install-root", type=Path, default=Path(os.environ.get("VIDEOBATCH_INSTALL_DIR", Path.home() / ".local/share/VideoBatchFast")))
    parser.add_argument("--online", action="store_true")
    parser.add_argument("--channel", choices=("stable", "rc"), default="stable")
    parser.add_argument("--index-url")
    parser.add_argument("--index-signature-url")
    parser.add_argument("--no-launch", action="store_true")
    parser.add_argument("--verify-only", action="store_true")
    parser.add_argument("--repair", action="store_true")
    parser.add_argument("--allow-downgrade", action="store_true")
    parser.add_argument("--rollback", action="store_true")
    parser.add_argument("--status", action="store_true")
    parser.add_argument("--feedback-mode", choices=("detailed", "compact"), default="detailed")
    return parser.parse_args()


def _directory_write_probe(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".videobatch-permission-test-", dir=path)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(b"ok")
            handle.flush()
            os.fsync(handle.fileno())
        os.unlink(temporary)
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass


def _directory_writable(path: Path) -> bool:
    try:
        metadata = path.lstat()
    except FileNotFoundError:
        metadata = None
    except OSError:
        return False
    if metadata is not None and stat.S_ISLNK(metadata.st_mode):
        return False
    try:
        _directory_write_probe(path)
    except OSError:
        return False
    return True


def _path_entry(path: Path) -> tuple[bool, bool]:
    """Return existence and symlink state without following an unsafe target."""
    try:
        metadata = path.lstat()
    except FileNotFoundError:
        return False, False
    except OSError:
        # An unreadable entry is treated as an existing conflict. The caller
        # will use the safe fallback instead of following or modifying it.
        return True, False
    return True, stat.S_ISLNK(metadata.st_mode)


def _prepare_user_install_root(requested: Path) -> tuple[Path, str]:
    requested = requested.expanduser().absolute()
    data_home = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share")).expanduser().absolute()
    fallback = data_home / "provoware" / "VideoBatchFast"
    parent = requested.parent
    try:
        parent.mkdir(parents=True, exist_ok=True)
    except OSError:
        parent = fallback.parent
        parent.mkdir(parents=True, exist_ok=True)

    entry_exists, entry_is_symlink = _path_entry(requested)
    if entry_exists:
        if entry_is_symlink or not _directory_writable(requested):
            quarantine = parent / f".{requested.name}.permission-conflict-{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}"
            try:
                if _directory_writable(parent):
                    os.replace(requested, quarantine)
                    _directory_write_probe(requested)
                    return requested.resolve(), f"Alte, nicht beschreibbare Installation wurde nach {quarantine} gesichert."
            except OSError:
                pass
            _directory_write_probe(fallback)
            return fallback.resolve(), f"Standardpfad war nicht beschreibbar. Sicherer Benutzerpfad wird verwendet: {fallback}"

    try:
        _directory_write_probe(requested)
        return requested.resolve(), ""
    except OSError:
        _directory_write_probe(fallback)
        return fallback.resolve(), f"Standardpfad war nicht beschreibbar. Sicherer Benutzerpfad wird verwendet: {fallback}"


def _prepare_optional_user_directory(preferred: Path, fallback: Path) -> Path:
    try:
        _directory_write_probe(preferred)
        return preferred
    except OSError:
        _directory_write_probe(fallback)
        return fallback


def runtime_paths(options: argparse.Namespace) -> dict[str, Any]:
    for name in ("python3", "openssl", "cp"):
        ensure_command(name)
    options.bundle_root = options.bundle_root.expanduser().resolve()
    root, permission_message = _prepare_user_install_root(options.install_root)
    state_dir = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local/state")) / "VideoBatchFast/installer"
    cache_dir = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "VideoBatchFast/installer"
    log_dir = state_dir / "logs"
    for path in (state_dir, cache_dir, log_dir):
        path.mkdir(parents=True, exist_ok=True)
    run_id = f"{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}-{os.getpid()}"
    return {
        "root": root,
        "permission_message": permission_message,
        "state_dir": state_dir,
        "cache_dir": cache_dir,
        "run_id": run_id,
        "log_path": log_dir / f"ab-install-{run_id}.log",
        "state_path": root / "installation_state.json",
        "transaction_path": root / "pending_transaction.json",
    }


def resolve_public_key(bundle_root: Path) -> Path:
    public_key = bundle_root / "VideoBatch_Release_Public_Key.pem"
    if not public_key.is_file() or public_key.is_symlink():
        raise InstallError("Öffentlicher Release-Schlüssel fehlt.", 12)
    return public_key


def installed_public_key(root: Path) -> Path:
    for candidate in (root / "controller/current/VideoBatch_Release_Public_Key.pem", root / "controller/previous/VideoBatch_Release_Public_Key.pem"):
        if candidate.is_file() and not candidate.is_symlink():
            return candidate
    raise InstallError("Kein lokal verankerter öffentlicher Release-Schlüssel vorhanden.", 12)


def load_installed_manifest(root: Path, slot: str) -> dict[str, Any]:
    path = root / "slot_manifests" / f"{slot}.json"
    payload = load_json(path)
    try:
        normalized = validate_slot_snapshot(payload, trusted_key_id=key_id(installed_public_key(root)))
    except ContractError as exc:
        raise InstallError(str(exc), 62) from exc
    if normalized != payload:
        atomic_json(path, normalized, 0o644)
    return normalized


def state_from_slot_manifest(root: Path, slot: str, previous_slot: str | None, old_state: dict[str, Any]) -> dict[str, Any]:
    manifest = load_installed_manifest(root, slot)
    return {
        "schema_version": 2,
        "product": manifest["product"],
        "version": manifest["version"],
        "release_sequence": manifest["release_sequence"],
        "release_id": manifest["release_id"],
        "channel": old_state.get("channel", "local"),
        "channel_index_url": old_state.get("channel_index_url"),
        "channel_generation": old_state.get("channel_generation", 0),
        "channel_index_sha256": old_state.get("channel_index_sha256"),
        "active_slot": slot,
        "previous_slot": previous_slot,
        "pending_boot": False,
        "installed_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "manifest_sha256": sha256(root / "slot_manifests" / f"{slot}.json"),
        "components": {
            component_id: {
                "version": component["version"],
                "tree_sha256": component["tree_sha256"],
                "file_count": component["file_count"],
            }
            for component_id, component in manifest["components"].items()
        },
        "history": old_state.get("history", []) if isinstance(old_state.get("history"), list) else [],
    }


def rollback_confirmed_slot(root: Path, state_path: Path, transaction_path: Path, state: dict[str, Any]) -> int:
    previous = str(state.get("previous_slot", ""))
    active = current_slot(root)
    if previous not in SLOTS or not (root / "slots" / previous / "AppRun").is_file():
        raise InstallError("Kein bestätigter Rückfallslot vorhanden.", 60)
    manifest = load_installed_manifest(root, previous)
    verify_slot(root / "slots" / previous, manifest)
    from ab_launcher import atomic_switch  # type: ignore
    atomic_switch(root, previous)
    restored = state_from_slot_manifest(root, previous, active, state)
    history = restored.setdefault("history", [])
    history.append({"utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "event": "manual_rollback", "restored_slot": previous, "previous_active_slot": active})
    del history[:-20]
    atomic_json(state_path, restored)
    transaction_path.unlink(missing_ok=True)
    print(f"ROLLBACK_OK slot={previous} version={restored['version']}")
    return 0


def handle_control_request(options: argparse.Namespace, paths: dict[str, Any], state: dict[str, Any]) -> int | None:
    root = paths["root"]
    if options.status:
        print(json.dumps({
            "install_root": str(root),
            "current_slot": current_slot(root),
            "state": state,
            "pending": load_json(paths["transaction_path"]),
        }, ensure_ascii=False, indent=2))
        return 0
    if options.rollback:
        return rollback_confirmed_slot(root, paths["state_path"], paths["transaction_path"], state)
    if paths["transaction_path"].exists():
        raise InstallError("Ein vorheriges Update wartet noch auf die automatische Boot-Bestätigung. VideoBatch einmal normal starten.", 61)
    return None


def validate_release_progression(manifest: dict[str, Any], state: dict[str, Any], allow_downgrade: bool, manifest_sha256: str) -> None:
    installed_sequence = int(state.get("release_sequence", 0) or 0)
    incoming_sequence = int(manifest["release_sequence"])
    if incoming_sequence < installed_sequence and not allow_downgrade:
        raise InstallError("Downgrade oder Replay wurde durch die monotone Releasefolge blockiert.", 21)
    installed_version = state.get("version")
    if installed_version and version_tuple(str(manifest["version"])) < version_tuple(str(installed_version)) and not allow_downgrade:
        raise InstallError("Versionsdowngrade ist blockiert.", 21)
    if installed_sequence == incoming_sequence and installed_version == manifest.get("version"):
        old_release_id = str(state.get("release_id", ""))
        if old_release_id and old_release_id != str(manifest.get("release_id", "")):
            raise InstallError("Eine bereits verwendete Version/Sequenz darf nicht mit anderem Inhalt neu veröffentlicht werden.", 22)
        old_manifest_hash = str(state.get("manifest_sha256", ""))
        if old_manifest_hash and old_manifest_hash != manifest_sha256 and old_release_id == str(manifest.get("release_id", "")):
            raise InstallError("Release-Manifest derselben Identität wurde nachträglich verändert.", 22)
    incoming_generation = int(manifest.get("_channel_generation", 0) or 0)
    installed_generation = int(state.get("channel_generation", 0) or 0)
    if incoming_generation and incoming_generation < installed_generation and not allow_downgrade:
        raise InstallError("Älterer Channel-Index wurde als Replay blockiert.", 22)


def active_slot_from_state(root: Path, state: dict[str, Any]) -> str | None:
    active = current_slot(root)
    if active is None and str(state.get("active_slot", "")) in SLOTS:
        return str(state["active_slot"])
    return active


def launcher_path(options: argparse.Namespace, root: Path) -> Path:
    candidate = options.bundle_root / "ab_launcher.py"
    return candidate if candidate.is_file() else root / "controller/current/ab_launcher.py"


def handle_verify_or_current(
    options: argparse.Namespace,
    root: Path,
    state: dict[str, Any],
    manifest: dict[str, Any],
    active: str | None,
    changed: list[str],
) -> int | None:
    if options.verify_only:
        if active not in SLOTS:
            raise InstallError("Keine aktive A/B-Installation vorhanden.", 62)
        installed_manifest = load_json(root / "slot_manifests" / f"{active}.json") or manifest
        verify_slot(root / "slots" / active, installed_manifest)
        print(f"VERIFY_OK slot={active} version={state.get('version', 'unbekannt')}")
        return 0
    if changed or active not in SLOTS:
        return None
    installed_manifest = load_json(root / "slot_manifests" / f"{active}.json") or manifest
    verify_slot(root / "slots" / active, installed_manifest)
    index_url = options.index_url if options.online else state.get("channel_index_url")
    channel = options.channel if options.online else str(state.get("channel", "stable"))
    install_user_wrappers(root, index_url, channel)
    print("BEREITS_AKTUELL")
    if options.no_launch:
        return 0
    return subprocess.run([sys.executable, str(launcher_path(options, root)), "--install-root", str(root)], check=False).returncode


def target_state_payload(
    manifest: dict[str, Any],
    source_root: Path,
    state: dict[str, Any],
    options: argparse.Namespace,
    target: str,
    active: str | None,
) -> dict[str, Any]:
    return {
        "schema_version": 2,
        "product": manifest["product"],
        "version": manifest["version"],
        "release_sequence": manifest["release_sequence"],
        "release_id": manifest["release_id"],
        "channel_generation": int(manifest.get("_channel_generation", state.get("channel_generation", 0)) or 0),
        "channel_index_sha256": manifest.get("_channel_index_sha256", state.get("channel_index_sha256")),
        "channel": options.channel if options.online else str(state.get("channel", "local")),
        "channel_index_url": options.index_url if options.online else state.get("channel_index_url"),
        "active_slot": target,
        "previous_slot": active,
        "pending_boot": True,
        "installed_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "manifest_sha256": sha256(source_root / "INSTALLER_MANIFEST.json"),
        "components": {
            component_id: {
                "version": component["version"],
                "tree_sha256": component["tree_sha256"],
                "file_count": component["file_count"],
            }
            for component_id, component in manifest["components"].items()
        },
        "history": state.get("history", []) if isinstance(state.get("history"), list) else [],
    }


def publish_inactive_slot(
    root: Path,
    stage: Path,
    target: str,
    manifest: dict[str, Any],
    run_id: str,
) -> Path:
    slots = root / "slots"
    final_target = slots / target
    backup_target = slots / f".{target}.previous-{run_id}"
    if final_target.exists():
        os.replace(final_target, backup_target)
    os.replace(stage, final_target)
    fsync_dir(slots)
    slot_manifests = root / "slot_manifests"
    slot_manifests.mkdir(parents=True, exist_ok=True)
    snapshot = {key: value for key, value in manifest.items() if not str(key).startswith("_")}
    atomic_json(slot_manifests / f"{target}.json", snapshot, 0o644)
    return final_target


def switch_with_transaction(
    root: Path,
    transaction_path: Path,
    active: str | None,
    target: str,
    target_state: dict[str, Any],
) -> None:
    transaction = {
        "schema_version": 1,
        "phase": "prepared",
        "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "previous_slot": active,
        "target_slot": target,
        "target_state": target_state,
    }
    atomic_json(transaction_path, transaction)
    from ab_launcher import atomic_switch  # type: ignore
    atomic_switch(root, target)
    transaction["phase"] = "switched"
    atomic_json(transaction_path, transaction)


def confirm_first_boot(
    options: argparse.Namespace,
    root: Path,
    state_path: Path,
    manifest: dict[str, Any],
    target: str,
    active: str | None,
) -> None:
    if options.no_launch:
        print("⚠ Boot-Bestätigung wird beim nächsten normalen Start automatisch abgeschlossen.")
        return
    result = subprocess.run([sys.executable, str(launcher_path(options, root)), "--install-root", str(root)], check=False).returncode
    confirmed = load_json(state_path)
    success = result == 0 and confirmed.get("active_slot") == target and confirmed.get("version") == manifest["version"]
    if success:
        print("✓ Oberfläche bereit; neuer Slot wurde dauerhaft bestätigt.")
        return
    if confirmed.get("active_slot") == active and active in SLOTS:
        raise InstallError("Der neue Slot hat den ersten Start nicht bestanden. Der bestätigte vorherige Slot wurde automatisch wiederhergestellt.", 64)
    raise InstallError(f"Neuer Slot und Rückfallslot konnten nicht erfolgreich gestartet werden (Code {result}).", 63)


def prune_slot_backups(root: Path) -> None:
    slots = root / "slots"
    backups = sorted(slots.glob(".*.previous-*"), key=lambda item: item.stat().st_mtime, reverse=True)
    for path in backups[2:]:
        safe_remove(path, root)


def verify_installed_without_source(root: Path, state: dict[str, Any]) -> int:
    active = active_slot_from_state(root, state)
    if active not in SLOTS:
        raise InstallError("Keine aktive A/B-Installation vorhanden.", 62)
    manifest_path = root / "slot_manifests" / f"{active}.json"
    manifest = load_installed_manifest(root, active)
    verify_slot(root / "slots" / active, manifest)
    if state.get("release_id") and state.get("release_id") != manifest.get("release_id"):
        raise InstallError("Installationsstatus und aktiver Slot besitzen unterschiedliche Release-Identitäten.", 62)
    if state.get("release_id") != manifest.get("release_id") or state.get("version") != manifest.get("version"):
        repaired = state_from_slot_manifest(root, active, state.get("previous_slot"), state)
        history = repaired.setdefault("history", [])
        history.append({"utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "event": "installation_state_rebuilt_from_slot_manifest", "slot": active})
        del history[:-20]
        atomic_json(root / "installation_state.json", repaired)
    print(f"VERIFY_OK slot={active} version={manifest['version']} release_id={manifest['release_id']}")
    return 0


def corrupt_components(root: Path, active: str | None, manifest: dict[str, Any]) -> list[str]:
    if active not in SLOTS:
        return list(manifest["update_order"])
    broken: list[str] = []
    slot = root / "slots" / active
    for component_id in manifest["update_order"]:
        try:
            verify_component(slot, manifest["components"][component_id])
        except InstallError:
            broken.append(component_id)
    return broken




ERROR_TITLES = {
    11: "Eine andere Installation läuft bereits",
    12: "Öffentlicher Prüfschlüssel fehlt",
    43: "Integritätsprüfung des Zielslots fehlgeschlagen",
    44: "Laufzeit- oder Medien-Selbsttest fehlgeschlagen",
    46: "Beschädigte Komponente kann nicht repariert werden",
    47: "Freier Speicher reicht nicht aus",
}

def _wrap(message: str, prefix: str, width: int = 72) -> list[str]:
    usable = max(28, width - len(prefix))
    lines = textwrap.wrap(str(message), width=usable) or [str(message)]
    return [prefix + lines[0], *(" " * len(prefix) + line for line in lines[1:])]

def feedback_step(options: argparse.Namespace, number: int, total: int, title: str) -> None:
    prefix = "  " if options.feedback_mode == "compact" else ""
    print(f"{prefix}[{number}/{total}] {title}")

def feedback_ok(options: argparse.Namespace, message: str) -> None:
    prefix = "      ✓ " if options.feedback_mode == "compact" else "✓ "
    for line in _wrap(message, prefix): print(line)

def feedback_info(options: argparse.Namespace, label: str, values: list[str]) -> None:
    if options.feedback_mode == "compact":
        print(f"      {label}:")
        for value in values or ["keine"]: print(f"        • {value}")
    else:
        print(f"  {label}: " + (", ".join(values) if values else "keine"))

def print_compact_error(exc: InstallError, log_path: Path) -> None:
    title = ERROR_TITLES.get(exc.code, "Installation konnte nicht abgeschlossen werden")
    first = str(exc).splitlines()[0].strip() or title
    print("", file=sys.stderr)
    print("  ┌─ INSTALLATION GESTOPPT " + "─" * 38, file=sys.stderr)
    print(f"  │ {title}", file=sys.stderr)
    print("  │", file=sys.stderr)
    for line in _wrap(first, "  │ ", width=70): print(line, file=sys.stderr)
    print("  │", file=sys.stderr)
    print("  │ Schutz: Der bestätigte aktive Slot blieb unverändert.", file=sys.stderr)
    print(f"  │ Details: {log_path}", file=sys.stderr)
    print("  └" + "─" * 66, file=sys.stderr)


def perform_install(options: argparse.Namespace, paths: dict[str, Any]) -> int:
    root = paths["root"]
    state_path = paths["state_path"]
    transaction_path = paths["transaction_path"]
    state = load_json(state_path)
    control_result = handle_control_request(options, paths, state)
    if control_result is not None:
        return control_result
    if options.verify_only:
        return verify_installed_without_source(root, state)

    public_key = resolve_public_key(options.bundle_root)
    if options.feedback_mode == "detailed": print()
    if paths.get("permission_message"):
        feedback_ok(options, str(paths["permission_message"]))
    feedback_step(options, 1, 9, "Signierten Releasevertrag laden")
    manifest, source_root, manifest_url = load_source(options, paths["cache_dir"] / paths["run_id"], public_key)
    channel_label = options.channel if options.online else "lokal"
    feedback_ok(options, f"Version {manifest['version']} · Sequenz {manifest['release_sequence']} · Kanal {channel_label}")
    validate_release_progression(manifest, state, options.allow_downgrade, sha256(source_root / "INSTALLER_MANIFEST.json"))

    active = active_slot_from_state(root, state)
    changed, unchanged = plan_changes(manifest, state, options.repair)
    broken = corrupt_components(root, active, manifest)
    for component_id in broken:
        if component_id not in changed:
            if not manifest["components"][component_id].get("included"):
                raise InstallError(f"Beschädigte Komponente {component_id} kann mit diesem Teilrelease nicht repariert werden.", 46)
            changed.append(component_id)
            if component_id in unchanged:
                unchanged.remove(component_id)
    changed.sort(key=manifest["update_order"].index)
    feedback_step(options, 2, 9, "Komponentenplan berechnen")
    feedback_info(options, "Ersetzen", changed)
    feedback_info(options, "Unverändert", unchanged)
    preflight_disk_space(root, paths["cache_dir"], manifest, changed)
    feedback_ok(options, "Speicherplatzreserve ist ausreichend")
    early_result = handle_verify_or_current(options, root, state, manifest, active, changed)
    if early_result is not None:
        return early_result

    feedback_step(options, 3, 9, "Signierte Teilpakete bereitstellen")
    parts_dir = download_required_parts(manifest, source_root, manifest_url, set(changed), public_key)
    feedback_ok(options, "Pakete sind vollständig, signiert und hashgebunden")

    target = "A" if active != "A" else "B"
    feedback_step(options, 4, 9, f"Inaktiven Slot {target} vorbereiten")
    stage = prepare_slot(root, manifest, parts_dir, changed, active, target, paths["run_id"])
    feedback_ok(options, "Inaktiver Slot wurde vollständig aufgebaut")
    feedback_step(options, 5, 9, "Inaktiven Slot vollständig prüfen")
    verify_slot(stage, manifest)
    feedback_ok(options, "Manifest, Python und Medien-Selbsttest sind grün")

    final_target = publish_inactive_slot(root, stage, target, manifest, paths["run_id"])
    target_state = target_state_payload(manifest, source_root, state, options, target, active)
    feedback_step(options, 6, 9, "Aktiven Slot atomar umschalten")
    switch_with_transaction(root, transaction_path, active, target, target_state)
    feedback_ok(options, f"Aktiver Verweis zeigt auf Slot {target}")

    feedback_step(options, 7, 9, "Starter und Benutzerzugänge vorbereiten")
    install_controller(final_target / "usr" / "app", public_key, root, str(manifest["version"]))
    index_url = options.index_url if options.online else state.get("channel_index_url")
    channel = options.channel if options.online else str(state.get("channel", "stable"))
    install_user_wrappers(root, index_url, channel)
    feedback_ok(options, "Starter und Updatecontroller sind bereit")

    feedback_step(options, 8, 9, "Ersten echten Start überwachen")
    confirm_first_boot(options, root, state_path, manifest, target, active)
    feedback_step(options, 9, 9, "Bestätigten Rückfallslot erhalten")
    prune_slot_backups(root)
    feedback_ok(options, f"Installation aktiv: {manifest['version']} · Slot {current_slot(root)}")
    print(f"INSTALLATION_OK version={manifest['version']} active_slot={current_slot(root)} log={paths['log_path']}")
    return 0


def run_locked(options: argparse.Namespace, paths: dict[str, Any]) -> int:
    lock_path = paths["state_dir"] / "ab-install.lock"
    with lock_path.open("a+") as lock:
        try:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise InstallError("Eine andere VideoBatch-Installation läuft bereits.", 11) from exc
        return perform_install(options, paths)


def main() -> int:
    options = parse_options()
    paths = runtime_paths(options)
    original_stdout, original_stderr = sys.stdout, sys.stderr
    log_handle = paths["log_path"].open("a", encoding="utf-8")
    sys.stdout = Tee(original_stdout, log_handle)  # type: ignore[assignment]
    sys.stderr = Tee(original_stderr, log_handle)  # type: ignore[assignment]
    try:
        return run_locked(options, paths)
    except InstallError as exc:
        log_handle.write(f"INSTALLATION_BLOCKIERT[{exc.code}]: {exc}\n")
        log_handle.flush()
        if options.feedback_mode == "compact": print_compact_error(exc, paths["log_path"])
        else:
            print(f"INSTALLATION_BLOCKIERT[{exc.code}]: {exc}", file=sys.stderr)
            print(f"Protokoll: {paths['log_path']}", file=sys.stderr)
        return exc.code
    except Exception as exc:
        log_handle.write(f"INSTALLATION_BLOCKIERT[99]: {type(exc).__name__}: {exc}\n")
        log_handle.flush()
        if options.feedback_mode == "compact":
            print_compact_error(InstallError("Unerwarteter interner Fehler. Technische Details wurden protokolliert.", 99), paths["log_path"])
        else:
            print(f"INSTALLATION_BLOCKIERT[99]: {type(exc).__name__}: {exc}", file=sys.stderr)
            print(f"Protokoll: {paths['log_path']}", file=sys.stderr)
        return 99
    finally:
        sys.stdout, sys.stderr = original_stdout, original_stderr
        log_handle.close()


if __name__ == "__main__":
    raise SystemExit(main())
