from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
from pathlib import Path
from types import ModuleType
from typing import Callable

ROOT = Path(__file__).resolve().parents[1]


def load_validator() -> ModuleType:
    path = ROOT / "scripts" / "validate_documentation.py"
    spec = importlib.util.spec_from_file_location("validate_documentation", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Dokumentationsvalidator kann nicht geladen werden: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_github_slug_is_deterministic() -> None:
    module = load_validator()
    assert module.github_slug("Schritt 1: Erstes Video") == "schritt-1-erstes-video"
    assert module.github_slug("„Ich möchte …“") == "ich-möchte"


def test_duplicate_heading_detection_uses_anchor_collisions() -> None:
    module = load_validator()
    with tempfile.TemporaryDirectory(prefix="videobatch-doc-heading-") as directory:
        sample = Path(directory) / "sample.md"
        sample.write_text("# Titel\n\n## Prüfung!\n\n## Prüfung\n", encoding="utf-8")
        found = module.headings(sample)
    assert found[1][2] == found[2][2] == "prüfung"


def test_relative_link_validation() -> None:
    module = load_validator()
    original_root = module.ROOT
    try:
        with tempfile.TemporaryDirectory(prefix="videobatch-doc-link-") as directory:
            root = Path(directory)
            source = root / "source.md"
            target = root / "target.md"
            source.write_text("# Quelle\n", encoding="utf-8")
            target.write_text("# Ziel\n\n## Abschnitt\n", encoding="utf-8")
            module.ROOT = root
            cache: dict[Path, set[str]] = {}
            assert module.validate_link(source, "target.md#abschnitt", cache) is None
            assert "fehlt" in str(module.validate_link(source, "target.md#unbekannt", cache))
            assert "fehlt" in str(module.validate_link(source, "missing.md", cache))
    finally:
        module.ROOT = original_root


def test_classification_schema_is_complete_and_unique() -> None:
    value = json.loads(
        (ROOT / "docs" / "DOCUMENTATION_CLASSIFICATION.json").read_text(encoding="utf-8")
    )
    documents = value["documents"]
    assert len(documents) == len(set(documents))
    assert all(
        entry["category"] in {"active", "technical", "historical", "internal"}
        for entry in documents.values()
    )
    assert all(
        entry.get("required_sections")
        for entry in documents.values()
        if entry["category"] == "active"
    )


def test_intent_help_is_safe_and_complete() -> None:
    source = (
        ROOT / "src" / "videobatch_fast" / "canonical_help_status_mixin.py"
    ).read_text(encoding="utf-8")
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
    help_start = source.index("def _build_canonical_help_page")
    help_end = len(source)
    assert "self._start(" not in source[help_start:help_end]


def contract_tests() -> tuple[tuple[str, Callable[[], None]], ...]:
    return tuple(
        (name, value)
        for name, value in sorted(globals().items())
        if name.startswith("test_") and callable(value)
    )


def main() -> int:
    tests = contract_tests()
    if not tests:
        print("DOKUMENTATIONSVERTRAG FEHLERHAFT · keine Tests gefunden", file=sys.stderr)
        return 2

    for name, test in tests:
        try:
            test()
        except Exception as exc:
            print(f"DOKUMENTATIONSVERTRAG FEHLERHAFT · {name} · {exc}", file=sys.stderr)
            return 1

    print(f"DOKUMENTATIONSVERTRAG BESTANDEN · {len(tests)} Tests")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
