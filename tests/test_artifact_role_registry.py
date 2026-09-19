from __future__ import annotations

import json
from pathlib import Path

from videobatch_fast.registry import REQUIRED_REGISTRIES

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "registries" / "ARTIFACT_ROLE_REGISTRY.json"


def _registry() -> dict[str, object]:
    payload = json.loads(REGISTRY.read_text(encoding="utf-8"))
    assert payload["schema_version"] == 1
    assert payload["contract_version"] == "artifact-role-1"
    return payload


def _inventory_expression(path: str) -> str:
    parts = Path(path).parts
    return "ROOT" + "".join(f' / "{part}"' for part in parts)


def test_active_contract_artifacts_exist_and_have_consumers() -> None:
    payload = _registry()
    artifacts = payload["artifacts"]
    assert isinstance(artifacts, list)
    assert artifacts

    paths: set[str] = set()
    for item in artifacts:
        assert isinstance(item, dict)
        path = str(item["path"])
        assert path not in paths
        paths.add(path)

        assert item["role"] == "active_contract_source"
        assert item["status"] == "active"
        assert item["release_included"] is False
        assert item["relocation_policy"] == "update_registry_and_all_consumers_same_change"
        assert item["deletion_policy"] == "forbidden_while_active"
        assert (ROOT / path).is_file()

        consumers = item["consumers"]
        assert isinstance(consumers, list)
        assert consumers
        for consumer in consumers:
            consumer_path = ROOT / str(consumer)
            assert consumer_path.is_file()
            source = consumer_path.read_text(encoding="utf-8")
            assert _inventory_expression(path) in source


def test_known_architecture_inventories_are_explicitly_protected() -> None:
    payload = _registry()
    paths = {
        str(item["path"])
        for item in payload["artifacts"]
        if isinstance(item, dict)
    }
    assert paths == {
        "docs/archive/diagnostics-checkpoints/architecture/CP-04_PERSISTENCE_INVENTORY.json",
        "docs/archive/diagnostics-checkpoints/architecture/CP-07_FFMPEG_INVENTORY.json",
    }


def test_artifact_role_registry_uses_shared_strict_registry_validation() -> None:
    assert "registries/ARTIFACT_ROLE_REGISTRY.json" in REQUIRED_REGISTRIES
