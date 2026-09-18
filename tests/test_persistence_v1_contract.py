from __future__ import annotations

import json
import stat
import sys
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from videobatch_fast.archive_service import recover_archive_transactions  # noqa: E402
from videobatch_fast.job_journal import SCHEMA_VERSION, recoverable_batches  # noqa: E402
from videobatch_fast.plugin_approvals import load_approvals  # noqa: E402
from videobatch_fast.safe_io import atomic_write_json, quarantine_file, read_json  # noqa: E402


INVENTORY = ROOT / "diagnostics" / "architecture" / "CP-04_PERSISTENCE_INVENTORY.json"
EXPECTED_DURABLE_STORES = {
    "project_state",
    "config",
    "retry_queue",
    "job_journal",
    "archive_transactions",
    "plugin_approvals",
}


def _inventory() -> dict[str, object]:
    payload = json.loads(INVENTORY.read_text(encoding="utf-8"))
    assert payload["checkpoint"] == "CP-04"
    assert payload["mode"] == "inventory_only"
    return payload


def test_persistence_inventory_covers_every_current_durable_store() -> None:
    payload = _inventory()
    stores = payload["durable_product_stores"]
    assert isinstance(stores, list)

    ids = {str(item["id"]) for item in stores if isinstance(item, dict)}
    assert ids == EXPECTED_DURABLE_STORES


def test_every_inventoried_durable_store_stays_on_atomic_json_boundary() -> None:
    payload = _inventory()
    stores = payload["durable_product_stores"]
    assert isinstance(stores, list)

    for item in stores:
        assert isinstance(item, dict)
        relative = str(item["module"])
        source = (ROOT / relative).read_text(encoding="utf-8")
        assert "atomic_write_json" in source, f"{relative} verlässt die kanonische Atomic-JSON-Grenze."
        assert "sqlite3" not in source, f"{relative} führt unerlaubt eine parallele SQLite-Persistenz ein."


def test_sqlite_remains_deferred_without_proven_requirement() -> None:
    payload = _inventory()
    sqlite = payload["sqlite"]
    assert isinstance(sqlite, dict)
    assert sqlite["status"] == "deferred_not_required"
    assert "Do not introduce SQLite" in str(sqlite["rule"])


def test_project_state_inventory_includes_user_selected_paths() -> None:
    payload = _inventory()
    stores = payload["durable_product_stores"]
    project = next(item for item in stores if isinstance(item, dict) and item.get("id") == "project_state")
    assert "user-selected" in str(project["path"])
    assert "explicit user-selected project file path" in str(project["path_boundary"])


def test_cp04_inventory_preserves_historical_job_journal_schema_finding() -> None:
    payload = _inventory()
    stores = payload["durable_product_stores"]
    journal = next(item for item in stores if isinstance(item, dict) and item.get("id") == "job_journal")
    limitation = str(journal.get("known_limitation", ""))
    assert "without a schema-version gate" in limitation
    assert "future integrity checkpoint" in limitation


def test_atomic_json_round_trip_is_private_and_complete(tmp_path: Path) -> None:
    target = tmp_path / "state.json"
    payload = {"schema_version": 7, "name": "Prüfung", "items": [1, 2, 3]}

    written = atomic_write_json(target, payload)

    assert written == target
    assert read_json(target) == payload
    assert stat.S_IMODE(target.stat().st_mode) == 0o600
    assert not list(tmp_path.glob(".state.json.*.tmp"))


def test_quarantine_preserves_corrupt_bytes_without_overwrite(tmp_path: Path) -> None:
    target = tmp_path / "config.json"
    raw = b"{broken-json"
    target.write_bytes(raw)

    quarantined = quarantine_file(target, label="corrupt")

    assert quarantined is not None
    assert not target.exists()
    assert quarantined.is_file()
    assert quarantined.read_bytes() == raw
    assert ".corrupt." in quarantined.name


