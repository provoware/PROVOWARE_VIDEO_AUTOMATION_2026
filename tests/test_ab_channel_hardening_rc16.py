from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import sys
import tarfile
from copy import deepcopy
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import ab_contract  # noqa: E402
import ab_installer  # noqa: E402
import ab_launcher  # noqa: E402


def record(path: Path, root: Path) -> dict[str, object]:
    return {
        "path": path.relative_to(root).as_posix(),
        "size": path.stat().st_size,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "mode": oct(path.stat().st_mode & 0o777),
    }


def tree_hash(records: list[dict[str, object]]) -> str:
    digest = hashlib.sha256()
    for item in sorted(records, key=lambda value: str(value["path"])):
        digest.update(f"{item['path']}\0{item['mode']}\0{item['size']}\0{item['sha256']}\n".encode())
    return digest.hexdigest()


def fake_manifest(slot: Path, version: str, sequence: int, release_id: str) -> dict:
    app = slot / "AppRun"
    app.write_text(
        "#!/usr/bin/env bash\n"
        "case \"${1:-}\" in\n"
        " --portable-verify) echo PORTABLE_VERIFY_OK;;\n"
        " --portable-smoke-test) echo PORTABLE_RUNTIME_OK;;\n"
        "esac\nexit 0\n",
        encoding="utf-8",
    )
    app.chmod(0o755)
    bootstrap = [record(app, slot)]
    components = {}
    for component_id, install_path in (
        ("bootstrap", "."),
        ("runtime", "usr/runtime"),
        ("media", "usr/media"),
        ("application", "usr/app"),
        ("desktop", "usr/share"),
    ):
        records = bootstrap if component_id == "bootstrap" else []
        components[component_id] = {
            "version": version,
            "tree_sha256": tree_hash(records),
            "file_count": len(records),
            "files": records,
            "install_path": install_path,
            "included": True,
        }
    public_key = ROOT / "resources/signing/release-public-key.pem"
    return {
        "schema_version": 2,
        "product": "VideoBatch Fast",
        "version": version,
        "build": version,
        "release_sequence": sequence,
        "release_id": release_id,
        "signing_key_id": ab_contract.key_id(public_key),
        "created_utc": "2026-08-03T20:00:00Z",
        "maximum_part_bytes": 30 * 1024 * 1024,
        "part_count": 1,
        "total_file_count": 1,
        "total_unpacked_bytes": app.stat().st_size,
        "installation_layout": {"strategy": "ab-slots", "slots": ["A", "B"]},
        "update_order": list(ab_contract.COMPONENTS),
        "parts": [{
            "number": 1,
            "component": "bootstrap",
            "file": "part.tar.gz",
            "signature_file": "part.tar.gz.ed25519",
            "url": "parts/part.tar.gz",
            "signature_url": "parts/part.tar.gz.ed25519",
            "size": 1,
            "unpacked_bytes": app.stat().st_size,
            "member_count": 1,
            "sha256": "0" * 64,
        }],
        "components": components,
    }


def install_key(root: Path) -> None:
    target = root / "controller/current"
    target.mkdir(parents=True)
    (target / "VideoBatch_Release_Public_Key.pem").write_bytes((ROOT / "resources/signing/release-public-key.pem").read_bytes())


def test_manifest_contract_rejects_path_escape(tmp_path: Path) -> None:
    slot = tmp_path / "slot"
    slot.mkdir()
    manifest = fake_manifest(slot, "2.8.3-rc17", 16, "1" * 64)
    broken = deepcopy(manifest)
    broken["components"]["bootstrap"]["files"][0]["path"] = "../AppRun"
    with pytest.raises(ab_contract.ContractError):
        ab_contract.validate_manifest(broken, expected_key_id=manifest["signing_key_id"])


