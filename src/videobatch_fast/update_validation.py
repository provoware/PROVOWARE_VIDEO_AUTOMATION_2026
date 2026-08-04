from __future__ import annotations

import hashlib
import json
import stat
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

from .registry import load_json
from .visual_approval import approval_fingerprint, inspection_manifest_hash
from .artifact_signing import verify_signed_update_manifest


@dataclass(frozen=True, slots=True)
class UpdateCheck:
    valid: bool
    version: str
    message: str
    files: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class UpdatePolicy:
    max_files: int
    max_uncompressed: int
    max_ratio: float
    require_compatible_from: bool
    allowed_operations: frozenset[str]

    @classmethod
    def load(cls) -> UpdatePolicy:
        raw = load_json("registries/UPDATE_REGISTRY.json")
        return cls(
            max_files=int(raw.get("max_files", 2000)),
            max_uncompressed=int(raw.get("max_uncompressed_bytes", 1_073_741_824)),
            max_ratio=float(raw.get("max_compression_ratio", 200.0)),
            require_compatible_from=bool(raw.get("require_compatible_from")),
            allowed_operations=frozenset(str(value) for value in raw.get("allowed_operations", [])),
        )


def safe_member(name: str) -> bool:
    path = PurePosixPath(name)
    return bool(name) and not path.is_absolute() and ".." not in path.parts and not name.startswith(("~", "/"))


def read_manifest(archive: zipfile.ZipFile) -> dict[str, Any]:
    raw = archive.read("update_manifest.json").decode("utf-8")
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise ValueError("Update-Manifest muss ein JSON-Objekt sein.")
    return value