def test_plugin_approval_corruption_is_quarantined_and_recreated_safely(tmp_path: Path) -> None:
    target = tmp_path / "plugin_approvals.json"
    target.write_text("{broken-json", encoding="utf-8")

    recovered = load_approvals(target)

    assert recovered["schema_version"] == 1
    assert recovered["approvals"] == {}
    assert target.is_file()
    assert read_json(target)["approvals"] == {}
    quarantined = list(tmp_path.glob("plugin_approvals.corrupt.*.json"))
    assert len(quarantined) == 1


def test_invalid_archive_transaction_is_reported_without_destructive_cleanup(tmp_path: Path) -> None:
    project = tmp_path / "project"
    transactions = project / "Verwendet" / ".transactions"
    transactions.mkdir(parents=True)
    journal = transactions / "broken.json"
    journal.write_text("{broken-json", encoding="utf-8")

    result = recover_archive_transactions(project)

    assert result == [
        {
            "journal": str(journal),
            "status": "invalid",
            "message": "Journal nicht lesbar.",
        }
    ]
    assert journal.is_file()
    assert journal.read_text(encoding="utf-8") == "{broken-json"

def test_recoverable_batches_accepts_schema_2_without_modifying_journal(tmp_path: Path) -> None:
    state = tmp_path / "state"
    journal = state / "jobs" / "active" / "valid.json"
    atomic_write_json(
        journal,
        {
            "schema_version": SCHEMA_VERSION,
            "operation_id": "valid",
            "state": "running",
            "jobs": [{"index": 1, "state": "pending"}],
            "options": {},
        },
    )
    before = journal.read_bytes(), journal.stat().st_mtime_ns

    with patch("videobatch_fast.job_journal.state_dir", return_value=state):
        recovered = recoverable_batches()

    assert len(recovered) == 1
    assert recovered[0]["schema_version"] == SCHEMA_VERSION
    assert recovered[0]["operation_id"] == "valid"
    assert recovered[0]["recoverable_jobs"] == 1
    assert recovered[0]["journal_path"] == str(journal)
    assert journal.read_bytes() == before[0]
    assert journal.stat().st_mtime_ns == before[1]


def test_recoverable_batches_rejects_missing_invalid_old_and_future_schemas(tmp_path: Path) -> None:
    state = tmp_path / "state"
    active = state / "jobs" / "active"
    payloads = {
        "missing.json": {
            "operation_id": "missing",
            "state": "running",
            "jobs": [{"index": 1, "state": "pending"}],
        },
        "string.json": {
            "schema_version": str(SCHEMA_VERSION),
            "operation_id": "string",
            "state": "running",
            "jobs": [{"index": 1, "state": "pending"}],
        },
        "old.json": {
            "schema_version": SCHEMA_VERSION - 1,
            "operation_id": "old",
            "state": "running",
            "jobs": [{"index": 1, "state": "pending"}],
        },
        "future.json": {
            "schema_version": SCHEMA_VERSION + 1,
            "operation_id": "future",
            "state": "running",
            "jobs": [{"index": 1, "state": "pending"}],
        },
    }
    before: dict[Path, tuple[bytes, int]] = {}
    for name, payload in payloads.items():
        path = active / name
        atomic_write_json(path, payload)
        before[path] = (path.read_bytes(), path.stat().st_mtime_ns)

    with patch("videobatch_fast.job_journal.state_dir", return_value=state):
        recovered = recoverable_batches()

    assert recovered == []
    for path, (content, mtime) in before.items():
        assert path.is_file()
        assert path.read_bytes() == content
        assert path.stat().st_mtime_ns == mtime


def test_recoverable_batches_leaves_corrupt_journal_untouched(tmp_path: Path) -> None:
    state = tmp_path / "state"
    journal = state / "jobs" / "active" / "corrupt.json"
    journal.parent.mkdir(parents=True)
    journal.write_bytes(b"{broken-json")
    before = journal.read_bytes(), journal.stat().st_mtime_ns

    with patch("videobatch_fast.job_journal.state_dir", return_value=state):
        recovered = recoverable_batches()

    assert recovered == []
    assert journal.is_file()
    assert journal.read_bytes() == before[0]
    assert journal.stat().st_mtime_ns == before[1]

