from __future__ import annotations

from pathlib import Path
from tkinter import StringVar, TclError, ttk
from typing import Any

from .canonical_kpi import KpiSnapshot, build_kpi_snapshots
from .canonical_kpi_state import format_kpi_timestamp, merge_kpi_history, normalize_kpi_history
from .effects import TRANSITIONS, VISUAL_EFFECTS
from .retry_queue import RetryQueueStore


class CanonicalKpiDetailMixin:
    """Persistent KPI details, causes, timestamps and bounded recovery actions."""

    def _build_shell_kpis(self, parent) -> None:
        self._kpi_persistence_ready = False
        self._kpi_persist_after_id: str | None = None
        self._canonical_retry_store: RetryQueueStore | None = None
        self._kpi_detail_history = self._kpi_history_from_state(getattr(self, "project_state", {}))
        super()._build_shell_kpis(parent)

        keys = tuple(self._shell_kpi_buttons)
        self._shell_kpi_cause_vars = {key: StringVar(value="Ursache wird ermittelt") for key in keys}
        self._shell_kpi_updated_vars = {key: StringVar(value="Aktualisiert: –") for key in keys}
        for key in keys:
            button = self._shell_kpi_buttons[key]
            card = button.master
            button.pack_forget()
            ttk.Label(
                card,
                textvariable=self._shell_kpi_cause_vars[key],
                style="ShellKpiHint.TLabel",
                wraplength=220,
                justify="left",
            ).pack(anchor="w", pady=(0, 4))
            ttk.Label(
                card,
                textvariable=self._shell_kpi_updated_vars[key],
                style="ShellKpiHint.TLabel",
                wraplength=220,
                justify="left",
            ).pack(anchor="w", pady=(0, 5))
            button.pack(fill="x")
        self._refresh_kpi_cards()

    @staticmethod
    def _kpi_history_from_state(state: Any) -> dict[str, dict[str, Any]]:
        if not isinstance(state, dict):
            return {}
        meta = state.get("meta", {})
        if not isinstance(meta, dict):
            return {}
        return normalize_kpi_history(meta.get("canonical_kpi", {}))

    def _collect_project_state(self) -> dict:
        state = super()._collect_project_state()
        meta = dict(state.get("meta", {}))
        meta["canonical_kpi"] = normalize_kpi_history(getattr(self, "_kpi_detail_history", {}))
        state["meta"] = meta
        return state

    def _apply_project_state(self, state: dict) -> None:
        super()._apply_project_state(state)
        self._kpi_detail_history = self._kpi_history_from_state(state)
        self._kpi_persistence_ready = True
        self._refresh_kpi_cards()

    def _new_project(self) -> None:
        super()._new_project()
        self._kpi_detail_history = {}
        self._refresh_kpi_cards()

    def _retry_store(self):
        injected = getattr(self, "_kpi_retry_store", None)
        if injected is not None:
            return injected
        if self._canonical_retry_store is None:
            self._canonical_retry_store = RetryQueueStore()
        return self._canonical_retry_store

    def _retry_snapshot_data(self) -> tuple[int, int, tuple[str, ...]]:
        try:
            store = self._retry_store()
            summary = store.summary()
            reasons = tuple(
                str(entry.get("latest_error", "") or entry.get("first_error", ""))
                for entry in store.entries()
                if str(entry.get("state", "")) in {"failed", "limit_reached", "not_started"}
            )
            return (
                max(0, int(getattr(summary, "retryable", 0) or 0)),
                max(0, int(getattr(summary, "blocked", 0) or 0)),
                reasons,
            )
        except (OSError, ValueError, TypeError):
            return 0, 0, ()

    def _refresh_kpi_cards(self) -> None:
        if not hasattr(self, "_shell_kpi_value_vars"):
            return
        paths = tuple(getattr(self, "audios", ())) + tuple(getattr(self, "media", ()))
        missing_paths = tuple(Path(path) for path in paths if not Path(path).is_file())
        last_results = tuple(getattr(self, "last_results", ()))
        failed_results = tuple(result for result in last_results if not bool(getattr(result, "success", False)))
        result_reasons = tuple(str(getattr(result, "message", "")) for result in failed_results)
        retryable, blocked, retry_reasons = self._retry_snapshot_data()
        active_tasks = self.tasks.active_names() if hasattr(self, "tasks") else ()
        snapshots = build_kpi_snapshots(
            audio_count=len(getattr(self, "audios", ())),
            media_count=len(getattr(self, "media", ())),
            missing_sources=len(missing_paths),
            missing_source_names=(path.name for path in missing_paths),
            job_count=len(getattr(self, "jobs", ())),
            completed_jobs=len(last_results),
            failed_jobs=len(failed_results),
            queue_failure_reasons=(*result_reasons, *retry_reasons),
            retryable_jobs=retryable,
            blocked_jobs=blocked,
            active_tasks=active_tasks,
            visual_effect=self.visual_effect.get(),
            transition=self.transition.get(),
            quick_mode=self.quick_mode.get(),
            effect_valid=self.visual_effect.get() in VISUAL_EFFECTS,
            transition_valid=self.transition.get() in TRANSITIONS,
        )
        self._shell_kpi_snapshots = snapshots
        history, changed = merge_kpi_history(getattr(self, "_kpi_detail_history", {}), snapshots)
        self._kpi_detail_history = history

        for key, snapshot in snapshots.items():
            self._shell_kpi_value_vars[key].set(snapshot.value)
            self._shell_kpi_detail_vars[key].set(snapshot.detail)
            self._shell_kpi_status_vars[key].set(snapshot.status)
            self._shell_kpi_status_labels[key].configure(style=f"ShellKpiState{snapshot.state.title()}.TLabel")
            if hasattr(self, "_shell_kpi_cause_vars"):
                cause = snapshot.cause or "Keine Störung erkannt."
                self._shell_kpi_cause_vars[key].set(f"Ursache: {cause}")
                updated = format_kpi_timestamp(str(history[key].get("updated_at", "")))
                self._shell_kpi_updated_vars[key].set(f"Aktualisiert: {updated}")
            callback = self._kpi_action_callback(snapshot.recovery_action)
            button = self._shell_kpi_buttons[key]
            button.configure(
                text=snapshot.action_label,
                command=callback,
                state="normal" if snapshot.action_enabled and callback is not None else "disabled",
                style=self._kpi_action_style(snapshot),
            )
        if changed and getattr(self, "_kpi_persistence_ready", False):
            self._schedule_kpi_persist()

    @staticmethod
    def _kpi_action_style(snapshot: KpiSnapshot) -> str:
        if snapshot.state == "error":
            return "Danger.TButton"
        if snapshot.state == "warning":
            return "Accent.TButton"
        if snapshot.state == "loading":
            return "Ghost.TButton"
        return "Ghost.TButton"

    def _kpi_action_callback(self, action: str):
        actions = {
            "open_media": lambda: self._select_shell_page(1),
            "import_audio": self._add_audio,
            "import_media": self._add_media,
            "remove_missing_sources": self._kpi_remove_missing_sources,
            "open_queue": lambda: self._select_shell_page(4),
            "reload_retry_queue": self._kpi_load_retry_queue,
            "open_retry_queue": self._kpi_open_retry_queue,
            "open_effects": lambda: self._select_shell_page(3),
            "reset_effects": self._kpi_reset_effects,
        }
        return actions.get(action)

    def _schedule_kpi_persist(self) -> None:
        previous = getattr(self, "_kpi_persist_after_id", None)
        if previous:
            try:
                self.root.after_cancel(previous)
            except TclError:
                pass
        self._kpi_persist_after_id = self.root.after(250, self._persist_kpi_detail_state)

    def _persist_kpi_detail_state(self) -> None:
        self._kpi_persist_after_id = None
        try:
            if self.root.winfo_exists():
                self._autosave_project(force=True, capture_layout=False)
        except TclError:
            return

    def _kpi_remove_missing_sources(self) -> None:
        before = len(self.audios) + len(self.media)
        self.audios = [Path(path) for path in self.audios if Path(path).is_file()]
        self.media = [Path(path) for path in self.media if Path(path).is_file()]
        removed = before - len(self.audios) - len(self.media)
        self._refresh_file_trees()
        self._rebuild_pairs()
        self._autosave_project(force=True, capture_layout=False)
        self.guidance_text.set(f"{removed} nicht erreichbare Quelle(n) wurden aus dem Projekt entfernt.")
        self._event(
            "KPI_MEDIA_RECOVERED",
            "Nicht erreichbare Quellen entfernt",
            f"{removed} veraltete Projektverweise entfernt",
            level="success" if removed else "warning",
            solution="Fehlende Audio- oder Mediendateien bei Bedarf neu importieren.",
        )
        self._refresh_kpi_cards()

    def _kpi_load_retry_queue(self) -> None:
        try:
            store = self._retry_store()
            entries = tuple(store.eligible_entries())
        except (OSError, ValueError, TypeError) as exc:
            self._show_error("UNKNOWN", f"Wiederanlaufliste konnte nicht gelesen werden: {exc}")
            return
        if not entries:
            self._kpi_open_retry_queue()
            return

        audio: list[Path] = []
        media: list[Path] = []
        missing = 0
        for entry in entries:
            audio_path = Path(str(entry.get("audio", ""))).expanduser()
            if audio_path.is_file():
                audio.append(audio_path)
            else:
                missing += 1
            sequence = entry.get("media_sequence")
            candidates = sequence if isinstance(sequence, list) and sequence else [entry.get("media", "")]
            for value in candidates:
                media_path = Path(str(value)).expanduser()
                if media_path.is_file():
                    media.append(media_path)
                else:
                    missing += 1

        self.audios = list(dict.fromkeys([*self.audios, *audio]))
        self.media = list(dict.fromkeys([*self.media, *media]))
        self._refresh_file_trees()
        self._rebuild_pairs()
        self._autosave_project(force=True, capture_layout=False)
        self._select_shell_page(4)
        self.guidance_text.set(
            f"{len(entries)} Wiederanlaufeintrag/-einträge kontrolliert geladen; kein Auftrag wurde automatisch gestartet."
        )
        self._event(
            "KPI_RETRY_QUEUE_LOADED",
            "Wiederanlaufliste geladen",
            f"{len(entries)} Einträge · {len(audio)} Audio · {len(media)} Medien · {missing} nicht erreichbar",
            level="warning" if missing else "success",
            solution="Zuordnung und Fehlerursache prüfen; danach ausdrücklich neu starten.",
        )
        self._refresh_kpi_cards()

    def _kpi_open_retry_queue(self) -> None:
        try:
            path = Path(self._retry_store().path).expanduser()
            path.parent.mkdir(parents=True, exist_ok=True)
            if hasattr(self, "_open_path"):
                self._open_path(path.parent)
            else:
                self._open_local_help_target(path.parent)
            self._select_shell_page(4)
            self.guidance_text.set(f"Wiederanlaufliste: {path}")
        except (OSError, ValueError, TypeError) as exc:
            self._show_error("UNKNOWN", f"Wiederanlaufliste konnte nicht geöffnet werden: {exc}")

    def _kpi_reset_effects(self) -> None:
        self._apply_quick_mode("smart_auto")
        self._autosave_project(force=True, capture_layout=False)
        self._select_shell_page(3)
        self.guidance_text.set("Ungültige Effektwerte wurden auf die sichere Automatik zurückgesetzt.")
        self._event(
            "KPI_EFFECTS_RECOVERED",
            "Effektvertrag wiederhergestellt",
            "Automatisch schnell · registrierte Standardwerte",
            level="success",
            solution="Effekte bei Bedarf erneut bewusst auswählen.",
        )
        self._refresh_kpi_cards()

    def _close(self) -> None:
        for name in ("_kpi_persist_after_id", "_shell_kpi_poll_id"):
            after_id = getattr(self, name, None)
            if after_id:
                try:
                    self.root.after_cancel(after_id)
                except TclError:
                    pass
                setattr(self, name, None)
        super()._close()
