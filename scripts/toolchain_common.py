#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
import platform
import re
import shutil
import sys
import tempfile
import zipfile
from email.parser import Parser
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "TOOLCHAIN_CONTRACT.json"
MANIFEST_NAME = "TOOLCHAIN_WHEELHOUSE_MANIFEST.json"
RESOLVED_LOCK_NAME = "requirements-toolchain-resolved.lock"
RUNTIME_RESOLVED_LOCK_NAME = "requirements-runtime-resolved.lock"


def canonical(value: str) -> str:
    return re.sub(r"[-_.]+", "-", value).lower()


def current_build(root: Path = ROOT) -> str:
    data = json.loads((root / "VERSION.json").read_text(encoding="utf-8"))
    return str(data["build"])


def read_exact_lock(path: Path) -> dict[str, str]:
    found: dict[str, str] = {}
    for line_number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        requirement = line.split(";", 1)[0].strip()
        match = re.fullmatch(r"([A-Za-z0-9_.-]+)==([^\s]+)", requirement)
        if not match:
            raise ValueError(f"Nicht exakt gesperrter Eintrag in {path.name}:{line_number}: {raw}")
        name = canonical(match.group(1))
        if name in found:
            raise ValueError(f"Doppelter Lockfile-Eintrag: {name}")
        found[name] = match.group(2)
    if not found:
        raise ValueError(f"Lockfile enthält keine Pakete: {path.name}")
    return found


def load_contract(root: Path = ROOT) -> dict[str, Any]:
    data = json.loads((root / "TOOLCHAIN_CONTRACT.json").read_text(encoding="utf-8"))
    if data.get("schema_version") != 1:
        raise ValueError("Unbekannte Toolchain-Vertragsversion.")
    build = current_build(root)
    if data.get("release_target") != build or build not in str(data.get("contract_id", "")):
        raise ValueError("Toolchain-Vertrag gehört nicht zum aktuellen Build.")
    policy = data.get("policy", {})
    required = (
        "fail_closed", "stable_requires_all_tools", "exact_versions_required",
        "offline_installation_required", "wheel_hash_manifest_required",
        "sdists_forbidden", "online_download_requires_explicit_consent",
        "atomic_replacement_required", "automatic_repair_on_launcher_start",
    )
    if not all(policy.get(key) is True for key in required):
        raise ValueError("Toolchain-Sicherheitsrichtlinie ist unvollständig.")
    expected_runtime = {canonical(k): str(v) for k, v in data["packages"]["runtime"].items()}
    expected_quality = {canonical(k): str(v) for k, v in data["packages"]["quality"].items()}
    expected_all = {**expected_runtime, **expected_quality}
    paths = data["paths"]
    runtime_lock = read_exact_lock(root / paths["runtime_lock"])
    quality_lock = read_exact_lock(root / paths["quality_lock"])
    unified_lock = read_exact_lock(root / paths["unified_lock"])
    if runtime_lock != expected_runtime:
        raise ValueError(f"Runtime-Lock weicht vom Vertrag ab: {runtime_lock}")
    if quality_lock != expected_quality:
        raise ValueError(f"Qualitäts-Lock weicht vom Vertrag ab: {quality_lock}")
    if unified_lock != expected_all:
        raise ValueError(f"Einheits-Lock weicht vom Vertrag ab: {unified_lock}")
    return data


def expected_packages(contract: dict[str, Any], scope: str = "all") -> dict[str, str]:
    runtime = {canonical(k): str(v) for k, v in contract["packages"]["runtime"].items()}
    quality = {canonical(k): str(v) for k, v in contract["packages"]["quality"].items()}
    if scope == "runtime":
        return runtime
    if scope == "quality":
        return quality
    if scope != "all":
        raise ValueError(f"Unbekannter Prüfbereich: {scope}")
    return {**runtime, **quality}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def wheel_metadata(path: Path) -> tuple[str, str]:
    with zipfile.ZipFile(path) as archive:
        metadata_names = [name for name in archive.namelist() if name.endswith(".dist-info/METADATA")]
        if len(metadata_names) != 1:
            raise ValueError(f"Wheel-Metadaten sind nicht eindeutig: {path.name}")
        text = archive.read(metadata_names[0]).decode("utf-8", errors="strict")
    name = version = ""
    for line in text.splitlines():
        if line.startswith("Name: "):
            name = canonical(line[6:].strip())
        elif line.startswith("Version: "):
            version = line[9:].strip()
    if not name or not version:
        raise ValueError(f"Wheel-Identität fehlt: {path.name}")
    return name, version