def test_manual_rollback_restores_complete_previous_state(tmp_path: Path) -> None:
    install_key(tmp_path)
    slot_a = tmp_path / "slots/A"
    slot_b = tmp_path / "slots/B"
    slot_a.mkdir(parents=True)
    slot_b.mkdir(parents=True)
    old_manifest = fake_manifest(slot_a, "2.8.3-rc15", 15, "a" * 64)
    new_manifest = fake_manifest(slot_b, "2.8.3-rc17", 16, "b" * 64)
    manifests = tmp_path / "slot_manifests"
    manifests.mkdir()
    (manifests / "A.json").write_text(json.dumps(old_manifest), encoding="utf-8")
    (manifests / "B.json").write_text(json.dumps(new_manifest), encoding="utf-8")
    (tmp_path / "current").symlink_to("slots/B")
    state = {
        "schema_version": 2,
        "version": "2.8.3-rc17",
        "release_sequence": 16,
        "release_id": "b" * 64,
        "active_slot": "B",
        "previous_slot": "A",
        "components": {name: {"tree_sha256": value["tree_sha256"]} for name, value in new_manifest["components"].items()},
        "history": [],
    }
    state_path = tmp_path / "installation_state.json"
    state_path.write_text(json.dumps(state), encoding="utf-8")
    assert ab_installer.rollback_confirmed_slot(tmp_path, state_path, tmp_path / "pending_transaction.json", state) == 0
    restored = json.loads(state_path.read_text())
    assert restored["version"] == "2.8.3-rc15"
    assert restored["release_sequence"] == 15
    assert restored["release_id"] == "a" * 64
    assert restored["active_slot"] == "A"
    assert ab_launcher.slot_from_current(tmp_path) == "A"


def test_verify_only_works_without_original_bundle(tmp_path: Path) -> None:
    install_key(tmp_path)
    slot = tmp_path / "slots/A"
    slot.mkdir(parents=True)
    manifest = fake_manifest(slot, "2.8.3-rc17", 16, "c" * 64)
    manifests = tmp_path / "slot_manifests"
    manifests.mkdir()
    (manifests / "A.json").write_text(json.dumps(manifest), encoding="utf-8")
    (tmp_path / "current").symlink_to("slots/A")
    state = {"active_slot": "A", "version": "2.8.3-rc17", "release_id": "c" * 64}
    assert ab_installer.verify_installed_without_source(tmp_path, state) == 0


def test_same_sequence_with_changed_release_identity_is_blocked() -> None:
    state = {"version": "2.8.3-rc17", "release_sequence": 16, "release_id": "a" * 64, "manifest_sha256": "c" * 64}
    manifest = {"version": "2.8.3-rc17", "release_sequence": 16, "release_id": "b" * 64}
    with pytest.raises(ab_installer.InstallError) as error:
        ab_installer.validate_release_progression(manifest, state, False, "d" * 64)
    assert error.value.code == 22


def test_archive_expansion_mismatch_is_blocked(tmp_path: Path) -> None:
    archive_path = tmp_path / "part.tar.gz"
    payload = tmp_path / "payload"
    payload.write_bytes(b"123456")
    with tarfile.open(archive_path, "w:gz") as archive:
        archive.add(payload, arcname="payload")
    target = tmp_path / "target"
    target.mkdir()
    with pytest.raises(ab_installer.InstallError):
        ab_installer.safe_extract(archive_path, target, {"member_count": 1, "unpacked_bytes": 5})


def test_channel_contract_requires_expiry_and_key_binding() -> None:
    public_key = ROOT / "resources/signing/release-public-key.pem"
    payload = {
        "schema_version": 1,
        "product": "VideoBatch Fast",
        "generation": 16,
        "created_utc": "2026-08-03T20:00:00Z",
        "expires_utc": "2026-11-01T20:45:00Z",
        "signing_key_id": ab_contract.key_id(public_key),
        "channels": {"stable": {"available": False}, "rc": {"available": False}},
    }
    ab_contract.validate_channel_index(payload, expected_key_id=payload["signing_key_id"])
    payload["signing_key_id"] = "falsch"
    with pytest.raises(ab_contract.ContractError):
        ab_contract.validate_channel_index(payload, expected_key_id=ab_contract.key_id(public_key))


