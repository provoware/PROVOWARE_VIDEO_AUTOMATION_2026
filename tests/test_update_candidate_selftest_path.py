"""Regression: Update candidate must use the actual supported self-test entrypoint."""
from pathlib import Path


def test_installer_prefers_current_selftest_and_accepts_legacy_fallback():
    root = Path(__file__).resolve().parents[1]
    code = (root / "src/videobatch_fast/updates.py").read_text(encoding="utf-8")
    modern = 'test_script = candidate / "scripts/dev/test.sh"'
    legacy = 'test_script = candidate / "test.sh"'
    assert modern in code and legacy in code
    assert code.index(modern) < code.index(legacy)
    assert (root / "scripts/dev/test.sh").is_file()
