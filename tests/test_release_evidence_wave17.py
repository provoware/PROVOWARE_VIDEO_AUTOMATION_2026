from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import zipfile

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import quality_evidence  # noqa: E402
import release_identity  # noqa: E402
import toolchain_common  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def _record(root: Path, relative: str) -> dict[str, object]:
    path = root / relative
    data = path.read_bytes()
    return {
        "path": relative,
        "size": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "mode": oct(path.stat().st_mode & 0o777),
    }


def _identity_root(tmp_path: Path) -> Path:
    root = tmp_path / "project"
    (root / "src").mkdir(parents=True)
    (root / "scripts").mkdir()
    (root / "src/app.py").write_text("VALUE = 1\n", encoding="utf-8")
    (root / "scripts/run.py").write_text("print('ok')\n", encoding="utf-8")
    (root / "README.md").write_text("docs\n", encoding="utf-8")
    records = [_record(root, item) for item in ("README.md", "scripts/run.py", "src/app.py")]
    (root / "RELEASE_MANIFEST.json").write_text(
        json.dumps({"build": "2.8.3-rc24", "files": records}), encoding="utf-8"
    )
    return root


def test_release_identity_binds_manifest_and_execution_source(tmp_path: Path) -> None:
    root = _identity_root(tmp_path)
    first = release_identity.release_identity(root)
    assert first["candidate_id"] == "2.8.3-rc24"
    assert first["source_file_count"] == 2
    assert len(first["manifest_sha256"]) == 64
    assert len(first["source_sha256"]) == 64
    (root / "src/app.py").write_text("VALUE = 2\n", encoding="utf-8")
    with pytest.raises(release_identity.ReleaseIdentityError, match="veraltet"):
        release_identity.release_identity(root)


def _passing_report(identity: dict[str, object]) -> dict[str, object]:
    return {
        "schema_version": 4,
        "offline": True,
        "candidate_identity": identity,
        "results": [
            {
                "tool": name,
                "version": version,
                "status": "pass",
                "returncode": 0,
                "offline_guard": True,
            }
            for name, version in quality_evidence.REQUIRED_TOOLS.items()
        ],
    }


def test_quality_evidence_rejects_stale_source_and_tampering(tmp_path: Path) -> None:
    root = _identity_root(tmp_path)
    evidence = tmp_path / "evidence"
    diagnostics = evidence / "diagnostics"
    diagnostics.mkdir(parents=True)
    report = diagnostics / "external_quality_latest.json"
    report.write_text(json.dumps(_passing_report(release_identity.release_identity(root))), encoding="utf-8")
    (evidence / "installed-versions.json").write_text("{}\n", encoding="utf-8")
    index = quality_evidence.build_index(evidence, root=root)
    quality_evidence.write_index(evidence, index)
    quality_evidence.verify_index(evidence, root=root)
    (evidence / "installed-versions.json").write_text('{"changed":true}\n', encoding="utf-8")
    with pytest.raises(quality_evidence.QualityEvidenceError, match="verändert"):
        quality_evidence.verify_index(evidence, root=root)


def test_quality_evidence_bundle_is_byte_reproducible(tmp_path: Path) -> None:
    root = _identity_root(tmp_path)
    evidence = tmp_path / "evidence"
    diagnostics = evidence / "diagnostics"
    diagnostics.mkdir(parents=True)
    (diagnostics / "external_quality_latest.json").write_text(
        json.dumps(_passing_report(release_identity.release_identity(root))), encoding="utf-8"
    )
    (evidence / "log.txt").write_text("deterministic\n", encoding="utf-8")
    quality_evidence.write_index(evidence, quality_evidence.build_index(evidence, root=root))
    first, second = tmp_path / "a.zip", tmp_path / "b.zip"
    quality_evidence.build_zip(evidence, first, root=root)
    quality_evidence.build_zip(evidence, second, root=root)
    assert first.read_bytes() == second.read_bytes()


def _minimal_wheel(path: Path, name: str, version: str) -> None:
    normalized = name.replace("-", "_")
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(f"{normalized}-{version}.dist-info/METADATA", f"Name: {name}\nVersion: {version}\n")
        archive.writestr(f"{normalized}-{version}.dist-info/WHEEL", "Wheel-Version: 1.0\nTag: py3-none-any\n")