class UpdatePackageValidator:
    def __init__(self, current_version: str, policy: UpdatePolicy | None = None) -> None:
        self.current_version = current_version
        self.policy = policy or UpdatePolicy.load()

    def validate(self, package: Path) -> UpdateCheck:
        if not package.is_file():
            return UpdateCheck(False, "", "Update-Paket wurde nicht gefunden.")
        try:
            with zipfile.ZipFile(package) as archive:
                envelope_error, names = self._validate_envelope(archive)
                if envelope_error:
                    return UpdateCheck(False, "", envelope_error)
                manifest = read_manifest(archive)
                return self._validate_manifest(archive, manifest, names)
        except (OSError, ValueError, zipfile.BadZipFile, UnicodeError, json.JSONDecodeError) as exc:
            return UpdateCheck(False, "", f"Update-Paket ist nicht lesbar: {exc}")

    def _validate_envelope(self, archive: zipfile.ZipFile) -> tuple[str, set[str]]:
        infos = archive.infolist()
        names = [info.filename for info in infos]
        unique = set(names)
        if len(names) != len(unique):
            return "Das Paket enthält doppelte ZIP-Dateinamen.", unique
        if "update_manifest.json" not in unique:
            return "update_manifest.json fehlt.", unique
        if len(infos) > self.policy.max_files + 1:
            return "Update-Paket enthält zu viele Dateien.", unique
        total_size = 0
        for info in infos:
            error = self._member_error(info)
            if error:
                return error, unique
            total_size += info.file_size
        if total_size > self.policy.max_uncompressed:
            return "Update-Paket überschreitet die erlaubte entpackte Größe.", unique
        return "", unique

    def _member_error(self, info: zipfile.ZipInfo) -> str:
        mode = (info.external_attr >> 16) & 0xFFFF
        if not safe_member(info.filename) or stat.S_ISLNK(mode):
            return f"Unsicherer ZIP-Eintrag: {info.filename}"
        if info.compress_size and info.file_size / info.compress_size > self.policy.max_ratio:
            return f"Verdächtige Kompressionsrate: {info.filename}"
        return ""

    def _validate_manifest(
        self,
        archive: zipfile.ZipFile,
        manifest: dict[str, Any],
        names: set[str],
    ) -> UpdateCheck:
        version = str(manifest.get("version", ""))
        compatibility_error = self._compatibility_error(manifest)
        if compatibility_error:
            return UpdateCheck(False, version, compatibility_error)
        declared = manifest.get("files", [])
        if not isinstance(declared, list) or not declared:
            return UpdateCheck(False, version, "Dateiliste fehlt.")
        entry_error, declared_paths, payload_paths = self._validate_entries(archive, declared, names)
        if entry_error:
            return UpdateCheck(False, version, entry_error)
        signature_error = self._signature_error(manifest, archive, names)
        if signature_error:
            return UpdateCheck(False, version, signature_error)
        extras = names - {"update_manifest.json", "update_signature.json"} - payload_paths
        if extras:
            return UpdateCheck(False, version, f"Nicht deklarierte Dateien: {sorted(extras)[0]}")
        visual_error = self._visual_binding_error(manifest, archive, names)
        if visual_error:
            return UpdateCheck(False, version, visual_error)
        return UpdateCheck(
            True,
            version,
            "Update-Paket ist konsistent und vollständig deklariert.",
            tuple(sorted(declared_paths)),
        )

    def _compatibility_error(self, manifest: dict[str, Any]) -> str:
        compatible = manifest.get("compatible_from", [])
        if self.policy.require_compatible_from and self.current_version not in compatible:
            return "Die aktuelle Version ist nicht als kompatibel deklariert."
        return ""

    def _validate_entries(
        self,
        archive: zipfile.ZipFile,
        declared: list[Any],
        names: set[str],
    ) -> tuple[str, set[str], set[str]]:
        declared_paths: set[str] = set()
        payload_paths: set[str] = set()
        for item in declared:
            error, path, payload = self._validate_entry(archive, item, names, declared_paths)
            if error:
                return error, declared_paths, payload_paths
            declared_paths.add(path)
            if payload:
                payload_paths.add(path)
        return "", declared_paths, payload_paths

    def _validate_entry(
        self,
        archive: zipfile.ZipFile,
        item: Any,
        names: set[str],
        declared_paths: set[str],
    ) -> tuple[str, str, bool]:
        if not isinstance(item, dict):
            return "Ungültiger Dateieintrag.", "", False
        path = str(item.get("path", ""))
        operation = str(item.get("operation", ""))
        if not safe_member(path) or path in declared_paths:
            return f"Ungültiger oder doppelter Update-Pfad: {path}", path, False
        if operation not in self.policy.allowed_operations:
            return f"Nicht erlaubte Update-Operation: {operation}", path, False
        if operation == "delete":
            return self._delete_error(path, names), path, False
        if path not in names:
            return f"Update-Datei fehlt: {path}", path, False
        expected = str(item.get("sha256", ""))
        if len(expected) != 64 or hashlib.sha256(archive.read(path)).hexdigest() != expected:
            return f"Prüfsumme stimmt nicht: {path}", path, False
        return "", path, True

    @staticmethod
    def _delete_error(path: str, names: set[str]) -> str:
        if path in names:
            return f"Löschoperation darf keine Nutzdatei enthalten: {path}"
        return ""


    @staticmethod
    def _signature_error(manifest: dict[str, Any], archive: zipfile.ZipFile, names: set[str]) -> str:
        if not bool(manifest.get("official", False)):
            return ""
        if "update_signature.json" not in names:
            return "Offizielles Update enthält keine kryptografische Signatur."
        public_key = Path(__file__).resolve().parents[2] / "resources" / "signing" / "release-public-key.pem"
        if not public_key.is_file():
            return "Öffentlicher Release-Schlüssel fehlt."
        check = verify_signed_update_manifest(
            archive.read("update_manifest.json"), archive.read("update_signature.json"), public_key
        )
        return "" if check.valid else check.message

    @staticmethod
    def _visual_binding_error(manifest: dict[str, Any], archive: zipfile.ZipFile, names: set[str]) -> str:
        if str(manifest.get("channel", "release-candidate")) != "stable":
            return ""
        binding = manifest.get("visual_approval")
        if not isinstance(binding, dict):
            return "Stable-Update enthält keine Bindung an die visuelle Freigabe."
        visual_path = "VISUAL_INSPECTION_MANIFEST.json"
        if visual_path not in names:
            return "Stable-Update enthält das signierte visuelle Prüfmanifest nicht."
        visual_manifest = UpdatePackageValidator._read_visual_manifest(archive, visual_path)
        if visual_manifest is None:
            return "Visuelles Prüfmanifest im Update ist ungültig."
        expected_contract = inspection_manifest_hash(visual_manifest)
        expected_approval = approval_fingerprint(visual_manifest)
        if str(binding.get("visual_contract_sha256", "")) != expected_contract:
            return "Stable-Update ist nicht an den aktuellen visuellen Vertrag gebunden."
        if str(binding.get("approval_sha256", "")) != expected_approval or not expected_approval:
            return "Stable-Update ist nicht an die signierte Desktop-Abnahme gebunden."
        approval_payload = visual_manifest.get("manual_approval", {}).get("payload", {})
        if str(binding.get("build_id", "")) != str(approval_payload.get("build_id", "")):
            return "Build-ID und visuelle Freigabe stimmen nicht überein."
        return ""

    @staticmethod
    def _read_visual_manifest(archive: zipfile.ZipFile, path: str) -> dict[str, Any] | None:
        try:
            value = json.loads(archive.read(path).decode("utf-8"))
        except (UnicodeError, json.JSONDecodeError):
            return None
        return value if isinstance(value, dict) else None


def validate_update_package(package: Path, current_version: str) -> UpdateCheck:
    return UpdatePackageValidator(current_version).validate(Path(package))