def runtime_identity() -> dict[str, str]:
    return {
        "python": f"{sys.version_info.major}.{sys.version_info.minor}",
        "implementation": platform.python_implementation(),
        "platform": platform.system().lower(),
        "machine": platform.machine().lower(),
    }


def toolchain_cache_key(root: Path = ROOT) -> str:
    digest = hashlib.sha256()
    digest.update((root / "requirements-toolchain.lock").read_bytes())
    digest.update(json.dumps(runtime_identity(), sort_keys=True).encode("utf-8"))
    return digest.hexdigest()[:20]


def build_manifest(wheelhouse: Path, *, root: Path = ROOT) -> dict[str, Any]:
    wheels: list[dict[str, Any]] = []
    for path in sorted(wheelhouse.glob("*.whl")):
        name, version = wheel_metadata(path)
        wheels.append({
            "filename": path.name,
            "name": name,
            "version": version,
            "size": path.stat().st_size,
            "sha256": sha256_file(path),
        })
    return {
        "schema_version": 1,
        "contract_version": f"unified-toolchain-{current_build(root)}-v1",
        "release_target": current_build(root),
        **runtime_identity(),
        "wheel_count": len(wheels),
        "wheels": wheels,
    }


def wheel_requirements(path: Path) -> set[str]:
    """Return canonical direct dependency names declared by a wheel.

    The bootstrap deliberately avoids third-party requirement parsers.  For the
    wheelhouse closure we only need the normalized distribution name; version
    constraints, extras and markers remain pip's responsibility.
    """
    with zipfile.ZipFile(path) as archive:
        metadata_names = [name for name in archive.namelist() if name.endswith(".dist-info/METADATA")]
        if len(metadata_names) != 1:
            raise ValueError(f"Wheel-Metadaten sind nicht eindeutig: {path.name}")
        message = Parser().parsestr(archive.read(metadata_names[0]).decode("utf-8", errors="strict"))
    dependencies: set[str] = set()
    for raw in message.get_all("Requires-Dist", []):
        # Name is the first PEP-508 token before extras, whitespace, comparison
        # operators or a marker.  This is sufficient for matching wheel names.
        match = re.match(r"\s*([A-Za-z0-9_.-]+)", raw)
        if match:
            dependencies.add(canonical(match.group(1)))
    return dependencies


def dependency_closure(wheelhouse: Path, manifest: dict[str, Any], direct_names: set[str]) -> set[str]:
    by_name = {canonical(str(item["name"])): item for item in manifest.get("wheels", [])}
    missing = sorted(name for name in direct_names if name not in by_name)
    if missing:
        raise ValueError("Direkte Pakete fehlen im Wheelhouse: " + ", ".join(missing))
    selected = set(direct_names)
    pending = list(direct_names)
    while pending:
        name = pending.pop()
        item = by_name[name]
        path = wheelhouse / str(item["filename"])
        for dependency in wheel_requirements(path):
            if dependency in by_name and dependency not in selected:
                selected.add(dependency)
                pending.append(dependency)
    return selected


def resolved_lock_text(manifest: dict[str, Any], include_names: set[str] | None = None) -> str:
    lines = [
        "# Automatisch erzeugt – nicht manuell bearbeiten.",
        "# Vollständig an das hashgeprüfte Einheits-Wheelhouse gebunden.",
    ]
    items = manifest.get("wheels", [])
    if include_names is not None:
        items = [item for item in items if canonical(str(item["name"])) in include_names]
    for item in sorted(items, key=lambda value: (str(value["name"]), str(value["version"]))):
        lines.append(f"{item['name']}=={item['version']} --hash=sha256:{item['sha256']}")
    return "\n".join(lines) + "\n"

def _fsync_directory(path: Path) -> None:
    try:
        fd = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    except OSError:
        return
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def atomic_write_text(path: Path, content: str, *, mode: int = 0o600) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, raw = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temporary = Path(raw)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, mode)
        os.replace(temporary, path)
        _fsync_directory(path.parent)
        return path
    finally:
        if temporary.exists():
            temporary.unlink(missing_ok=True)