def test_wheelhouse_manifest_binds_lock_contract_and_canonical_wheel_list(tmp_path: Path) -> None:
    root = tmp_path / "project"
    root.mkdir()
    (root / "VERSION.json").write_text('{"build":"2.8.3-rc24"}', encoding="utf-8")
    (root / "requirements-toolchain.lock").write_text("demo==1.0\n", encoding="utf-8")
    (root / "TOOLCHAIN_CONTRACT.json").write_text("{}\n", encoding="utf-8")
    wheelhouse = root / "wheelhouse"
    wheelhouse.mkdir()
    _minimal_wheel(wheelhouse / "demo-1.0-py3-none-any.whl", "demo", "1.0")
    manifest = toolchain_common.build_manifest(wheelhouse, root=root)
    assert manifest["schema_version"] == 2
    assert len(manifest["requirements_toolchain_sha256"]) == 64
    assert len(manifest["toolchain_contract_sha256"]) == 64
    assert len(manifest["wheels_sha256"]) == 64
    manifest["wheels"][0]["size"] += 1
    _ids, _declared, errors = toolchain_common._verify_wheel_items(wheelhouse, manifest)
    assert any("Gesamt-Hash" in item for item in errors)


def test_offline_install_explicitly_forbids_sdists() -> None:
    text = (ROOT / "scripts/toolchain.py").read_text(encoding="utf-8")
    assert '"--only-binary=:all:"' in text
    assert '"--require-hashes"' in text
    assert '"--no-index"' in text


def test_stable_release_and_finalizer_bind_source_hash() -> None:
    stable = (ROOT / "stable_release.sh").read_text(encoding="utf-8")
    finalizer = (ROOT / "scripts/finalize_release.py").read_text(encoding="utf-8")
    assert "VIDEOBATCH_ACCEPTANCE_SOURCE_SHA256" in stable
    assert "--source-sha256" in stable
    assert "candidate_source_hash" in finalizer
    assert "VIDEOBATCH_ACCEPTANCE_SOURCE_SHA256" in finalizer


def test_physical_harnesses_can_export_machine_bound_evidence() -> None:
    desktop = (ROOT / "scripts/live_desktop_gate.py").read_text(encoding="utf-8")
    long_render = (ROOT / "scripts/run_long_render_acceptance.py").read_text(encoding="utf-8")
    exporter = (ROOT / "scripts/export_stable_evidence.py").read_text(encoding="utf-8")
    assert "--evidence-dir" in desktop
    assert "--evidence-dir" in long_render
    assert '"source_sha256"' in exporter
    assert 'len(jobs) != 96' in exporter


def test_desktop_export_rejects_non_physical_report(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import export_stable_evidence as exporter
    from videobatch_fast.automated_desktop_approval import AutomatedDesktopApprovalCheck

    monkeypatch.setattr(exporter, "ROOT", tmp_path)
    monkeypatch.setattr(
        exporter,
        "verify_automated_desktop_approval",
        lambda _root: AutomatedDesktopApprovalCheck(True, "valid", "ok", "2026-08-07T12:00:00Z", "x11"),
    )
    monkeypatch.setenv("XDG_CURRENT_DESKTOP", "KDE")
    monkeypatch.setenv("DISPLAY", ":0")
    (tmp_path / "AUTOMATED_DESKTOP_APPROVAL.json").write_text(
        json.dumps({"physical_acceptance": False, "scaling_profiles": [{"passed": True}] * 9}),
        encoding="utf-8",
    )
    with pytest.raises(RuntimeError, match="physischem Abnahmemodus"):
        exporter.export_desktop(tmp_path / "evidence.json")


def test_long_render_export_rejects_non_physical_target(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import export_stable_evidence as exporter

    monkeypatch.setattr(exporter, "ROOT", tmp_path)
    jobs = [{"state": "completed", "output_sha256": "a" * 64} for _ in range(96)]
    outputs = [{"sha256": "b" * 64} for _ in range(96)]
    report = {
        "status": "completed",
        "rehearsal_only": False,
        "jobs": jobs,
        "output_manifest": {"entries": outputs, "digest": "c" * 64},
        "target": {
            "external_usb": False,
            "rehearsal_target": False,
            "filesystem": "ext4",
            "source": "/dev/sdz1",
            "mount_options": ["rw"],
            "write_mib_s": 20.0,
            "free_gib": 600.0,
            "filesystem_uuid": "uuid",
        },
    }
    path = tmp_path / "final-report.json"
    path.write_text(json.dumps(report), encoding="utf-8")
    with pytest.raises(RuntimeError, match="Slow-USB"):
        exporter.export_long_render(path, tmp_path / "long_render.json")
