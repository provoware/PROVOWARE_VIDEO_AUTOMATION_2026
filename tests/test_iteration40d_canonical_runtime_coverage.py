from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from tkinter import Tk


def _isolated_canonical_app(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    monkeypatch.setenv("VIDEOBATCH_SAFE_MODE", "1")

    from videobatch_fast.config import DEFAULT_CONFIG
    from videobatch_fast.canonical_ui import CanonicalVideoBatchFastUI

    monkeypatch.setitem(DEFAULT_CONFIG, "output_dir", str(tmp_path / "output"))
    monkeypatch.setitem(DEFAULT_CONFIG, "current_project_file", str(tmp_path / "project.vbfast.json"))
    monkeypatch.setitem(DEFAULT_CONFIG, "last_audio_dir", str(tmp_path))
    monkeypatch.setitem(DEFAULT_CONFIG, "last_media_dir", str(tmp_path))

    root = Tk()
    root.geometry("1500x920")
    app = CanonicalVideoBatchFastUI(root)
    root.update_idletasks()
    root.update()
    return root, app


def test_canonical_runtime_exercises_real_shell_navigation_and_responsive_layouts(monkeypatch, tmp_path) -> None:
    root, app = _isolated_canonical_app(monkeypatch, tmp_path)
    try:
        assert app.main_notebook.index("end") == 6

        for index in range(6):
            app._select_shell_page(index)
            root.update_idletasks()
            app._on_shell_tab_changed()

        for query, expected_index in (
            ("medien", 1),
            ("preview", 2),
            ("effekt", 3),
            ("queue", 4),
            ("hilfe", 5),
            ("nichts-passendes", 0),
        ):
            app.shell_search.set(query)
            app._run_shell_search()
            assert int(app.main_notebook.index(app.main_notebook.select())) == expected_index

        for view in ("assistant", "overview", "nicht-vorhanden"):
            app._show_dashboard_view(view)
            root.update_idletasks()

        for width in (0, 450, 620, 700, 900, 1100, 1250, 1500, 1800):
            app._layout_canonical_dashboard(max(1, width))
            app._layout_shell_header(width=width)
            app._layout_shell_kpis(width=width)
            app._layout_shell_actions(width=width)
            app._layout_help_intents(width=width)

        app._select_shell_page(None)
        previous = app.config.get("active_tab", 0)
        app.config["active_tab"] = "ungueltig"
        app._restore_shell_selection()
        app.config["active_tab"] = previous

        app._set_canonical_theme("nicht-vorhanden")
        app._set_canonical_theme(app.theme_name.get())
        app._refresh_kpi_cards()
        app._refresh_canonical_dashboard()
        context = app._debug_context()
        assert context["Aktiver Tab"] in range(6)
    finally:
        root.destroy()


def test_canonical_runtime_exercises_dashboard_kpi_and_debug_decision_paths(monkeypatch, tmp_path) -> None:
    root, app = _isolated_canonical_app(monkeypatch, tmp_path)
    try:
        from videobatch_fast.canonical_kpi_detail_mixin import CanonicalKpiDetailMixin

        audio = tmp_path / "audio.wav"
        medium = tmp_path / "medium.png"
        audio.write_bytes(b"audio")
        medium.write_bytes(b"image")
        missing = tmp_path / "missing.png"

        jobs = [
            SimpleNamespace(index=index, output=Path(f"job-{index}.mp4"), audio=audio, source_media=(medium,))
            for index in range(101)
        ]
        success = SimpleNamespace(success=True, job=jobs[0], message="ok")
        failure = SimpleNamespace(success=False, job=jobs[1], message="controlled")

        app.audios = [audio]
        app.media = [medium, missing]
        app.jobs = jobs
        app.last_results = [success, failure]
        app._dashboard_queue_filter.set("")
        app._refresh_canonical_dashboard()
        assert "fehlerhaft" in app._dashboard_queue_summary.get()

        app.last_results = [success]
        app._refresh_canonical_dashboard()
        assert "Bestanden" in app._dashboard_renderproof.get()
        app.last_results = []
        app._refresh_canonical_dashboard()
        assert "nicht bestätigt" in app._dashboard_renderproof.get()

        app._refresh_dashboard_sources([audio] * 101, [])
        app._refresh_dashboard_queue(jobs, [success, failure])
        children = app._dashboard_queue_tree.get_children()
        assert len(children) == 101
        first = children[0]
        app._dashboard_queue_tree.selection_set(first)
        app._select_dashboard_job()
        assert app._dashboard_selected_job_index == 0
        app._dashboard_queue_tree.selection_remove(first)
        app._select_dashboard_job()

        app._dashboard_queue_filter.set("kein-treffer")
        app._refresh_dashboard_queue(jobs, [])
        assert not app._dashboard_queue_tree.get_children()

        for delta in (120, -120, 0):
            app._scroll_dashboard(SimpleNamespace(delta=delta))

        assert CanonicalKpiDetailMixin._kpi_history_from_state(None) == {}
        assert CanonicalKpiDetailMixin._kpi_history_from_state({"meta": []}) == {}
        for state in ("error", "warning", "loading", "success"):
            assert CanonicalKpiDetailMixin._kpi_action_style(SimpleNamespace(state=state)).endswith(".TButton")
        for action in (
            "open_media",
            "import_audio",
            "import_media",
            "remove_missing_sources",
            "open_queue",
            "reload_retry_queue",
            "open_retry_queue",
            "open_effects",
            "reset_effects",
        ):
            assert app._kpi_action_callback(action) is not None
        assert app._kpi_action_callback("unbekannt") is None

        class RetryStore:
            def summary(self):
                return SimpleNamespace(retryable=2, blocked=1)

            def entries(self):
                return (
                    {"state": "failed", "latest_error": "Encoderfehler"},
                    {"state": "done", "first_error": "ignoriert"},
                )

        app._kpi_retry_store = RetryStore()
        retryable, blocked, reasons = app._retry_snapshot_data()
        assert (retryable, blocked) == (2, 1)
        assert reasons == ("Encoderfehler",)

        class BrokenRetryStore:
            def summary(self):
                raise OSError("kontrollierter Testfehler")

        app._kpi_retry_store = BrokenRetryStore()
        assert app._retry_snapshot_data() == (0, 0, ())

        app.debug_mode.set(False)
        app._toggle_debug_mode()
        assert app.config["debug_mode"] is False
        app.debug_mode.set(True)
        app._toggle_debug_mode()
        assert app.config["debug_mode"] is True

        class BrokenVariable:
            def get(self):
                raise RuntimeError("kontrollierter Testfehler")

        original_theme = app.theme_name
        app.theme_name = BrokenVariable()
        assert app._debug_context()["Theme"] == "<nicht lesbar>"
        app.theme_name = original_theme
    finally:
        root.destroy()
