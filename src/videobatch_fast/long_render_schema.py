from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .safe_io import read_json

SCHEMA_VERSION = 1
TERMINAL_STATES = {"completed", "failed", "cancelled"}
PAUSED_STATES = {"paused", "paused_timeout", "paused_failure"}


class LongRenderContractError(RuntimeError):
    """Raised when the long-render acceptance contract cannot be executed safely."""


@dataclass(frozen=True, slots=True)
class ResourceLimits:
    cpu_percent: int
    memory_mb: int
    invocation_timeout_seconds: int
    total_timeout_seconds: int
    heartbeat_seconds: int

    def validate(self) -> None:
        if not 1 <= self.cpu_percent <= 100:
            raise LongRenderContractError("CPU-Grenze muss zwischen 1 und 100 Prozent liegen.")
        if self.memory_mb < 256:
            raise LongRenderContractError("RAM-Grenze muss mindestens 256 MiB betragen.")
        if self.invocation_timeout_seconds < 30:
            raise LongRenderContractError("Der Aufruf-Timeout muss mindestens 30 Sekunden betragen.")
        if self.total_timeout_seconds < self.invocation_timeout_seconds:
            raise LongRenderContractError("Der Gesamt-Timeout darf nicht kleiner als der Aufruf-Timeout sein.")
        if not 5 <= self.heartbeat_seconds <= 3600:
            raise LongRenderContractError("Das Heartbeat-Intervall muss zwischen 5 und 3600 Sekunden liegen.")


@dataclass(frozen=True, slots=True)
class TargetPolicy:
    require_external: bool
    required_filesystem: str
    max_write_mib_s: float
    min_free_gib: float
    require_hard_limits: bool


@dataclass(frozen=True, slots=True)
class JobSpec:
    job_id: str
    audio: Path
    media: tuple[Path, ...]
    output_name: str


@dataclass(frozen=True, slots=True)
class LoadedContract:
    source: Path
    candidate: str
    package: Path | None
    target_dir: Path
    state_file: Path
    jobs: tuple[JobSpec, ...]
    options: dict[str, Any]
    limits: ResourceLimits
    target_policy: TargetPolicy
    digest: str


