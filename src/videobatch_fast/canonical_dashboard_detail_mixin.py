from __future__ import annotations

from tkinter import Canvas, DoubleVar, StringVar, TclError, filedialog, messagebox, ttk

from .scheduler_readiness import inspect_scheduler_readiness
from .scheduler import (
    cancel_schedule, create_schedule_record, list_schedules, next_active_schedule,
    register_systemd_schedule, save_schedule, schedule_display_time, schedule_recurrence_label,
)
from .scheduler_dialog import SchedulerDialog
from .scheduler_history import list_scheduler_history
from .scheduler_manager_dialog import SchedulerManagerDialog
from .scheduler_governance import cleanup_completed_schedules, pause_schedule, resume_schedule
from .scheduler_operations import build_operations_snapshot
from .scheduler_policy_dialog import SchedulerPolicyDialog
from .scheduler_reconcile import reconcile_scheduler_state
from .scheduler_export import export_scheduler_state
from .theme import COLORS


class CanonicalDashboardDetailMixin:
    """Job-detail and scheduler cards kept separate from dashboard orchestration."""

    def _build_dashboard_details_card(self, parent):
        card = ttk.Frame(parent, style="ShellCard.TFrame", padding=(12, 10))
        card.columnconfigure(0, weight=1)
        card.rowconfigure(1, weight=1)
        self._dashboard_detail_title = StringVar(value="Job Details")
        ttk.Label(card, textvariable=self._dashboard_detail_title, style="SectionHeader.TLabel").grid(row=0, column=0, sticky="w")

        tabs = ttk.Notebook(card)
        tabs.grid(row=1, column=0, sticky="nsew", pady=(6, 0))
        preview_tab = ttk.Frame(tabs, style="ShellCard.TFrame", padding=6)
        effects_tab = ttk.Frame(tabs, style="ShellCard.TFrame", padding=8)
        output_tab = ttk.Frame(tabs, style="ShellCard.TFrame", padding=8)
        schedule_tab = ttk.Frame(tabs, style="ShellCard.TFrame", padding=8)
        tabs.add(preview_tab, text="Vorschau")
        tabs.add(effects_tab, text="Effekte")
        tabs.add(output_tab, text="Ausgabe")
        tabs.add(schedule_tab, text="Zeitplan")
        self._dashboard_detail_tabs = tabs

        preview_tab.columnconfigure(0, weight=1)
        preview_tab.rowconfigure(0, weight=1)
        preview = Canvas(
            preview_tab,
            height=190,
            background=COLORS["preview"],
            highlightbackground=COLORS["border_subtle"],
            highlightthickness=1,
            borderwidth=0,
        )
        preview.grid(row=0, column=0, sticky="nsew")
        preview.bind("<Configure>", lambda _event: self._refresh_dashboard_preview(), add="+")
        self._dashboard_preview_canvas = preview
        transport = ttk.Frame(preview_tab, style="ShellCard.TFrame")
        transport.grid(row=1, column=0, sticky="ew", pady=(6, 0))
        self._dashboard_play_button = ttk.Button(transport, text="Abspielen", command=self._dashboard_transport_play, state="disabled")
        self._dashboard_play_button.pack(side="left")
        self._dashboard_pause_button = ttk.Button(transport, text="Pause", command=self._dashboard_transport_pause, state="disabled")
        self._dashboard_pause_button.pack(side="left", padx=(3, 0))
        self._dashboard_stop_button = ttk.Button(transport, text="Stopp", command=self._dashboard_transport_stop, state="disabled")
        self._dashboard_stop_button.pack(side="left", padx=(3, 0))
        ttk.Button(transport, text="−", width=3, command=lambda: self._set_preview_zoom(max(25, self.preview_zoom.get() - 25))).pack(side="left", padx=(6, 0))
        ttk.Button(transport, text="Einpassen", command=lambda: self._set_preview_zoom(100)).pack(side="left", padx=(3, 0))
        ttk.Button(transport, text="+", width=3, command=lambda: self._set_preview_zoom(min(800, self.preview_zoom.get() + 25))).pack(side="left", padx=(3, 0))
        ttk.Button(transport, text="Vollbild", command=self._open_preview_fullscreen).pack(side="left", padx=(3, 0))

        seek = ttk.Frame(preview_tab, style="ShellCard.TFrame")
        seek.grid(row=2, column=0, sticky="ew", pady=(5, 0))
        seek.columnconfigure(0, weight=1)
        self._dashboard_seek_value = DoubleVar(value=0.0)
        self._dashboard_seek_scale = ttk.Scale(seek, from_=0.0, to=1.0, variable=self._dashboard_seek_value, state="disabled")
        self._dashboard_seek_scale.grid(row=0, column=0, sticky="ew")
        self._dashboard_seek_scale.bind("<ButtonRelease-1>", self._dashboard_transport_seek, add="+")
        self._dashboard_transport_time = StringVar(value="Kein Video ausgewählt")
        ttk.Label(seek, textvariable=self._dashboard_transport_time, style="Hint.TLabel").grid(row=0, column=1, padx=(8, 0))
        ttk.Label(preview_tab, textvariable=self.preview_meta, style="Hint.TLabel").grid(row=3, column=0, sticky="w", pady=(4, 0))

        self._dashboard_detail_summary = StringVar(value="Noch kein Auftrag ausgewählt")
        ttk.Label(effects_tab, text="Aktives Preset / Effekte", style="SectionHeader.TLabel").pack(anchor="w")
        ttk.Label(effects_tab, textvariable=self._dashboard_detail_summary, style="Hint.TLabel", justify="left").pack(anchor="w", fill="x", pady=(7, 8))
        ttk.Button(effects_tab, text="Effekte bearbeiten", command=lambda: self._select_shell_page(3)).pack(fill="x")

        self._dashboard_output_detail = StringVar(value="Ausgabe wird geladen")
        ttk.Label(output_tab, text="Ausgabe-Einstellungen", style="SectionHeader.TLabel").pack(anchor="w")
        ttk.Label(output_tab, textvariable=self._dashboard_output_detail, style="Hint.TLabel", justify="left").pack(anchor="w", fill="x", pady=(7, 8))
        ttk.Button(output_tab, text="Ausgabe konfigurieren", command=self._open_settings).pack(fill="x")

        ttk.Label(schedule_tab, text="Startzeituhr", style="SectionHeader.TLabel").pack(anchor="w")
        self._dashboard_scheduler_readiness = StringVar(value="Voraussetzungen werden geprüft …")
        ttk.Label(schedule_tab, textvariable=self._dashboard_scheduler_readiness, style="Hint.TLabel", justify="left").pack(anchor="w", fill="x", pady=(7, 5))
        ttk.Button(schedule_tab, text="Voraussetzungen prüfen", command=self._refresh_scheduler_readiness).pack(fill="x", pady=(0, 5))
        self._dashboard_schedule_button = ttk.Button(schedule_tab, text="Zeitpläne verwalten", command=self._open_scheduler_dialog, state="disabled")
        self._dashboard_schedule_button.pack(fill="x")
        self.root.after_idle(self._refresh_scheduler_readiness)

        proof = ttk.Frame(card, style="ShellCard.TFrame", padding=(0, 6, 0, 0))
        proof.grid(row=2, column=0, sticky="ew")
        self._dashboard_renderproof = StringVar(value="RenderProof – nicht bestätigt")
        self._dashboard_renderproof_label = ttk.Label(proof, textvariable=self._dashboard_renderproof, style="Warning.TLabel")
        self._dashboard_renderproof_label.pack(side="left")
        card.bind("<Configure>", self._update_dashboard_wraplengths, add="+")
        return card

    def _refresh_scheduler_readiness(self) -> None:
        readiness = inspect_scheduler_readiness()
        if readiness.ready and not getattr(self, "_scheduler_reconciled_once", False):
            try:
                reconcile_scheduler_state(project_path=getattr(self, "project_file", None), repair=True)
            except (OSError, ValueError, RuntimeError):
                pass
            else:
                self._scheduler_reconciled_once = True
        lines = [readiness.summary]
        lines.extend(f"{'✓' if ok else '–'} {name}: {detail}" for name, ok, detail in readiness.checks)
        active = self._active_scheduler_record()
        plans = self._scheduler_records()
        if active is not None:
            lines.append(
                f"Nächster Lauf: {schedule_display_time(active)} · {schedule_recurrence_label(active)} · "
                f"{active.get('status', 'pending')}"
            )
        if plans:
            lines.append(f"Zeitpläne dieses Projekts: {len(plans)}")
        if hasattr(self, "_dashboard_scheduler_readiness"):
            self._dashboard_scheduler_readiness.set("\n".join(lines))
        if hasattr(self, "_dashboard_scheduler_summary"):
            self._dashboard_scheduler_summary.set(self._scheduler_summary(active, readiness.ready))
        state = "normal" if readiness.ready else "disabled"
        for name in ("_dashboard_schedule_button", "_dashboard_schedule_card_button"):
            button = getattr(self, name, None)
            if button is not None:
                button.configure(state=state)

    def _active_scheduler_record(self):
        try:
            return next_active_schedule(getattr(self, "project_file", None))
        except (OSError, ValueError):
            return None

    def _scheduler_records(self):
        try:
            return list_schedules(project_path=getattr(self, "project_file", None))
        except (OSError, ValueError):
            return []

    @staticmethod
    def _scheduler_summary(active, ready: bool) -> str:
        if active is not None:
            return f"Nächster Lauf: {schedule_display_time(active)} · {schedule_recurrence_label(active)}"
        return "Keine aktive Planung · Scheduler bereit" if ready else "Keine aktive Planung · Systemvoraussetzungen fehlen"

    def _open_scheduler_dialog(self) -> None:
        readiness = inspect_scheduler_readiness()
        if not readiness.ready:
            messagebox.showwarning(
                "Scheduler nicht bereit",
                "Die systemd-Benutzerumgebung oder benötigte Medienwerkzeuge fehlen. Bitte zuerst die Voraussetzungen prüfen.",
                parent=self.root,
            )
            self._refresh_scheduler_readiness()
            return
        SchedulerManagerDialog(
            self,
            load_schedules=self._scheduler_records,
            load_history=lambda: list_scheduler_history(project_path=getattr(self, "project_file", None), limit=300),
            open_editor=self._open_scheduler_editor,
            cancel_schedule=self._cancel_scheduler_plan,
            pause_schedule=pause_schedule,
            resume_schedule=resume_schedule,
            load_operations=lambda horizon_hours=24: build_operations_snapshot(
                schedules=self._scheduler_records(), project_path=getattr(self, "project_file", None),
                horizon_hours=horizon_hours,
            ),
            export_state=self._export_scheduler_state,
            cleanup_completed=lambda: cleanup_completed_schedules(project_path=getattr(self, "project_file", None)),
            reconcile_state=lambda: reconcile_scheduler_state(
                project_path=getattr(self, "project_file", None), repair=True
            ),
            open_policy=self._open_scheduler_policy,
        )

    def _open_scheduler_editor(self, record=None, replace: bool = False):
        replace_id = str(record.get("schedule_id")) if replace and record else None
        dialog = SchedulerDialog(
            self,
            on_save=lambda when, **kwargs: self._save_scheduler_plan(
                when, replace_schedule_id=replace_id, **kwargs
            ),
            active_schedule=record,
            title="Zeitplan bearbeiten" if replace_id else ("Zeitplan duplizieren" if record else "Zeitplan anlegen"),
        )
        return dialog.window

    def _save_scheduler_plan(
        self,
        when,
        *,
        inhibit_sleep: bool,
        after_action: str,
        max_lateness_minutes: int,
        recurrence: dict,
        timezone_name: str,
        priority: int = 50,
        replace_schedule_id: str | None = None,
    ) -> None:
        self._autosave_project(force=True)
        self._rebuild_pairs()
        if not self.jobs:
            raise ValueError("Es sind keine gültigen Renderaufträge vorbereitet.")
        options = self._options()
        from .validation import validate_pairs
        blockers = [item for item in validate_pairs(self.jobs, options) if item.blocking]
        if blockers:
            raise ValueError("Vor der Planung müssen alle blockierenden Projektangaben vollständig sein.")
        record = create_schedule_record(
            project_path=self.project_file,
            source_paths=[*self.audios, *self.media],
            options=options,
            scheduled_at=when,
            inhibit_sleep=inhibit_sleep,
            after_action=after_action,
            max_lateness_minutes=max_lateness_minutes,
            recurrence=recurrence,
            timezone_name=timezone_name,
            priority=priority,
        )
        save_schedule(record)
        try:
            register_systemd_schedule(record)
            if replace_schedule_id:
                cancel_schedule(replace_schedule_id)
        except Exception as exc:
            try:
                cancel_schedule(record["schedule_id"])
            except Exception:
                pass
            from .scheduler import update_schedule_status
            update_schedule_status(record["schedule_id"], "failed", f"Planung konnte nicht registriert werden: {exc}")
            raise ValueError(f"Zeitplan konnte nicht aktiviert werden: {exc}") from exc
        action = "ersetzt" if replace_schedule_id else "gespeichert"
        self.guidance_text.set(
            f"Zeitplan {action}. Wiederholung, Catch-up und Quellzustand werden vor jedem Lauf sicher geprüft."
        )
        self._refresh_scheduler_readiness()
        if hasattr(self, "_refresh_kpi_cards"):
            self._refresh_kpi_cards()

    def _open_scheduler_policy(self) -> None:
        dialog = SchedulerPolicyDialog(self, on_saved=self._refresh_scheduler_readiness)
        self.root.wait_window(dialog.window)

    def _export_scheduler_state(self):
        if getattr(self, "project_file", None) is None:
            raise ValueError("Für den Scheduler-Export muss zuerst ein Projekt gespeichert sein.")
        destination = filedialog.askdirectory(title="Scheduler-Exportordner wählen", parent=self.root)
        if not destination:
            return None
        from pathlib import Path
        return export_scheduler_state(Path(self.project_file), Path(destination))

    def _cancel_scheduler_plan(self, schedule_id: str) -> None:
        try:
            cancel_schedule(schedule_id)
        except Exception as exc:
            messagebox.showerror("Planung konnte nicht gelöscht werden", str(exc), parent=self.root)
            return
        self.guidance_text.set("Zeitplan wurde gelöscht.")
        self._refresh_scheduler_readiness()
        if hasattr(self, "_refresh_kpi_cards"):
            self._refresh_kpi_cards()

    @staticmethod
    def _set_dashboard_scheduler_wrap(label, width: int) -> None:
        target = max(180, int(width) - 4)
        try:
            current = int(float(label.cget("wraplength") or 0))
            if current != target:
                label.configure(wraplength=target)
        except (TclError, ValueError):
            return

    def _build_dashboard_scheduler_card(self, parent):
        card = ttk.Frame(parent, style="ShellCard.TFrame", padding=(14, 12))
        ttk.Label(card, text="Startzeituhr", style="SectionHeader.TLabel").pack(anchor="w")
        self._dashboard_scheduler_summary = StringVar(
            value="Nicht geplant · Schedulerstatus wird geprüft"
        )
        scheduler = ttk.Label(
            card,
            textvariable=self._dashboard_scheduler_summary,
            style="Hint.TLabel",
            justify="left",
        )
        scheduler.pack(anchor="w", fill="x", pady=(7, 8))
        scheduler.bind(
            "<Configure>",
            lambda event: self._set_dashboard_scheduler_wrap(scheduler, event.width),
            add="+",
        )
        self._dashboard_schedule_card_button = ttk.Button(
            card,
            text="◷ Zeitpläne verwalten",
            command=self._open_scheduler_dialog,
            state="disabled",
        )
        self._dashboard_schedule_card_button.pack(fill="x")
        return card
