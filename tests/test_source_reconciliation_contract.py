from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[1]


def load_validator() -> ModuleType:
    path = ROOT / "scripts" / "validate_source_reconciliation.py"
    spec = importlib.util.spec_from_file_location("validate_source_reconciliation", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Validator kann nicht geladen werden: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def write_contract(root: Path) -> Path:
    contract = {
        "required_q1_16_source": {
            "required_file": "src/videobatch_fast/output_safety.py",
            "required_symbols": [
                "OutputLeaseTransaction",
                "AtomicOutputTransaction",
                "OutputLeaseTransitionError",
                "estimate_encoded_output_bytes",
                "calculate_output_space_budget",
            ],
            "required_stages": [
                "RESERVED",
                "PREFLIGHTED",
                "TEMP_CREATED",
                "WRITTEN",
                "FILE_SYNCED",
                "DEVICE_RECHECKED",
                "REPLACED",
                "DIRECTORY_SYNCED",
                "RELEASED",
            ],
        },
        "policy": {
            "fail_closed": True,
            "q1_17_allowed_only_when_reconciled": True,
        },
    }
    path = root / "contract.json"
    path.write_text(json.dumps(contract), encoding="utf-8")
    return path


def test_missing_q1_16_source_blocks() -> None:
    module = load_validator()
    with tempfile.TemporaryDirectory(prefix="videobatch-reconcile-") as directory:
        root = Path(directory)
        contract = write_contract(root)
        result = module.evaluate(root, contract)
    assert result.status == "BLOCKED"
    assert any("Quelldatei fehlt" in finding for finding in result.findings)


def test_complete_q1_16_contract_reconciles() -> None:
    module = load_validator()
    with tempfile.TemporaryDirectory(prefix="videobatch-reconcile-") as directory:
        root = Path(directory)
        contract = write_contract(root)
        source = root / "src" / "videobatch_fast" / "output_safety.py"
        source.parent.mkdir(parents=True)
        payload = "\n".join(
            [
                "OutputLeaseTransaction",
                "AtomicOutputTransaction",
                "OutputLeaseTransitionError",
                "estimate_encoded_output_bytes",
                "calculate_output_space_budget",
                "RESERVED",
                "PREFLIGHTED",
                "TEMP_CREATED",
                "WRITTEN",
                "FILE_SYNCED",
                "DEVICE_RECHECKED",
                "REPLACED",
                "DIRECTORY_SYNCED",
                "RELEASED",
            ]
        )
        source.write_text(payload, encoding="utf-8")
        result = module.evaluate(root, contract)
    assert result.status == "RECONCILED"
    assert result.findings == ()


def test_partial_q1_16_source_blocks_without_fallback() -> None:
    module = load_validator()
    with tempfile.TemporaryDirectory(prefix="videobatch-reconcile-") as directory:
        root = Path(directory)
        contract = write_contract(root)
        source = root / "src" / "videobatch_fast" / "output_safety.py"
        source.parent.mkdir(parents=True)
        source.write_text("OutputLeaseTransaction\nRESERVED\n", encoding="utf-8")
        result = module.evaluate(root, contract)
    assert result.status == "BLOCKED"
    assert any("Symbol fehlt" in finding for finding in result.findings)
    assert any("Stage fehlt" in finding for finding in result.findings)


def test_repository_contract_records_exact_q1_16_provenance() -> None:
    value = json.loads((ROOT / "SOURCE_RECONCILIATION_CONTRACT.json").read_text(encoding="utf-8"))
    required = value["required_q1_16_source"]
    assert required["archive_sha256"] == (
        "ae33da8a0130ea0b3d22799c3d7977a16bac98c36f4bcedfdafc4b82d19a217b"
    )
    assert value["github_baseline"]["startup_safe_mode_head"] == (
        "0af1eac84fc6715b96bfed7dd69d61622efd6176"
    )
    assert value["policy"]["fail_closed"] is True
    assert value["policy"]["runner_integration_allowed"] is False
    assert value["policy"]["q2_allowed"] is False


def test_current_branch_correctly_reports_blocked_until_q1_16_is_imported() -> None:
    module = load_validator()
    result = module.evaluate(ROOT, ROOT / "SOURCE_RECONCILIATION_CONTRACT.json")
    assert result.status == "BLOCKED"
    assert any("output_safety.py" in finding for finding in result.findings)
