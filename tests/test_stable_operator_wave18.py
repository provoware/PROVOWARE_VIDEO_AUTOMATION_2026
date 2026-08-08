from __future__ import annotations

import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import stable_operator_common as common  # noqa: E402


def _identity_root(tmp_path: Path) -> Path:
    root = tmp_path / "candidate"
    (root / "src").mkdir(parents=True)
    (root / "scripts").mkdir()
    (root / "src/app.py").write_text("VALUE=1\n", encoding="utf-8")
    (root / "STABLE_OPERATOR_CONTRACT.json").write_text(
        json.dumps({
            "schema_version": 1,
            "phases": ["toolchain", "quality", "desktop_x11", "long_render", "promotion_rehearsal"],
        }),
        encoding="utf-8",
    )
    files = []
    for rel in ("src/app.py", "STABLE_OPERATOR_CONTRACT.json"):
        path = root / rel
        import hashlib
        data = path.read_bytes()
        files.append({"path": rel, "size": len(data), "sha256": hashlib.sha256(data).hexdigest(), "mode": "0o644"})
    (root / "RELEASE_MANIFEST.json").write_text(
        json.dumps({"build": "2.8.3-rc24", "files": files}), encoding="utf-8"
    )
    return root


def test_operator_contract_orders_real_stable_gates() -> None:
    contract = json.loads((ROOT / "STABLE_OPERATOR_CONTRACT.json").read_text(encoding="utf-8"))
    assert contract["phases"] == [
        "toolchain", "quality", "desktop_x11", "long_render", "promotion_rehearsal"
    ]
    assert contract["quality_tools"] == {
        "ruff": "0.16.1", "mypy": "2.3.0", "bandit": "1.9.4", "pip-audit": "2.10.1"
    }
    assert contract["long_render"]["jobs"] == 96
    assert contract["desktop"]["profiles_per_session"] == 9


def test_operator_session_is_candidate_bound_and_stale_after_source_change(tmp_path: Path) -> None:
    root = _identity_root(tmp_path)
    session_dir = tmp_path / "session"
    session = common.init_session(session_dir, root=root)
    assert session["candidate_identity"]["candidate_id"] == "2.8.3-rc24"
    (root / "src/app.py").write_text("VALUE=2\n", encoding="utf-8")
    with pytest.raises(Exception, match="stale|veraltet"):
        common.load_session(session_dir, root=root)


def test_operator_refuses_out_of_order_phase(tmp_path: Path) -> None:
    root = _identity_root(tmp_path)
    session_dir = tmp_path / "session"
    session = common.init_session(session_dir, root=root)
    contract = common.load_contract(root)
    with pytest.raises(common.OperatorBlocked, match="toolchain"):
        common.require_previous(session, "quality", contract)


def test_operator_phase_record_requires_previous_and_hashes_artifact(tmp_path: Path) -> None:
    root = _identity_root(tmp_path)
    session_dir = tmp_path / "session"
    common.init_session(session_dir, root=root)
    artifact = tmp_path / "wheelhouse.json"
    artifact.write_text("{}\n", encoding="utf-8")
    session = common.record_phase(session_dir, "toolchain", [artifact], root=root)
    record = session["phases"][0]
    assert record["phase"] == "toolchain"
    assert len(record["artifacts"][0]["sha256"]) == 64


def test_external_quality_gate_is_forced_offline() -> None:
    source = (ROOT / "scripts/toolchain.py").read_text(encoding="utf-8")
    assert '[str(python), str(runner), "--mode", "required", "--offline"]' in source


def test_operator_desktop_phase_requires_explicit_real_session() -> None:
    source = (ROOT / "scripts/stable_operator.py").read_text(encoding="utf-8")
    assert 'actual != expected_session' in source
    assert 'VIDEOBATCH_PHYSICAL_ACCEPTANCE' in source
    assert 'desktop_x11' in (ROOT / "STABLE_OPERATOR_CONTRACT.json").read_text(encoding="utf-8")
    assert 'desktop_wayland' not in (ROOT / "STABLE_OPERATOR_CONTRACT.json").read_text(encoding="utf-8")


def test_promotion_rehearsal_consumes_both_quality_and_physical_evidence() -> None:
    source = (ROOT / "scripts/stable_operator.py").read_text(encoding="utf-8")
    assert 'quality_evidence.verify_index(quality_dir)' in source
    assert 'validate_evidence(' in source
    assert 'first.read_bytes() != second.read_bytes()' in source
    assert 'Rehearsal only: kein Stable-Artefakt wurde veröffentlicht.' in source


def test_operator_kit_is_deterministic_by_contract() -> None:
    source = (ROOT / "scripts/build_stable_operator_kit.py").read_text(encoding="utf-8")
    assert 'FIXED = (2026, 1, 1, 0, 0, 0)' in source
    assert 'CANDIDATE_IDENTITY.json' in source
    assert 'candidate/RELEASE_MANIFEST.json' in source


def test_operator_freezes_pip_audit_advisory_cache_before_offline_quality() -> None:
    source = (ROOT / "scripts/stable_operator.py").read_text(encoding="utf-8")
    assert 'pip-audit-cache' in source
    assert '"-m", "pip_audit"' in source
    assert '"VIDEOBATCH_PIP_AUDIT_CACHE"' in source
    contract = json.loads((ROOT / "STABLE_OPERATOR_CONTRACT.json").read_text(encoding="utf-8"))
    assert contract["wheelhouse"]["pip_audit_advisory_cache_required"] is True
    assert contract["wheelhouse"]["pip_audit_final_gate_offline"] is True


def test_operator_session_rejects_tampered_recorded_artifact(tmp_path: Path) -> None:
    root = _identity_root(tmp_path)
    session_dir = tmp_path / "session"
    common.init_session(session_dir, root=root)
    artifact = tmp_path / "evidence.json"
    artifact.write_text("{}\n", encoding="utf-8")
    common.record_phase(session_dir, "toolchain", [artifact], root=root)
    artifact.write_text('{"tampered":true}\n', encoding="utf-8")
    with pytest.raises(common.OperatorBlocked, match="verändert"):
        common.load_session(session_dir, root=root)


def test_operator_preserves_raw_physical_evidence_artifacts() -> None:
    source = (ROOT / "scripts/stable_operator.py").read_text(encoding="utf-8")
    assert 'raw_report = raw_dir / "AUTOMATED_DESKTOP_APPROVAL.json"' in source
    assert 'raw_screenshot = raw_dir / "live_desktop_approval.png"' in source
    assert '[evidence, raw_report, raw_screenshot]' in source
    assert 'final_report = loaded.state_file.parent / "final-report.json"' in source
    assert '[evidence, contract_path.resolve(strict=True), final_report]' in source


def test_operator_kit_output_mode_is_portable_readable() -> None:
    source = (ROOT / "scripts/build_stable_operator_kit.py").read_text(encoding="utf-8")
    assert 'os.chmod(output, 0o644)' in source
