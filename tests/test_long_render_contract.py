from __future__ import annotations

import json
from pathlib import Path

import pytest

from videobatch_fast.long_render_contract import (
    LongRenderAcceptance,
    LongRenderContractError,
    _reservation_path,
    load_contract,
)
from videobatch_fast.models import JobResult, MediaInfo


def _write_contract(tmp_path: Path, *, target: Path, jobs: int = 2) -> Path:
    source = tmp_path / "inputs"
    source.mkdir()
    job_items = []
    for index in range(1, jobs + 1):
        audio = source / f"audio-{index}.wav"
        image_a = source / f"image-{index}-a.png"
        image_b = source / f"image-{index}-b.png"
        audio.write_bytes((f"audio-{index}" * 100).encode())
        image_a.write_bytes((f"image-{index}-a" * 100).encode())
        image_b.write_bytes((f"image-{index}-b" * 100).encode())
        job_items.append(
            {
                "id": f"{index:03d}",
                "audio": str(audio),
                "media": [str(image_a), str(image_b)],
                "output": f"output-{index:03d}.mp4",
            }
        )
    payload = {
        "schema_version": 1,
        "candidate": "2.8.3-rc24",
        "target_dir": str(target),
        "limits": {
            "cpu_percent": 50,
            "memory_mb": 512,
            "invocation_timeout_seconds": 60,
            "total_timeout_seconds": 180,
            "heartbeat_seconds": 5,
        },
        "target": {
            "require_external": False,
            "required_filesystem": "ext4",
            "max_write_mib_s": 10000,
            "min_free_gib": 0.001,
            "require_hard_limits": False,
        },
        "options": {"resolution": "Original", "profile": "turbo", "fps": 12, "max_threads": 1},
        "jobs": job_items,
    }
    contract = tmp_path / "contract.json"
    contract.write_text(json.dumps(payload), encoding="utf-8")
    return contract


def _install_fakes(monkeypatch: pytest.MonkeyPatch) -> None:
    import videobatch_fast.long_render_contract as module
    import videobatch_fast.long_render_execution as execution

    monkeypatch.setattr(
        module,
        "validate_target",
        lambda _contract, allow_rehearsal_target=False: {
            "mount_point": "/tmp",
            "filesystem": "tmpfs",
            "source": "tmpfs",
            "mount_options": ["rw"],
            "external_usb": False,
            "write_mib_s": 1.0,
            "free_gib": 10.0,
            "rehearsal_target": bool(allow_rehearsal_target),
        },
    )

    def fake_probe(path: Path) -> MediaInfo:
        kind = "audio" if path.suffix == ".wav" else "image"
        return MediaInfo(path=path, kind=kind, duration=2.0 if kind == "audio" else None, width=64, height=64)

    monkeypatch.setattr(execution, "probe_media", fake_probe)
    monkeypatch.setattr(module, "verify_output", lambda *_args, **_kwargs: (True, "vollständig geprüft"))


def _executor(job, _options, emit, cancelled):
    if cancelled():
        return JobResult(job, False, 143, 0.0, "abgebrochen")
    job.output.write_bytes((job.output.name * 5000).encode())
    emit("log", {"message": "fertig"})
    return JobResult(job, True, 0, 0.01, "ok")


def test_checkpoint_resume_is_idempotent_and_releases_reservations(tmp_path: Path, monkeypatch) -> None:
    _install_fakes(monkeypatch)
    target = tmp_path / "target"
    contract_path = _write_contract(tmp_path, target=target)
    contract = load_contract(contract_path)

    first = LongRenderAcceptance(
        contract,
        allow_rehearsal_target=True,
        allow_soft_limits=True,
        executor=_executor,
    )
    first.prepare(resume=False)
    paused = first.run(checkpoint_stop_after=1)
    assert paused["state"] == "paused"
    assert [item["state"] for item in paused["jobs"]] == ["completed", "pending"]
    first_hash = paused["jobs"][0]["output_sha256"]
    first_attempts = paused["jobs"][0]["attempts"]

    second = LongRenderAcceptance(
        contract,
        allow_rehearsal_target=True,
        allow_soft_limits=True,
        executor=_executor,
    )
    resumed = second.prepare(resume=True)
    assert resumed["resume_count"] == 1
    completed = second.run()

    assert completed["state"] == "completed"
    assert completed["terminal_event"] == "run_completed"
    assert completed["jobs"][0]["output_sha256"] == first_hash
    assert completed["jobs"][0]["attempts"] == first_attempts
    assert completed["jobs"][1]["attempts"] == 1
    assert (contract.state_file.parent / "final-report.json").is_file()
    assert not any(_reservation_path(target / item.output_name).exists() for item in contract.jobs)


def test_resume_blocks_changed_original_media(tmp_path: Path, monkeypatch) -> None:
    _install_fakes(monkeypatch)
    target = tmp_path / "target"
    contract_path = _write_contract(tmp_path, target=target)
    contract = load_contract(contract_path)
    first = LongRenderAcceptance(
        contract,
        allow_rehearsal_target=True,
        allow_soft_limits=True,
        executor=_executor,
    )
    first.prepare(resume=False)
    assert first.run(checkpoint_stop_after=1)["state"] == "paused"

    contract.jobs[1].audio.write_bytes(b"changed")
    second = LongRenderAcceptance(
        contract,
        allow_rehearsal_target=True,
        allow_soft_limits=True,
        executor=_executor,
    )
    with pytest.raises(LongRenderContractError, match="verändert"):
        second.prepare(resume=True)


def test_resume_blocks_modified_contract(tmp_path: Path, monkeypatch) -> None:
    _install_fakes(monkeypatch)
    target = tmp_path / "target"
    contract_path = _write_contract(tmp_path, target=target)
    contract = load_contract(contract_path)
    first = LongRenderAcceptance(
        contract,
        allow_rehearsal_target=True,
        allow_soft_limits=True,
        executor=_executor,
    )
    first.prepare(resume=False)
    assert first.run(checkpoint_stop_after=1)["state"] == "paused"

    payload = json.loads(contract_path.read_text(encoding="utf-8"))
    payload["limits"]["cpu_percent"] = 40
    contract_path.write_text(json.dumps(payload), encoding="utf-8")
    changed = load_contract(contract_path)
    second = LongRenderAcceptance(
        changed,
        allow_rehearsal_target=True,
        allow_soft_limits=True,
        executor=_executor,
    )
    with pytest.raises(LongRenderContractError, match="Vertrag wurde"):
        second.prepare(resume=True)


def test_new_run_never_moves_or_overwrites_existing_output(tmp_path: Path, monkeypatch) -> None:
    _install_fakes(monkeypatch)
    target = tmp_path / "target"
    contract_path = _write_contract(tmp_path, target=target, jobs=1)
    contract = load_contract(contract_path)
    target.mkdir(parents=True)
    output = target / contract.jobs[0].output_name
    output.write_bytes(b"existing-user-output")

    controller = LongRenderAcceptance(
        contract,
        allow_rehearsal_target=True,
        allow_soft_limits=True,
        executor=_executor,
    )
    with pytest.raises(LongRenderContractError, match="nichts wird überschrieben"):
        controller.prepare(resume=False)
    assert output.read_bytes() == b"existing-user-output"
