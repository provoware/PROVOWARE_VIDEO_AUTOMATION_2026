#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import re
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path, PurePosixPath
from typing import Any

PRODUCT = "VideoBatch Fast"
MANIFEST_SCHEMA = 2
INDEX_SCHEMA = 1
SLOTS = ("A", "B")
COMPONENTS = ("bootstrap", "runtime", "media", "application", "desktop")
MAX_PART_BYTES_HARD = 30 * 1024 * 1024
MAX_PART_COUNT = 256
MAX_COMPONENT_FILES = 100_000
MAX_TOTAL_FILES = 250_000
MAX_UNPACKED_BYTES = 8 * 1024 * 1024 * 1024
CHANNEL_CLOCK_SKEW = timedelta(hours=24)
SHA256_RE = re.compile(r"[0-9a-f]{64}")
VERSION_RE = re.compile(r"(\d+)\.(\d+)\.(\d+)(?:-rc(\d+))?")


class ContractError(ValueError):
    pass


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def key_id(public_key: Path) -> str:
    completed = subprocess.run(
        ["openssl", "pkey", "-pubin", "-in", str(public_key), "-outform", "DER"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode or len(completed.stdout) < 32:
        raise ContractError("Öffentlicher Schlüssel ist ungültig.")
    # Einheitliche Ed25519-Key-ID: SHA-256 über die 32 rohen öffentlichen Schlüsselbytes.
    return hashlib.sha256(completed.stdout[-32:]).hexdigest()[:24]


def safe_relative(value: str, *, field: str = "Pfad") -> str:
    pure = PurePosixPath(value)
    if not value or value.startswith("/") or ".." in pure.parts or "." in pure.parts or "" in pure.parts:
        raise ContractError(f"{field} ist unsicher: {value!r}")
    normalized = pure.as_posix()
    if normalized != value:
        raise ContractError(f"{field} ist nicht kanonisch: {value!r}")
    return normalized


def safe_optional_relative(value: str, *, field: str) -> str:
    if value == ".":
        return value
    return safe_relative(value, field=field)


def parse_utc(value: str, *, field: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise ContractError(f"{field} ist kein gültiger UTC-Zeitpunkt.") from exc
    if parsed.tzinfo is None:
        raise ContractError(f"{field} benötigt eine Zeitzone.")
    return parsed.astimezone(timezone.utc)


def version_tuple(value: str) -> tuple[int, int, int, int]:
    match = VERSION_RE.fullmatch(value)
    if not match:
        raise ContractError(f"Versionsnummer ist ungültig: {value!r}")
    major, minor, patch, rc = match.groups()
    return int(major), int(minor), int(patch), int(rc) if rc is not None else 999_999


def _sha(value: Any, field: str) -> str:
    text = str(value)
    if not SHA256_RE.fullmatch(text):
        raise ContractError(f"{field} enthält keinen gültigen SHA-256-Wert.")
    return text


def _validate_component_records(components: dict[str, Any]) -> tuple[int, int]:
    all_paths: set[str] = set()
    total_files = 0
    total_unpacked = 0
    for component_id in COMPONENTS:
        component = components[component_id]
        if not isinstance(component, dict):
            raise ContractError(f"Komponente {component_id} ist ungültig.")
        safe_optional_relative(str(component.get("install_path", "")), field=f"install_path:{component_id}")
        records = component.get("files")
        if not isinstance(records, list) or len(records) > MAX_COMPONENT_FILES:
            raise ContractError(f"Dateiliste von {component_id} ist ungültig oder zu groß.")
        if int(component.get("file_count", -1)) != len(records):
            raise ContractError(f"Dateizahl von {component_id} widerspricht der Dateiliste.")
        seen: set[str] = set()
        digest = hashlib.sha256()
        for record in sorted(records, key=lambda item: str(item.get("path", ""))):
            if not isinstance(record, dict):
                raise ContractError(f"Dateieintrag von {component_id} ist ungültig.")
            path = safe_relative(str(record.get("path", "")), field=f"Dateipfad:{component_id}")
            if path in seen or path in all_paths:
                raise ContractError(f"Dateipfad ist doppelt oder komponentenübergreifend: {path}")
            seen.add(path)
            all_paths.add(path)
            size = int(record.get("size", -1))
            if size < 0:
                raise ContractError(f"Dateigröße ist ungültig: {path}")
            mode = str(record.get("mode", ""))
            if mode not in {"0o644", "0o755"}:
                raise ContractError(f"Dateimodus ist nicht zugelassen: {path}:{mode}")
            digest_value = _sha(record.get("sha256"), f"Datei:{path}")
            digest.update(f"{path}\0{mode}\0{size}\0{digest_value}\n".encode())
            total_files += 1
            total_unpacked += size
        if digest.hexdigest() != str(component.get("tree_sha256", "")):
            raise ContractError(f"Komponentenbaum-Hash ist ungültig: {component_id}")
    return total_files, total_unpacked


def _validate_parts(parts: Any, components: dict[str, Any], maximum: int) -> None:
    if not isinstance(parts, list) or not (1 <= len(parts) <= MAX_PART_COUNT):
        raise ContractError("Teilpaketliste fehlt oder ist zu groß.")
    numbers: list[int] = []
    names: set[str] = set()
    for part in parts:
        if not isinstance(part, dict):
            raise ContractError("Teilpaketeintrag ist ungültig.")
        numbers.append(int(part.get("number", 0)))
        component_id = str(part.get("component", ""))
        if component_id not in COMPONENTS or not components[component_id].get("included"):
            raise ContractError(f"Teilpaket verweist auf ungültige Komponente: {component_id}")
        name = safe_relative(str(part.get("file", "")), field="Teilpaketname")
        signature_name = safe_relative(str(part.get("signature_file", "")), field="Signaturdatei")
        if "/" in name or "/" in signature_name or name in names or signature_name in names:
            raise ContractError("Teilpaketnamen sind doppelt oder enthalten Verzeichnisse.")
        names.update({name, signature_name})
        size = int(part.get("size", -1))
        unpacked = int(part.get("unpacked_bytes", -1))
        members = int(part.get("member_count", -1))
        if not (0 < size <= maximum) or not (0 <= unpacked <= MAX_UNPACKED_BYTES) or not (1 <= members <= MAX_TOTAL_FILES):
            raise ContractError(f"Teilpaketgrenzen sind ungültig: {name}")
        _sha(part.get("sha256"), f"Teilpaket:{name}")
        safe_relative(str(part.get("url", "")), field="Teilpaket-URL")
        safe_relative(str(part.get("signature_url", "")), field="Signatur-URL")
    if numbers != list(range(1, len(parts) + 1)):
        raise ContractError("Teilpaketnummern müssen lückenlos bei 1 beginnen.")


def validate_manifest(manifest: dict[str, Any], *, expected_key_id: str | None = None) -> None:
    if manifest.get("schema_version") != MANIFEST_SCHEMA or manifest.get("product") != PRODUCT:
        raise ContractError("Installationsmanifest hat Produkt oder Schema nicht bestanden.")
    version_tuple(str(manifest.get("version", "")))
    if not isinstance(manifest.get("release_sequence"), int) or int(manifest["release_sequence"]) < 1:
        raise ContractError("Release-Reihenfolge fehlt oder ist ungültig.")
    if not SHA256_RE.fullmatch(str(manifest.get("release_id", ""))):
        raise ContractError("Eindeutige Release-ID fehlt oder ist ungültig.")
    manifest_key_id = str(manifest.get("signing_key_id", ""))
    if expected_key_id and manifest_key_id != expected_key_id:
        raise ContractError("Manifest wurde nicht an den lokal vertrauten Signaturschlüssel gebunden.")
    if parse_utc(str(manifest.get("created_utc", "")), field="created_utc").year < 2020:
        raise ContractError("Manifestzeitpunkt ist unplausibel.")
    maximum = int(manifest.get("maximum_part_bytes", 0))
    if maximum < 1 or maximum > MAX_PART_BYTES_HARD:
        raise ContractError("Teilpaketgrenze ist ungültig.")
    layout = manifest.get("installation_layout")
    if not isinstance(layout, dict) or layout.get("strategy") != "ab-slots" or layout.get("slots") != list(SLOTS):
        raise ContractError("A/B-Installationsvertrag fehlt.")
    order = manifest.get("update_order")
    components = manifest.get("components")
    if not isinstance(order, list) or not isinstance(components, dict):
        raise ContractError("Komponentenvertrag fehlt.")
    if order != list(COMPONENTS) or len(order) != len(set(order)) or set(components) != set(COMPONENTS):
        raise ContractError("Komponentenreihenfolge ist inkonsistent.")
    total_files, total_unpacked = _validate_component_records(components)
    if total_files > MAX_TOTAL_FILES or total_unpacked > MAX_UNPACKED_BYTES:
        raise ContractError("Gesamtumfang des Releases überschreitet die Sicherheitsgrenzen.")
    if int(manifest.get("total_file_count", total_files)) != total_files:
        raise ContractError("Gesamtdateizahl ist inkonsistent.")
    if int(manifest.get("total_unpacked_bytes", total_unpacked)) != total_unpacked:
        raise ContractError("Gesamtgröße ist inkonsistent.")
    parts = manifest.get("parts")
    _validate_parts(parts, components, maximum)
    if int(manifest.get("part_count", -1)) != len(parts):
        raise ContractError("Teilpaketanzahl ist inkonsistent.")


def validate_channel_index(index: dict[str, Any], *, expected_key_id: str, now: datetime | None = None) -> None:
    if index.get("schema_version") != INDEX_SCHEMA or index.get("product") != PRODUCT:
        raise ContractError("Channel-Index hat Produkt oder Schema nicht bestanden.")
    if str(index.get("signing_key_id", "")) != expected_key_id:
        raise ContractError("Channel-Index ist nicht an den lokal vertrauten Schlüssel gebunden.")
    generation = index.get("generation")
    if not isinstance(generation, int) or generation < 1:
        raise ContractError("Channel-Generation fehlt oder ist ungültig.")
    created = parse_utc(str(index.get("created_utc", "")), field="created_utc")
    expires = parse_utc(str(index.get("expires_utc", "")), field="expires_utc")
    if expires <= created:
        raise ContractError("Channel-Index besitzt keinen gültigen Gültigkeitszeitraum.")
    current = now or datetime.now(timezone.utc)
    if current + CHANNEL_CLOCK_SKEW < created.replace(microsecond=0) or current - CHANNEL_CLOCK_SKEW > expires:
        raise ContractError("Channel-Index ist noch nicht gültig oder bereits abgelaufen.")
    channels = index.get("channels")
    if not isinstance(channels, dict) or set(channels) != {"stable", "rc"}:
        raise ContractError("Stable- und RC-Kanal müssen beide definiert sein.")
    for name, entry in channels.items():
        if not isinstance(entry, dict) or not isinstance(entry.get("available"), bool):
            raise ContractError(f"Kanal {name} ist ungültig.")
        if not entry["available"]:
            continue
        version_tuple(str(entry.get("version", "")))
        if not isinstance(entry.get("release_sequence"), int) or int(entry["release_sequence"]) < 1:
            raise ContractError(f"Release-Reihenfolge von {name} ist ungültig.")
        if int(entry.get("minimum_installer_schema", 0)) > MANIFEST_SCHEMA:
            raise ContractError(f"Kanal {name} benötigt einen neueren Installer.")
        safe_relative(str(entry.get("manifest_url", "")), field=f"Manifest-URL:{name}")
        safe_relative(str(entry.get("manifest_signature_url", "")), field=f"Manifest-Signatur-URL:{name}")
        _sha(entry.get("manifest_sha256"), f"Manifest:{name}")
        if int(entry.get("manifest_size", -1)) <= 0:
            raise ContractError(f"Manifestgröße von {name} ist ungültig.")


def _normalize_legacy_component_records(components: dict[str, Any]) -> tuple[dict[str, Any], int, int]:
    normalized = json.loads(json.dumps(components))
    all_paths: set[str] = set()
    total_files = 0
    total_bytes = 0
    for component_id in COMPONENTS:
        component = normalized[component_id]
        safe_optional_relative(str(component.get("install_path", "")), field=f"install_path:{component_id}")
        records = component.get("files")
        if not isinstance(records, list) or int(component.get("file_count", -1)) != len(records):
            raise ContractError(f"Legacy-Dateiliste von {component_id} ist inkonsistent.")
        original_digest = hashlib.sha256()
        for record in sorted(records, key=lambda item: str(item.get("path", ""))):
            path = safe_relative(str(record.get("path", "")), field=f"Dateipfad:{component_id}")
            if path in all_paths:
                raise ContractError(f"Legacy-Dateipfad ist doppelt: {path}")
            all_paths.add(path)
            size = int(record.get("size", -1))
            if size < 0:
                raise ContractError(f"Legacy-Dateigröße ist ungültig: {path}")
            digest_value = _sha(record.get("sha256"), f"Legacy-Datei:{path}")
            mode_text = str(record.get("mode", ""))
            try:
                mode_value = int(mode_text, 8)
            except ValueError as exc:
                raise ContractError(f"Legacy-Dateimodus ist ungültig: {path}:{mode_text}") from exc
            if mode_value < 0 or mode_value > 0o777 or mode_value & 0o7000:
                raise ContractError(f"Legacy-Dateimodus ist unsicher: {path}:{mode_text}")
            original_digest.update(f"{path}\0{mode_text}\0{size}\0{digest_value}\n".encode())
            record["mode"] = "0o755" if mode_value & 0o111 else "0o644"
            total_files += 1
            total_bytes += size
        if original_digest.hexdigest() != str(component.get("tree_sha256", "")):
            raise ContractError(f"Legacy-Komponentenbaum-Hash ist ungültig: {component_id}")
        digest = hashlib.sha256()
        for record in sorted(records, key=lambda item: str(item["path"])):
            digest.update(f"{record['path']}\0{record['mode']}\0{record['size']}\0{record['sha256']}\n".encode())
        component["tree_sha256"] = digest.hexdigest()
    return normalized, total_files, total_bytes


def validate_slot_snapshot(snapshot: dict[str, Any], *, trusted_key_id: str) -> dict[str, Any]:
    """Validiert auch bestätigte Slots älterer Installer ohne neue Download-Metadaten."""
    if snapshot.get("schema_version") != MANIFEST_SCHEMA or snapshot.get("product") != PRODUCT:
        raise ContractError("Slotmanifest hat Produkt oder Schema nicht bestanden.")
    version = str(snapshot.get("version", ""))
    version_tuple(version)
    sequence = int(snapshot.get("release_sequence", 0) or 0)
    if sequence < 1:
        raise ContractError("Slotmanifest besitzt keine gültige Release-Reihenfolge.")
    layout = snapshot.get("installation_layout", {})
    if not isinstance(layout, dict) or layout.get("strategy") != "ab-slots" or layout.get("slots") != list(SLOTS):
        raise ContractError("Slotmanifest besitzt keinen gültigen A/B-Vertrag.")
    order = snapshot.get("update_order")
    components = snapshot.get("components")
    if order != list(COMPONENTS) or not isinstance(components, dict) or set(components) != set(COMPONENTS):
        raise ContractError("Slotmanifest besitzt keinen vollständigen Komponentenvertrag.")
    try:
        total_files, total_bytes = _validate_component_records(components)
        normalized_components = json.loads(json.dumps(components))
    except ContractError:
        normalized_components, total_files, total_bytes = _normalize_legacy_component_records(components)
    normalized = dict(snapshot)
    normalized["components"] = normalized_components
    normalized["signing_key_id"] = str(snapshot.get("signing_key_id") or trusted_key_id)
    if normalized["signing_key_id"] != trusted_key_id:
        raise ContractError("Slotmanifest ist an einen anderen Signaturschlüssel gebunden.")
    normalized["total_file_count"] = total_files
    normalized["total_unpacked_bytes"] = total_bytes
    identity = {
        "product": PRODUCT,
        "version": version,
        "release_sequence": sequence,
        "signing_key_id": trusted_key_id,
        "components": {component_id: normalized_components[component_id]["tree_sha256"] for component_id in COMPONENTS},
    }
    derived_release_id = hashlib.sha256(canonical_json(identity)).hexdigest()
    release_id = str(snapshot.get("release_id") or derived_release_id)
    if not SHA256_RE.fullmatch(release_id):
        raise ContractError("Slotmanifest besitzt keine gültige Release-ID.")
    normalized["release_id"] = release_id
    normalized["slot_snapshot_schema"] = 1
    return normalized

