from __future__ import annotations

import os
import shutil
import subprocess
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .long_render_schema import LoadedContract, LongRenderContractError, ResourceLimits, unique_inputs
from .safe_io import fsync_directory


@dataclass(frozen=True, slots=True)
class MountInfo:
    mount_point: Path
    filesystem: str
    source: str
    options: tuple[str, ...]


def _decode_mount_path(value: str) -> Path:
    decoded = value.replace("\\040", " ").replace("\\011", "\t").replace("\\134", "\\")
    return Path(decoded)


def find_mount(path: Path) -> MountInfo:
    resolved = path.resolve()
    selected: MountInfo | None = None
    try:
        lines = Path("/proc/self/mountinfo").read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise LongRenderContractError(f"Mount-Informationen konnten nicht gelesen werden: {exc}") from exc
    for line in lines:
        left, separator, right = line.partition(" - ")
        if not separator:
            continue
        left_fields = left.split()
        right_fields = right.split()
        if len(left_fields) < 6 or len(right_fields) < 2:
            continue
        mount_point = _decode_mount_path(left_fields[4])
        try:
            resolved.relative_to(mount_point)
        except ValueError:
            continue
        candidate = MountInfo(
            mount_point=mount_point,
            filesystem=right_fields[0],
            source=right_fields[1],
            options=tuple(left_fields[5].split(",")),
        )
        if selected is None or len(str(candidate.mount_point)) > len(str(selected.mount_point)):
            selected = candidate
    if selected is None:
        raise LongRenderContractError(f"Kein Einhängepunkt für {resolved} gefunden.")
    return selected


def _udev_properties(device: str) -> dict[str, str]:
    binary = shutil.which("udevadm")
    if not binary:
        return {}
    try:
        result = subprocess.run(
            [binary, "info", "--query=property", f"--name={device}"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
            errors="replace",
        )
    except (OSError, subprocess.SubprocessError):
        return {}
    properties: dict[str, str] = {}
    for line in result.stdout.splitlines():
        key, separator, value = line.partition("=")
        if separator:
            properties[key] = value
    return properties


def measure_write_speed(target_dir: Path, *, sample_bytes: int = 64 * 1024 * 1024) -> float:
    probe = target_dir / f".provoware-write-probe-{uuid.uuid4().hex}.tmp"
    block = b"\0" * (1024 * 1024)
    started = time.monotonic()
    try:
        with probe.open("xb", buffering=0) as handle:
            for _ in range(max(1, sample_bytes // len(block))):
                handle.write(block)
            handle.flush()
            os.fsync(handle.fileno())
        elapsed = max(0.001, time.monotonic() - started)
        return sample_bytes / (1024 * 1024) / elapsed
    finally:
        probe.unlink(missing_ok=True)
        fsync_directory(target_dir)


def validate_target(contract: LoadedContract, *, allow_rehearsal_target: bool = False) -> dict[str, Any]:
    target = contract.target_dir
    target.mkdir(parents=True, exist_ok=True)
    if not os.access(target, os.W_OK | os.X_OK):
        raise LongRenderContractError(f"Zielordner ist nicht beschreibbar: {target}")
    mount = find_mount(target)
    properties = _udev_properties(mount.source) if mount.source.startswith("/dev/") else {}
    external = properties.get("ID_BUS") == "usb"
    if contract.target_policy.require_external and not allow_rehearsal_target:
        if mount.mount_point == Path("/") or not mount.source.startswith("/dev/"):
            raise LongRenderContractError("Das Ziel ist kein eigener physischer Blockdatenträger.")
        if mount.filesystem != contract.target_policy.required_filesystem:
            raise LongRenderContractError(
                f"Zieldateisystem ist {mount.filesystem}, erwartet wird {contract.target_policy.required_filesystem}."
            )
        if not external:
            raise LongRenderContractError("Das Ziel konnte nicht als USB-Datenträger bestätigt werden.")
    free_gib = shutil.disk_usage(target).free / (1024**3)
    if free_gib < contract.target_policy.min_free_gib and not allow_rehearsal_target:
        raise LongRenderContractError(
            f"Ziel besitzt nur {free_gib:.1f} GiB freien Platz; "
            f"gefordert sind {contract.target_policy.min_free_gib:.1f} GiB."
        )
    if "rw" not in mount.options and not allow_rehearsal_target:
        raise LongRenderContractError("Der Ziel-Datenträger ist nicht schreibbar eingehängt.")
    for input_path in unique_inputs(contract):
        input_mount = find_mount(input_path)
        if input_mount.mount_point == mount.mount_point and not allow_rehearsal_target:
            raise LongRenderContractError(
                "Originalmedien und Ausgabeziel dürfen nicht auf demselben Datenträger liegen."
            )
        if "ro" not in input_mount.options and not allow_rehearsal_target:
            raise LongRenderContractError(
                f"Originalmedium liegt nicht auf einem schreibgeschützten Mount: {input_path}"
            )
    speed = measure_write_speed(target)
    if speed > contract.target_policy.max_write_mib_s and not allow_rehearsal_target:
        raise LongRenderContractError(
            f"Ziel ist mit {speed:.1f} MiB/s schneller als die festgelegten "
            f"{contract.target_policy.max_write_mib_s:.1f} MiB/s."
        )
    return {
        "mount_point": str(mount.mount_point),
        "filesystem": mount.filesystem,
        "source": mount.source,
        "mount_options": list(mount.options),
        "external_usb": external,
        "write_mib_s": round(speed, 3),
        "free_gib": round(free_gib, 3),
        "device_model": properties.get("ID_MODEL", ""),
        "device_serial": properties.get("ID_SERIAL_SHORT", properties.get("ID_SERIAL", "")),
        "filesystem_uuid": properties.get("ID_FS_UUID", ""),
        "rehearsal_target": bool(allow_rehearsal_target),
    }


def hard_limit_prefix(limits: ResourceLimits) -> list[str]:
    binary = shutil.which("systemd-run")
    if not binary:
        return []
    return [
        binary,
        "--user",
        "--scope",
        "--quiet",
        "--wait",
        "--collect",
        "--pipe",
        f"--property=CPUQuota={limits.cpu_percent}%",
        f"--property=MemoryMax={limits.memory_mb}M",
        "--",
    ]


def validate_hard_limit_runtime(limits: ResourceLimits) -> None:
    prefix = hard_limit_prefix(limits)
    if not prefix:
        raise LongRenderContractError("Harte CPU-/RAM-Grenzen benötigen systemd-run im Benutzerkontext.")
    try:
        result = subprocess.run(
            [*prefix, "true"],
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
            errors="replace",
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise LongRenderContractError(f"Harte Ressourcengrenzen konnten nicht initialisiert werden: {exc}") from exc
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "unbekannter systemd-run-Fehler").strip().splitlines()
        message = detail[-1] if detail else "unbekannt"
        raise LongRenderContractError(f"Harte Ressourcengrenzen sind nicht verfügbar: {message[:400]}")
