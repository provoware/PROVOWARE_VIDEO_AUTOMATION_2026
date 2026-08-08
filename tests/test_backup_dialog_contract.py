from pathlib import Path


def test_backup_action_opens_manager_not_implicit_backup() -> None:
    source = Path("src/videobatch_fast/canonical_shell_chrome.py").read_text(encoding="utf-8")
    assert '("backup", "Sicherungen", self._open_backup_manager' in source


def test_backup_dialog_protects_active_project() -> None:
    source = Path("src/videobatch_fast/project_backup_dialog.py").read_text(encoding="utf-8")
    assert "Aktives Projekt geschützt" in source
    assert "overwrite=False" in source
