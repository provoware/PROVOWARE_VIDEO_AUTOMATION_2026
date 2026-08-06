from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


def load_validator():
    path = Path(__file__).resolve().parents[1] / "scripts" / "validate_documentation.py"
    spec = importlib.util.spec_from_file_location("validate_documentation", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_github_slug_is_deterministic() -> None:
    module = load_validator()
    assert module.github_slug("Schritt 1: Erstes Video") == "schritt-1-erstes-video"
    assert module.github_slug("„Ich möchte …“") == "ich-möchte"


def test_duplicate_heading_detection_uses_anchor_collisions(tmp_path: Path) -> None:
    module = load_validator()
    sample = tmp_path / "sample.md"
    sample.write_text("# Titel\n\n## Prüfung!\n\n## Prüfung\n", encoding="utf-8")
    found = module.headings(sample)
    assert found[1][2] == found[2][2] == "prüfung"


def test_relative_link_validation(tmp_path: Path) -> None:
    module = load_validator()
    source = tmp_path / "source.md"
    target = tmp_path / "target.md"
    source.write_text("# Quelle\n", encoding="utf-8")
    target.write_text("# Ziel\n\n## Abschnitt\n", encoding="utf-8")
    original_root = module.ROOT
    try:
        module.ROOT = tmp_path
        cache = {}
        assert module.validate_link(source, "target.md#abschnitt", cache) is None
        assert "fehlt" in str(module.validate_link(source, "target.md#unbekannt", cache))
        assert "fehlt" in str(module.validate_link(source, "missing.md", cache))
    finally:
        module.ROOT = original_root


def test_classification_schema_is_complete_and_unique() -> None:
    root = Path(__file__).resolve().parents[1]
    value = json.loads((root / "docs" / "DOCUMENTATION_CLASSIFICATION.json").read_text(encoding="utf-8"))
    documents = value["documents"]
    assert len(documents) == len(set(documents))
    assert all(entry["category"] in {"active", "technical", "historical", "internal"} for entry in documents.values())
    assert all(entry.get("required_sections") for entry in documents.values() if entry["category"] == "active")


def test_intent_help_is_safe_and_complete() -> None:
    root = Path(__file__).resolve().parents[1]
    source = (root / "src" / "videobatch_fast" / "canonical_shell_workspace.py").read_text(encoding="utf-8")
    for label in (
        "Ich möchte …",
        "Erstes Video erstellen",
        "Fehlende Datei beheben",
        "Queuefehler wiederholen",
        "Cache leeren",
        "Update rückgängig machen",
    ):
        assert label in source
    assert "keine Produktion, Löschung oder Aktualisierung automatisch gestartet" in source
    assert "self._start(" not in source[source.index("def _build_canonical_help_page"):source.index("def _restore_shell_selection")]
