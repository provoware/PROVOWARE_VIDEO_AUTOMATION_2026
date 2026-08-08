from __future__ import annotations

import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _shell_scripts() -> list[Path]:
    return sorted([*ROOT.glob('*.sh'), *(ROOT / 'scripts').glob('*.sh')])


def test_all_shell_entrypoints_are_executable() -> None:
    scripts = _shell_scripts()
    assert scripts, 'Keine Shell-Entrypoints gefunden.'
    missing = [path.relative_to(ROOT).as_posix() for path in scripts if not os.access(path, os.X_OK)]
    assert not missing, f'Nicht ausführbare Shell-Entrypoints: {missing}'


def test_desktop_launcher_targets_executable_start_script() -> None:
    desktop = (ROOT / 'VideoBatch-Fast.desktop').read_text(encoding='utf-8')
    match = re.search(r'exec\s+\./([^\s\'\"]+\.sh)', desktop)
    assert match, 'Desktopstarter enthält kein direktes Shell-Entrypoint-Ziel.'
    target = ROOT / match.group(1)
    assert target.is_file(), f'Desktopstarter-Ziel fehlt: {target.name}'
    assert os.access(target, os.X_OK), f'Desktopstarter-Ziel ist nicht ausführbar: {target.name}'