def utc_now() -> str:
    import time

    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def canonical_hash(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path, *, chunk_size: int = 4 * 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def _resolve_path(base: Path, value: str) -> Path:
    path = Path(value).expanduser()
    return path.resolve() if path.is_absolute() else (base / path).resolve()


def _safe_output_name(value: str) -> str:
    candidate = Path(value)
    if candidate.is_absolute() or len(candidate.parts) != 1 or candidate.name in {"", ".", ".."}:
        raise LongRenderContractError(f"Unsicherer Ausgabename: {value!r}")
    if candidate.suffix.lower() != ".mp4":
        raise LongRenderContractError(f"Ausgabe muss eine MP4-Datei sein: {value!r}")
    return candidate.name


def load_contract(path: Path | str, *, state_file: Path | None = None) -> LoadedContract:
    source = Path(path).expanduser().resolve()
    raw = read_json(source)
    if not isinstance(raw, dict) or int(raw.get("schema_version", 0)) != SCHEMA_VERSION:
        raise LongRenderContractError("Unbekannte oder fehlende Langzeitrender-Vertragsschemaversion.")
    base = source.parent
    candidate = str(raw.get("candidate", "")).strip()
    if not candidate:
        raise LongRenderContractError("Der Kandidat fehlt im Langzeitrender-Vertrag.")
    target_dir = _resolve_path(base, str(raw.get("target_dir", "")))
    package_value = str(raw.get("package", "")).strip()
    package = _resolve_path(base, package_value) if package_value else None

    limit_raw = raw.get("limits")
    if not isinstance(limit_raw, dict):
        raise LongRenderContractError("Ressourcengrenzen fehlen im Langzeitrender-Vertrag.")
    limits = ResourceLimits(
        cpu_percent=int(limit_raw.get("cpu_percent", 50)),
        memory_mb=int(limit_raw.get("memory_mb", 4096)),
        invocation_timeout_seconds=int(limit_raw.get("invocation_timeout_seconds", 8 * 3600)),
        total_timeout_seconds=int(limit_raw.get("total_timeout_seconds", 16 * 3600)),
        heartbeat_seconds=int(limit_raw.get("heartbeat_seconds", 900)),
    )
    limits.validate()

    target_raw = raw.get("target")
    if not isinstance(target_raw, dict):
        raise LongRenderContractError("Zielrichtlinie fehlt im Langzeitrender-Vertrag.")
    target_policy = TargetPolicy(
        require_external=bool(target_raw.get("require_external", True)),
        required_filesystem=str(target_raw.get("required_filesystem", "ext4")),
        max_write_mib_s=float(target_raw.get("max_write_mib_s", 35.0)),
        min_free_gib=float(target_raw.get("min_free_gib", 500.0)),
        require_hard_limits=bool(target_raw.get("require_hard_limits", True)),
    )
    if target_policy.max_write_mib_s <= 0:
        raise LongRenderContractError("Die maximale Schreibrate muss größer als null sein.")
    if target_policy.min_free_gib <= 0:
        raise LongRenderContractError("Der geforderte freie Zielspeicher muss größer als null sein.")

    jobs_raw = raw.get("jobs")
    if not isinstance(jobs_raw, list) or not jobs_raw:
        raise LongRenderContractError("Der Vertrag enthält keine Renderaufträge.")
    jobs: list[JobSpec] = []
    identifiers: set[str] = set()
    outputs: set[str] = set()
    for item in jobs_raw:
        if not isinstance(item, dict):
            raise LongRenderContractError("Ein Renderauftrag ist kein Objekt.")
        job_id = str(item.get("id", "")).strip()
        if not job_id or job_id in identifiers:
            raise LongRenderContractError(f"Fehlende oder doppelte Auftrags-ID: {job_id!r}")
        audio = _resolve_path(base, str(item.get("audio", "")))
        media_raw = item.get("media")
        if not isinstance(media_raw, list) or not media_raw:
            raise LongRenderContractError(f"Auftrag {job_id} besitzt keine feste Medienauswahl.")
        media = tuple(_resolve_path(base, str(value)) for value in media_raw)
        output_name = _safe_output_name(str(item.get("output", "")))
        if output_name in outputs:
            raise LongRenderContractError(f"Doppelter Ausgabename: {output_name}")
        jobs.append(JobSpec(job_id, audio, media, output_name))
        identifiers.add(job_id)
        outputs.add(output_name)

    options = raw.get("options")
    if not isinstance(options, dict):
        options = {}
    persisted = {
        "schema_version": SCHEMA_VERSION,
        "candidate": candidate,
        "package": str(package) if package else "",
        "target_dir": str(target_dir),
        "jobs": [
            {
                "id": item.job_id,
                "audio": str(item.audio),
                "media": [str(value) for value in item.media],
                "output": item.output_name,
            }
            for item in jobs
        ],
        "options": options,
        "limits": asdict(limits),
        "target": asdict(target_policy),
    }
    digest = canonical_hash(persisted)
    resolved_state = state_file or target_dir / ".provoware-long-render" / "state.json"
    return LoadedContract(
        source=source,
        candidate=candidate,
        package=package,
        target_dir=target_dir,
        state_file=resolved_state.expanduser().resolve(),
        jobs=tuple(jobs),
        options=dict(options),
        limits=limits,
        target_policy=target_policy,
        digest=digest,
    )


def unique_inputs(contract: LoadedContract) -> tuple[Path, ...]:
    selected: list[Path] = []
    for job in contract.jobs:
        for path in (job.audio, *job.media):
            if path not in selected:
                selected.append(path)
    if contract.package and contract.package not in selected:
        selected.append(contract.package)
    return tuple(selected)


def build_input_manifest(contract: LoadedContract) -> dict[str, Any]:
    entries: list[dict[str, Any]] = []
    for path in unique_inputs(contract):
        if not path.is_file():
            raise LongRenderContractError(f"Eingabedatei fehlt: {path}")
        stat = path.stat()
        entries.append(
            {
                "path": str(path),
                "size": stat.st_size,
                "mtime_ns": stat.st_mtime_ns,
                "sha256": sha256_file(path),
            }
        )
    payload = {"schema_version": 1, "created_at": utc_now(), "entries": entries}
    payload["digest"] = canonical_hash(entries)
    return payload


def verify_input_manifest(manifest: dict[str, Any], *, full_hash: bool) -> None:
    entries = manifest.get("entries")
    if not isinstance(entries, list):
        raise LongRenderContractError("Eingabemanifest ist beschädigt.")
    for item in entries:
        if not isinstance(item, dict):
            raise LongRenderContractError("Eingabemanifest enthält einen ungültigen Eintrag.")
        path = Path(str(item.get("path", "")))
        if not path.is_file():
            raise LongRenderContractError(f"Originalmedium fehlt nach Start: {path}")
        stat = path.stat()
        if stat.st_size != int(item.get("size", -1)) or stat.st_mtime_ns != int(item.get("mtime_ns", -1)):
            raise LongRenderContractError(f"Originalmedium wurde verändert: {path}")
        if full_hash and sha256_file(path) != str(item.get("sha256", "")):
            raise LongRenderContractError(f"SHA-256 des Originalmediums wurde verändert: {path}")