def write_manifest(wheelhouse: Path, manifest: dict[str, Any]) -> Path:
    return atomic_write_text(
        wheelhouse / MANIFEST_NAME,
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
    )


def write_resolved_lock(wheelhouse: Path, manifest: dict[str, Any], contract: dict[str, Any] | None = None) -> Path:
    result = atomic_write_text(wheelhouse / RESOLVED_LOCK_NAME, resolved_lock_text(manifest))
    if contract is not None:
        runtime_names = set(expected_packages(contract, "runtime"))
        closure = dependency_closure(wheelhouse, manifest, runtime_names)
        atomic_write_text(
            wheelhouse / RUNTIME_RESOLVED_LOCK_NAME,
            resolved_lock_text(manifest, closure),
        )
    return result


def _load_wheelhouse_manifest(wheelhouse: Path) -> tuple[dict[str, Any] | None, list[str]]:
    if wheelhouse.is_symlink() or not wheelhouse.is_dir():
        return None, ["Wheelhouse fehlt, ist kein Ordner oder ist ein Link."]
    manifest_path = wheelhouse / MANIFEST_NAME
    if not manifest_path.is_file() or manifest_path.is_symlink():
        return None, [f"{MANIFEST_NAME} fehlt oder ist ein Link."]
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return None, [f"Toolchain-Manifest ist unlesbar: {exc}"]
    return manifest, []


def _verify_manifest_header(manifest: dict[str, Any], root: Path) -> list[str]:
    errors: list[str] = []
    expected_header = {
        "contract_version": f"unified-toolchain-{current_build(root)}-v1",
        "release_target": current_build(root),
        **runtime_identity(),
    }
    for key, expected in expected_header.items():
        if str(manifest.get(key, "")).lower() != str(expected).lower():
            errors.append(f"{key}: erwartet {expected}, Manifest {manifest.get(key)}")
    return errors


def _verify_wheel_item(
    wheelhouse: Path,
    item: object,
    identities: set[tuple[str, str]],
    declared: set[str],
) -> list[str]:
    if not isinstance(item, dict):
        return ["Ungültiger Wheel-Eintrag."]
    filename = str(item.get("filename", ""))
    if not filename or Path(filename).name != filename:
        return ["Ungültiger Wheel-Dateiname im Manifest."]
    declared.add(filename)
    path = wheelhouse / filename
    if not path.is_file() or path.is_symlink():
        return [f"Wheel fehlt oder ist ein Link: {filename}"]
    try:
        if path.stat().st_size != int(item.get("size", -1)):
            return [f"Wheelgröße stimmt nicht: {filename}"]
        if sha256_file(path) != str(item.get("sha256", "")):
            return [f"Wheel-Prüfsumme stimmt nicht: {filename}"]
        identity = wheel_metadata(path)
    except (OSError, UnicodeError, ValueError, zipfile.BadZipFile) as exc:
        return [str(exc)]
    errors: list[str] = []
    expected_identity = (canonical(str(item.get("name", ""))), str(item.get("version", "")))
    if identity != expected_identity:
        errors.append(f"Wheel-Identität stimmt nicht: {filename}")
    if identity in identities:
        errors.append(f"Doppelte Distribution: {identity[0]}=={identity[1]}")
    identities.add(identity)
    return errors


def _verify_wheel_items(
    wheelhouse: Path,
    manifest: dict[str, Any],
) -> tuple[set[tuple[str, str]], set[str], list[str]]:
    items = manifest.get("wheels", [])
    if not isinstance(items, list) or manifest.get("wheel_count") != len(items):
        return set(), set(), ["Wheelanzahl im Manifest ist inkonsistent."]
    identities: set[tuple[str, str]] = set()
    declared: set[str] = set()
    errors: list[str] = []
    for item in items:
        errors.extend(_verify_wheel_item(wheelhouse, item, identities, declared))
    extras = {path.name for path in wheelhouse.glob("*.whl")} - declared
    if extras:
        errors.append(f"Nicht manifestiertes Wheel: {sorted(extras)[0]}")
    return identities, declared, errors