def test_legacy_slot_snapshot_is_normalized_for_rollback(tmp_path: Path) -> None:
    slot = tmp_path / "slot"
    slot.mkdir()
    manifest = fake_manifest(slot, "2.8.3-rc15", 15, "d" * 64)
    for key in ("release_id", "signing_key_id", "total_file_count", "total_unpacked_bytes"):
        manifest.pop(key, None)
    for part in manifest["parts"]:
        part.pop("unpacked_bytes", None)
        part.pop("member_count", None)
    trusted = ab_contract.key_id(ROOT / "resources/signing/release-public-key.pem")
    normalized = ab_contract.validate_slot_snapshot(manifest, trusted_key_id=trusted)
    assert normalized["version"] == "2.8.3-rc15"
    assert normalized["release_id"]
    assert normalized["signing_key_id"] == trusted


def test_key_id_matches_release_artifact_convention() -> None:
    assert ab_contract.key_id(ROOT / "resources/signing/release-public-key.pem") == "6781ce300a9eccf9f5dd5da0"


def test_verify_only_is_resolved_before_online_source_loading() -> None:
    source = INSTALLER_PATH.read_text(encoding="utf-8") if (INSTALLER_PATH := ROOT / "scripts/ab_installer.py") else ""
    verify_position = source.index("if options.verify_only:")
    key_position = source.index("public_key = resolve_public_key")
    assert verify_position < key_position


def test_rc15_bridge_repairs_missing_contract_after_application_rollback(tmp_path: Path) -> None:
    import subprocess

    root = tmp_path / "install"
    slot_a = root / "slots/A"
    slot_b = root / "slots/B"
    slot_a.mkdir(parents=True)
    slot_b.mkdir(parents=True)
    old_manifest = fake_manifest(slot_a, "2.8.3-rc15", 15, "e" * 64)
    new_manifest = fake_manifest(slot_b, "2.8.3-rc17", 16, "f" * 64)

    contract_target = slot_b / "usr/app/scripts/ab_contract.py"
    contract_target.parent.mkdir(parents=True)
    contract_target.write_bytes((SCRIPTS / "ab_contract.py").read_bytes())
    contract_target.chmod(0o755)
    contract_entry = record(contract_target, slot_b)
    application = new_manifest["components"]["application"]
    application["files"] = [contract_entry]
    application["file_count"] = 1
    application["tree_sha256"] = tree_hash([contract_entry])
    new_manifest["total_file_count"] = 2
    new_manifest["total_unpacked_bytes"] += contract_target.stat().st_size

    manifests = root / "slot_manifests"
    manifests.mkdir()
    (manifests / "A.json").write_text(json.dumps(old_manifest), encoding="utf-8")
    (manifests / "B.json").write_text(json.dumps(new_manifest), encoding="utf-8")
    (root / "current").symlink_to("slots/A")
    (root / "installation_state.json").write_text(json.dumps({
        "schema_version": 2,
        "version": "2.8.3-rc15",
        "release_sequence": 15,
        "release_id": "e" * 64,
        "active_slot": "A",
        "previous_slot": "B",
        "components": {name: {"tree_sha256": value["tree_sha256"]} for name, value in old_manifest["components"].items()},
        "history": [],
    }), encoding="utf-8")

    controller = root / "controller/versions/2.8.3-rc17"
    controller.mkdir(parents=True)
    (controller / "ab_installer.py").write_bytes((SCRIPTS / "ab_installer.py").read_bytes())
    (controller / "ab_installer.py").chmod(0o755)
    (controller / "VideoBatch_Release_Public_Key.pem").write_bytes(
        (ROOT / "resources/signing/release-public-key.pem").read_bytes()
    )
    (root / "controller/current").symlink_to("versions/2.8.3-rc17")
    completed = subprocess.run([
        sys.executable, str(controller / "ab_installer.py"),
        "--bundle-root", str(controller),
        "--install-root", str(root),
        "--verify-only",
    ], text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
    assert completed.returncode == 0, completed.stdout
    assert "VERIFY_OK" in completed.stdout
    repaired = controller / "ab_contract.py"
    assert repaired.is_file() and not repaired.is_symlink()
    assert repaired.read_bytes() == contract_target.read_bytes()
