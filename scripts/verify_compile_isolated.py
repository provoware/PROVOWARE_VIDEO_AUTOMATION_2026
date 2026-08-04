#!/usr/bin/env python3
from __future__ import annotations

import compileall
import shutil
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="videobatch_compile_") as tmp:
        target = Path(tmp) / "python"
        target.mkdir()
        for source_root in (ROOT / "src", ROOT / "scripts", ROOT / "tests"):
            destination = target / source_root.name
            shutil.copytree(source_root, destination, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"))
        ok = compileall.compile_dir(target, quiet=1, force=True)
    print("ISOLIERTE PYTHON-KOMPILIERUNG BESTANDEN" if ok else "ISOLIERTE PYTHON-KOMPILIERUNG FEHLGESCHLAGEN")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
