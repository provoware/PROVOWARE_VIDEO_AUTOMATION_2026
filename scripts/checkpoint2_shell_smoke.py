#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from tkinter import Tk

from videobatch_fast.canonical_shell_contract import (
    CANONICAL_THEME_LABELS,
    FONT_PROFILES,
    SHELL_NAVIGATION,
)
from videobatch_fast.canonical_ui import CanonicalVideoBatchFastUI


class FakeRetryStore:
    def __init__(self, source: Path, *, enabled: bool = True) -> None:
        self.path = Path("retry-evidence") / "retry_queue.json"
        self._entry = {
            "state": "failed",
            "retry_allowed": True,
            "audio": str(source),
            "media": str(source),
            "media_sequence": [],
            "latest_error": "Encoder meldet kontrollierten Testfehler",
            "first_error": "Encoder meldet kontrollierten Testfehler",
        }
        self.enabled = enabled

    def summary(self):
        return SimpleNamespace(
            retryable=1 if self.enabled else 0,
            blocked=0,
            total=1 if self.enabled else 0,
        )

    def entries(self):
        return (self._entry,) if self.enabled else ()

    def eligible_entries(self):
        return (self._entry,) if self.enabled else ()


def main() -> int:
    root = Tk()
    root.geometry("1024x680")
    app = CanonicalVideoBatchFastUI(root)
    root.update_idletasks()

    existing = Path("README.md")
    missing = Path("checkpoint3-intentionally-missing-source.png")
    app._kpi_retry_store = FakeRetryStore(existing, enabled=False)
    app.audios = []
    app.media = []
    app.jobs = []
    app.last_results = []
    app._refresh_kpi_cards()

    assert root.minsize() == (1024, 680)
    assert len(app._shell_nav_buttons) == len(SHELL_NAVIGATION)
    assert len(app._shell_action_buttons) == 7
    assert len(app._shell_kpi_buttons) == 4
    assert len(app._shell_kpi_cause_vars) == 4
    assert len(app._shell_kpi_updated_vars) == 4
    assert app.main_notebook.index("end") == 6
    assert app._shell_kpi_status_vars["media"].get() == "Leer"
    assert str(app._shell_kpi_buttons["scheduler"].cget("state")) == "disabled"

    for key, page_index in (("media", 1), ("queue", 1), ("effects", 3)):
        app._shell_kpi_buttons[key].invoke()
        root.update_idletasks()
        actual_page = app.main_notebook.index(app.main_notebook.select())
        assert actual_page == page_index, f"{key}: expected page {page_index}, got {actual_page}"

    app.audios = [existing]
    app.media = [missing]
    app._refresh_kpi_cards()
    assert app._shell_kpi_status_vars["media"].get() == "Wiederherstellung nötig"
    assert "nicht mehr vorhanden" in app._shell_kpi_cause_vars["media"].get()
    assert app._shell_kpi_buttons["media"].cget("text") == "Fehlende entfernen"
    app._shell_kpi_buttons["media"].invoke()
    root.update_idletasks()
    assert missing not in app.media

    app._kpi_retry_store = FakeRetryStore(existing, enabled=True)
    app.audios = [existing]
    app.media = [existing]
    app.jobs = [object()]
    app.last_results = [
        SimpleNamespace(success=False, message="Encoder meldet kontrollierten Testfehler")
    ]
    app._refresh_kpi_cards()
    assert app._shell_kpi_status_vars["queue"].get() == "Wiederherstellung nötig"
    assert "Encoder" in app._shell_kpi_cause_vars["queue"].get()
    assert app._shell_kpi_buttons["queue"].cget("text") == "Wiederanlauf laden"
    app._shell_kpi_buttons["queue"].invoke()
    root.update_idletasks()
    assert app.main_notebook.index(app.main_notebook.select()) == 4
    assert existing in app.audios and existing in app.media

    app.visual_effect.set("ungueltiger-effekt")
    app.transition.set("none")
    app._refresh_kpi_cards()
    assert app._shell_kpi_status_vars["effects"].get() == "Wiederherstellung nötig"
    assert app._shell_kpi_buttons["effects"].cget("text") == "Automatik herstellen"
    app._shell_kpi_buttons["effects"].invoke()
    root.update_idletasks()
    assert app.quick_mode.get() == "smart_auto"
    assert app.visual_effect.get() == "none"
    assert app.transition.get() == "none"

    app._kpi_retry_store = FakeRetryStore(existing, enabled=False)
    for index in range(160):
        phase = index % 4
        app.last_results = []
        app.jobs = []
        app.visual_effect.set("none")
        app.transition.set("none")
        if phase == 0:
            app.audios = [existing]
            app.media = [existing]
            app.jobs = [object()]
        elif phase == 1:
            app.audios = [existing]
            app.media = [missing]
        elif phase == 2:
            app.audios = [existing]
            app.media = [existing]
            app.jobs = [object()]
            app.last_results = [
                SimpleNamespace(success=False, message="Schneller Queue-Testfehler")
            ]
        else:
            app.audios = [existing]
            app.media = [existing]
            app.visual_effect.set("hardtechno" if index % 8 else "ungueltig")
        app._refresh_kpi_cards()
        root.update_idletasks()

    history_before = dict(app._kpi_detail_history["media"])
    app._refresh_kpi_cards()
    assert app._kpi_detail_history["media"]["updated_at"] == history_before["updated_at"]
    persisted = app._collect_project_state()["meta"]["canonical_kpi"]
    assert set(persisted) == {"media", "queue", "effects", "scheduler"}
    assert all(value["updated_at"] for value in persisted.values())

    for page_index in range(6):
        app._select_shell_page(page_index)
        root.update_idletasks()
        assert app.main_notebook.index(app.main_notebook.select()) == page_index

    for theme_id, label in CANONICAL_THEME_LABELS.items():
        app._set_canonical_theme(theme_id)
        root.update_idletasks()
        assert app.theme_name.get() == theme_id
        assert app.shell_theme_combo.get() == label

    for label, scale in FONT_PROFILES.items():
        app._set_global_zoom(scale)
        root.update_idletasks()
        assert app.global_font_scale.get() == scale
        assert app._font_profile_for_scale(scale) == label

    root.update_idletasks()
    assert root.winfo_width() >= 1024
    assert root.winfo_height() >= 680
    root.destroy()
    print("CHECKPOINT2_CANONICAL_SHELL_OK")
    print("CHECKPOINT3_KPI_DETAIL_RECOVERY_SEQUENCE_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
