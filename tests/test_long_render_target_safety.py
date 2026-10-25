"""Target-policy fault injection; these tests do not certify physical hardware."""
from __future__ import annotations

import subprocess
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

from videobatch_fast import long_render_target as target
from videobatch_fast.long_render_schema import (
    JobSpec, LoadedContract, LongRenderContractError, ResourceLimits, TargetPolicy,
)


@pytest.fixture
def contract(tmp_path: Path, monkeypatch) -> LoadedContract:
    source = tmp_path / "source.wav"
    source.write_bytes(b"unchanged original")
    selected = LoadedContract(
        tmp_path / "contract.json", "candidate", None, tmp_path / "output",
        tmp_path / "state.json", (JobSpec("one", source, (source,), "out.mp4"),), {},
        ResourceLimits(50, 512, 60, 180, 5), TargetPolicy(True, "ext4", 35, 500, True), "digest",
    )
    output_mount = target.MountInfo(Path("/mnt/output"), "ext4", "/dev/sdb1", ("rw",))
    input_mount = target.MountInfo(Path("/mnt/input"), "ext4", "/dev/sda1", ("ro",))
    monkeypatch.setattr(target, "find_mount", lambda p: output_mount if p == selected.target_dir else input_mount)
    monkeypatch.setattr(target, "_udev_properties", lambda _device: {"ID_BUS": "usb", "ID_MODEL": "test"})
    monkeypatch.setattr(target.shutil, "disk_usage", lambda _path: SimpleNamespace(free=600 * 1024**3))
    monkeypatch.setattr(target, "measure_write_speed", lambda _path: 12.0)
    return selected


def test_verified_target_observations_are_reported_without_touching_sources(contract) -> None:
    result = target.validate_target(contract)
    assert result["external_usb"] is True
    assert result["rehearsal_target"] is False
    assert result["write_mib_s"] == 12
    assert contract.jobs[0].audio.read_bytes() == b"unchanged original"


@pytest.mark.parametrize("fault,message", [
    ("root", "Blockdatenträger"), ("filesystem", "Zieldateisystem"),
    ("bus", "USB"), ("space", "freien Platz"), ("readonly", "nicht schreibbar"),
    ("same_device", "demselben Datenträger"), ("writable_source", "schreibgeschützten"),
    ("speed", "schneller"),
])
def test_invalid_target_observations_block_acceptance(contract, monkeypatch, fault, message) -> None:
    output = target.MountInfo(Path("/mnt/output"), "ext4", "/dev/sdb1", ("rw",))
    source = target.MountInfo(Path("/mnt/input"), "ext4", "/dev/sda1", ("ro",))
    if fault == "root":
        output = replace(output, mount_point=Path("/"), source="overlay")
    elif fault == "filesystem":
        output = replace(output, filesystem="tmpfs")
    elif fault == "readonly":
        output = replace(output, options=("ro",))
    elif fault == "same_device":
        source = output
    elif fault == "writable_source":
        source = replace(source, options=("rw",))
    elif fault == "bus":
        monkeypatch.setattr(target, "_udev_properties", lambda _device: {"ID_BUS": "ata"})
    elif fault == "space":
        monkeypatch.setattr(target.shutil, "disk_usage", lambda _path: SimpleNamespace(free=1))
    elif fault == "speed":
        monkeypatch.setattr(target, "measure_write_speed", lambda _path: 99.0)
    monkeypatch.setattr(target, "find_mount", lambda p: output if p == contract.target_dir else source)
    with pytest.raises(LongRenderContractError, match=message):
        target.validate_target(contract)
    assert contract.jobs[0].audio.read_bytes() == b"unchanged original"


def test_rehearsal_remains_explicit_and_cannot_impersonate_real_acceptance(contract, monkeypatch) -> None:
    mount = target.MountInfo(Path("/"), "overlay", "overlay", ("rw",))
    monkeypatch.setattr(target, "find_mount", lambda _path: mount)
    monkeypatch.setattr(target.shutil, "disk_usage", lambda _path: SimpleNamespace(free=1))
    result = target.validate_target(contract, allow_rehearsal_target=True)
    assert result["rehearsal_target"] is True
    assert result["external_usb"] is False


def test_mount_parser_chooses_longest_matching_mount_and_decodes_spaces(monkeypatch) -> None:
    text = (
        "malformed\n"
        "1 0 0:1 / / rw - overlay overlay rw\n"
        "2 0 8:1 / /mnt/media\\040files ro - ext4 /dev/sdb1 ro\n"
        "3 0 8:2 / /unrelated rw - ext4 /dev/sdc1 rw\n"
    )
    monkeypatch.setattr(Path, "read_text", lambda *_args, **_kwargs: text)
    found = target.find_mount(Path("/mnt/media files/video.mp4"))
    assert found.mount_point == Path("/mnt/media files")
    assert found.source == "/dev/sdb1"
    assert found.options == ("ro",)


def test_unreadable_mount_table_blocks_validation(tmp_path, monkeypatch) -> None:
    def denied(*_args, **_kwargs):
        raise PermissionError("denied")
    monkeypatch.setattr(Path, "read_text", denied)
    with pytest.raises(LongRenderContractError, match="Mount-Informationen"):
        target.find_mount(tmp_path)


def test_real_write_probe_removes_only_its_own_temporary_file(tmp_path, monkeypatch) -> None:
    original = tmp_path / "keep.wav"
    original.write_bytes(b"keep")
    times = iter((1.0, 1.25))
    monkeypatch.setattr(target.time, "monotonic", lambda: next(times))
    assert target.measure_write_speed(tmp_path, sample_bytes=1024**2) == 4.0
    assert list(tmp_path.iterdir()) == [original]
    assert original.read_bytes() == b"keep"


@pytest.mark.parametrize("failure", ["missing", "timeout", "rejected", "success"])
def test_hard_resource_limits_never_silently_degrade(monkeypatch, failure) -> None:
    limits = ResourceLimits(50, 512, 60, 180, 5)
    monkeypatch.setattr(target.shutil, "which", lambda _name: None if failure == "missing" else "/usr/bin/systemd-run")
    calls = []
    def run(command, **kwargs):
        calls.append((command, kwargs))
        if failure == "timeout":
            raise subprocess.TimeoutExpired(command, 20)
        return SimpleNamespace(returncode=1 if failure == "rejected" else 0, stdout="", stderr="denied")
    monkeypatch.setattr(target.subprocess, "run", run)
    if failure == "success":
        target.validate_hard_limit_runtime(limits)
        assert "--property=CPUQuota=50%" in calls[0][0]
        assert "--property=MemoryMax=512M" in calls[0][0]
        assert calls[0][1]["timeout"] == 20
    else:
        with pytest.raises(LongRenderContractError):
            target.validate_hard_limit_runtime(limits)