def _verify_text_lock(path: Path, expected: str, title: str) -> list[str]:
    if not path.is_file() or path.is_symlink():
        return [f"{path.name} fehlt oder ist ein Link."]
    try:
        actual = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        return [f"{title} ist unlesbar: {exc}"]
    return [] if actual == expected else [f"{title} stimmt nicht mit dem Manifest überein."]


def _verify_lock_files(
    wheelhouse: Path,
    manifest: dict[str, Any],
    contract: dict[str, Any],
) -> list[str]:
    errors = _verify_text_lock(
        wheelhouse / RESOLVED_LOCK_NAME,
        resolved_lock_text(manifest),
        "Hash-Lockfile",
    )
    try:
        closure = dependency_closure(wheelhouse, manifest, set(expected_packages(contract, "runtime")))
        runtime_text = resolved_lock_text(manifest, closure)
    except (OSError, UnicodeError, ValueError, zipfile.BadZipFile) as exc:
        return errors + [f"Runtime-Hash-Lockfile ist unlesbar: {exc}"]
    errors.extend(_verify_text_lock(
        wheelhouse / RUNTIME_RESOLVED_LOCK_NAME,
        runtime_text,
        "Runtime-Hash-Lockfile",
    ))
    return errors


def verify_wheelhouse(
    wheelhouse: Path,
    contract: dict[str, Any],
    *,
    root: Path = ROOT,
    scope: str = "all",
) -> list[str]:
    manifest, errors = _load_wheelhouse_manifest(wheelhouse)
    if manifest is None:
        return errors
    errors.extend(_verify_manifest_header(manifest, root))
    identities, _declared, item_errors = _verify_wheel_items(wheelhouse, manifest)
    errors.extend(item_errors)
    package_scope = "runtime" if scope == "runtime" else "all"
    for name, version in expected_packages(contract, package_scope).items():
        if (name, version) not in identities:
            errors.append(f"Direktes Toolchain-Paket fehlt: {name}=={version}")
    errors.extend(_verify_lock_files(wheelhouse, manifest, contract))
    return errors


def rebuild_wheelhouse_metadata(wheelhouse: Path, contract: dict[str, Any], *, root: Path = ROOT) -> dict[str, Any]:
    if wheelhouse.is_symlink() or not wheelhouse.is_dir():
        raise ValueError("Wheelhouse ist kein sicherer Ordner.")
    if not any(wheelhouse.glob("*.whl")):
        raise ValueError("Wheelhouse enthält keine Wheel-Dateien.")
    manifest = build_manifest(wheelhouse, root=root)
    write_manifest(wheelhouse, manifest)
    write_resolved_lock(wheelhouse, manifest, contract)
    errors = verify_wheelhouse(wheelhouse, contract, root=root)
    if errors:
        raise ValueError(" | ".join(errors))
    return manifest


def _reject_dangerous_path(path: Path, *, allowed_parent: Path) -> Path:
    resolved = path.resolve(strict=False)
    parent = allowed_parent.resolve(strict=True)
    forbidden = {Path("/").resolve(), Path.home().resolve(), ROOT.resolve(), Path.cwd().resolve()}
    if resolved in forbidden or resolved.parent != parent:
        raise ValueError(f"Unsicherer temporärer Pfad blockiert: {resolved}")
    return resolved


def safe_remove_tree(path: Path | None, *, allowed_parent: Path) -> None:
    if path is None or not path.exists():
        return
    safe = _reject_dangerous_path(path, allowed_parent=allowed_parent)
    shutil.rmtree(safe)


def publish_directory(staging: Path, output: Path) -> None:
    output_parent = output.parent.resolve(strict=True)
    staged = _reject_dangerous_path(staging, allowed_parent=output_parent)
    destination = output.resolve(strict=False)
    if output.is_symlink() or destination.parent != output_parent or destination in {ROOT.resolve(), Path.home().resolve()}:
        raise ValueError(f"Unsicheres Wheelhouse-Ziel blockiert: {destination}")
    backup = output.with_name(f".{output.name}.previous")
    if backup.exists():
        safe_remove_tree(backup, allowed_parent=output.parent)
    if output.exists():
        os.replace(output, backup)
    try:
        os.replace(staged, output)
        _fsync_directory(output.parent)
    except BaseException:
        if backup.exists() and not output.exists():
            os.replace(backup, output)
        raise
    if backup.exists():
        safe_remove_tree(backup, allowed_parent=output.parent)
