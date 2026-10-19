from __future__ import annotations
import importlib.util
import zipfile
from pathlib import Path

CODE = Path(__file__).resolve().parents[1] / "scripts" / "validate_root_layout.py"
spec = importlib.util.spec_from_file_location("root_layout_contract", CODE)
assert spec and spec.loader
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

def test_repo_root_limit() -> None:
    mod.validate(mod.root_files(Path(__file__).resolve().parents[1]))

def test_archive_limit(tmp_path: Path) -> None:
    target = tmp_path / "build.zip"
    with zipfile.ZipFile(target, "w") as output:
        for name in ("STARTEN.sh", "README.md", ".gitignore", "AGENTS.md", "pyproject.toml"):
            output.writestr("VideoBatch/" + name, b"ok")
    mod.validate(mod.archive_root_files(target))

def test_archive_rejects_nine_files(tmp_path: Path) -> None:
    target = tmp_path / "bad.zip"
    with zipfile.ZipFile(target, "w") as output:
        for name in ("STARTEN.sh", "README.md") + tuple(f"extra-{x}.txt" for x in range(7)):
            output.writestr("VideoBatch/" + name, b"ok")
    try:
        mod.validate(mod.archive_root_files(target))
    except ValueError as error:
        assert "Zu viele" in str(error)
    else:
        raise AssertionError("Paket mit neun Root-Dateien akzeptiert")
