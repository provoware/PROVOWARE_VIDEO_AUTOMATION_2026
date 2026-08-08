from __future__ import annotations

from tkinter import StringVar, Toplevel, messagebox, ttk

from .scheduler import schedule_display_time, schedule_recurrence_label
from .scheduler_operations import priority_label


def _clock(seconds) -> str:
    if seconds is None:
        return "–"
    total = max(0, int(float(seconds)))
    hours, rest = divmod(total, 3600)
    minutes, _secs = divmod(rest, 60)
    return f"{hours}h {minutes:02d}m" if hours else f"{minutes}m"


def _bytes_label(value) -> str:
    if value is None:
        return "–"
    amount = max(0.0, float(value))
    units = ("B", "KiB", "MiB", "GiB", "TiB")
    index = 0
    while amount >= 1024.0 and index < len(units) - 1:
        amount /= 1024.0
        index += 1
    return f"{amount:.1f} {units[index]}"


class SchedulerManagerDialog:
    def __init__(
        self,
        owner,
        *,
        load_schedules,
        load_history,
        load_operations,
        open_editor,
        cancel_schedule,
        pause_schedule,
        resume_schedule,
        export_state,
        cleanup_completed,
        reconcile_state,
        open_policy,
    ) -> None:
        self.owner = owner
        self.load_schedules = load_schedules
        self.load_history = load_history
        self.load_operations = load_operations
        self.open_editor = open_editor
        self.cancel_schedule = cancel_schedule
        self.pause_schedule = pause_schedule
        self.resume_schedule = resume_schedule
        self.export_state = export_state
        self.cleanup_completed = cleanup_completed
        self.reconcile_state = reconcile_state
        self.open_policy = open_policy
        self.records: dict[str, dict] = {}
        self.summary_value = StringVar(value="Schedulerstatus wird geladen …")
        self.quality_summary_value = StringVar(value="Prognosequalität wird geladen …")
        self.horizon_value = StringVar(value="24")
        self.window = Toplevel(owner.root)
        self.window.title("Scheduler Operations")
        self.window.transient(owner.root)
        self.window.geometry("1180x700")
        self.window.minsize(900, 540)
        self._build()
        self.refresh()
        self.window.grab_set()
        self.window.focus_set()

    def _build(self) -> None:
        shell = ttk.Frame(self.window, padding=14)
        shell.pack(fill="both", expand=True)
        ttk.Label(shell, text="Was läuft wann und warum?", style="SectionHeader.TLabel").pack(anchor="w")
        ttk.Label(shell, textvariable=self.summary_value, style="Hint.TLabel", wraplength=1120, justify="left").pack(anchor="w", fill="x", pady=(3, 8))
        tabs = ttk.Notebook(shell)
        tabs.pack(fill="both", expand=True)
        ops_tab = ttk.Frame(tabs, padding=6)
        forecast_tab = ttk.Frame(tabs, padding=6)
        plans_tab = ttk.Frame(tabs, padding=6)
        history_tab = ttk.Frame(tabs, padding=6)
        quality_tab = ttk.Frame(tabs, padding=6)
        tabs.add(ops_tab, text="Operations")
        tabs.add(forecast_tab, text="Dry-Run-Prognose")
        tabs.add(quality_tab, text="Prognosequalität")
        tabs.add(plans_tab, text="Zeitpläne")
        tabs.add(history_tab, text="Verlauf")

        self.ops_tree = ttk.Treeview(
            ops_tab, columns=("priority", "next", "status", "eta", "why", "action"), show="headings", selectmode="browse"
        )
        for key, label, width in (
            ("priority", "Priorität", 80), ("next", "Nächster Termin", 155), ("status", "Status", 100),
            ("eta", "ETA", 80), ("why", "Warum?", 320), ("action", "Nächste Aktion", 330),
        ):
            self.ops_tree.heading(key, text=label)
            self.ops_tree.column(key, width=width, anchor="w")
        self.ops_tree.pack(fill="both", expand=True)
        self.ops_tree.bind("<Double-1>", lambda _event: self._edit_from(self.ops_tree))

        forecast_bar = ttk.Frame(forecast_tab)
        forecast_bar.pack(fill="x", pady=(0, 6))
        ttk.Label(forecast_bar, text="Horizont:").pack(side="left")
        horizon = ttk.Combobox(forecast_bar, textvariable=self.horizon_value, values=("24", "48", "168"), width=7, state="readonly")
        horizon.pack(side="left", padx=(5, 4))
        ttk.Label(forecast_bar, text="Stunden · reine Simulation, keine Timer-/Dateiänderung", style="Hint.TLabel").pack(side="left")
        horizon.bind("<<ComboboxSelected>>", lambda _event: self.refresh())
        self.forecast_tree = ttk.Treeview(
            forecast_tab, columns=("planned", "start", "end", "priority", "confidence", "storage", "status", "reason"), show="headings"
        )
        for key, label, width in (
            ("planned", "Geplant", 140), ("start", "Prognose Start", 140), ("end", "Prognose Ende", 140),
            ("priority", "Prio", 55), ("confidence", "Konfidenz", 75), ("storage", "Speicher P75", 100),
            ("status", "Status", 80), ("reason", "Konflikt / Hinweis", 320),
        ):
            self.forecast_tree.heading(key, text=label)
            self.forecast_tree.column(key, width=width, anchor="w")
        self.forecast_tree.pack(fill="both", expand=True)

        ttk.Label(quality_tab, textvariable=self.quality_summary_value, style="Hint.TLabel", wraplength=1100).pack(
            anchor="w", fill="x", pady=(0, 6)
        )
        quality_panes = ttk.Panedwindow(quality_tab, orient="vertical")
        quality_panes.pack(fill="both", expand=True)
        backtest_frame = ttk.Frame(quality_panes)
        segment_frame = ttk.Frame(quality_panes)
        actual_frame = ttk.Frame(quality_panes)
        quality_panes.add(backtest_frame, weight=1)
        quality_panes.add(segment_frame, weight=1)
        quality_panes.add(actual_frame, weight=2)
        self.quality_tree = ttk.Treeview(
            backtest_frame, columns=("window", "count", "mae", "median", "p90", "bias"), show="headings"
        )
        for key, label, width in (
            ("window", "Backtest", 100), ("count", "Läufe", 70), ("mae", "MAE", 100),
            ("median", "Median-Fehler", 120), ("p90", "P90-Fehler", 110), ("bias", "Bias", 90),
        ):
            self.quality_tree.heading(key, text=label)
            self.quality_tree.column(key, width=width, anchor="w")
        self.quality_tree.pack(fill="both", expand=True)
        self.segment_tree = ttk.Treeview(
            segment_frame, columns=("segment", "count", "median", "p90", "output"), show="headings"
        )
        for key, label, width in (
            ("segment", "Codec / Profil / Auflösung", 300), ("count", "Läufe", 65),
            ("median", "Median-Fehler", 120), ("p90", "P90-Fehler", 110), ("output", "Speicherfehler", 120),
        ):
            self.segment_tree.heading(key, text=label)
            self.segment_tree.column(key, width=width, anchor="w")
        self.segment_tree.pack(fill="both", expand=True)
        self.actual_tree = ttk.Treeview(
            actual_frame, columns=("finished", "segment", "environment", "predicted", "actual", "error", "confidence"), show="headings"
        )
        for key, label, width in (
            ("finished", "Gemessen", 145), ("segment", "Codec / Profil / Auflösung", 220),
            ("environment", "Umgebung / Epoche", 180), ("predicted", "Prognose", 90),
            ("actual", "Ist", 90), ("error", "Abw.", 80), ("confidence", "Konfidenz", 85),
        ):
            self.actual_tree.heading(key, text=label)
            self.actual_tree.column(key, width=width, anchor="w")
        self.actual_tree.pack(fill="both", expand=True)

        self.plan_tree = ttk.Treeview(
            plans_tab, columns=("next", "repeat", "priority", "status", "progress"), show="headings", selectmode="browse"
        )
        for key, label, width in (
            ("next", "Nächster Termin", 165), ("repeat", "Wiederholung", 220), ("priority", "Priorität", 90),
            ("status", "Status", 110), ("progress", "Läufe", 90),
        ):
            self.plan_tree.heading(key, text=label)
            self.plan_tree.column(key, width=width, anchor="w")
        self.plan_tree.pack(fill="both", expand=True)
        self.plan_tree.bind("<Double-1>", lambda _event: self._edit())

        self.history_tree = ttk.Treeview(
            history_tab, columns=("finished", "outcome", "occurrence", "detail"), show="headings"
        )
        for key, label, width in (
            ("finished", "Abschluss", 165), ("outcome", "Ergebnis", 120), ("occurrence", "Lauf", 70), ("detail", "Details", 620),
        ):
            self.history_tree.heading(key, text=label)
            self.history_tree.column(key, width=width, anchor="w")
        self.history_tree.pack(fill="both", expand=True)

        actions = ttk.Frame(shell)
        actions.pack(fill="x", pady=(9, 0))
        ttk.Button(actions, text="＋ Neu", style="Success.TButton", command=self._new).pack(side="left")
        ttk.Button(actions, text="Bearbeiten", command=self._edit).pack(side="left", padx=(5, 0))
        ttk.Button(actions, text="Duplizieren", command=self._duplicate).pack(side="left", padx=(5, 0))
        ttk.Button(actions, text="Pause/Fortsetzen", command=self._toggle_pause).pack(side="left", padx=(5, 0))
        ttk.Button(actions, text="Löschen", style="Danger.TButton", command=self._cancel).pack(side="left", padx=(5, 0))
        ttk.Button(actions, text="Betriebsregeln", command=self._policy).pack(side="left", padx=(12, 0))
        ttk.Button(actions, text="Abgleichen", command=self._reconcile).pack(side="left", padx=(5, 0))
        ttk.Button(actions, text="Export", command=self._export).pack(side="left", padx=(5, 0))
        ttk.Button(actions, text="Aufräumen", command=self._cleanup).pack(side="left", padx=(5, 0))
        ttk.Button(actions, text="Aktualisieren", command=self.refresh).pack(side="right", padx=(0, 5))
        ttk.Button(actions, text="Schließen", command=self.window.destroy).pack(side="right")

    def refresh(self) -> None:
        self.records.clear()
        for tree in (self.plan_tree, self.ops_tree, self.forecast_tree, self.quality_tree, self.segment_tree, self.actual_tree, self.history_tree):
            for item in tree.get_children():
                tree.delete(item)
        schedules = list(self.load_schedules())
        for record in schedules:
            schedule_id = str(record.get("schedule_id", ""))
            self.records[schedule_id] = record
            recurrence = record.get("recurrence", {}) if isinstance(record.get("recurrence"), dict) else {}
            maximum = int(recurrence.get("max_occurrences", 1) or 1)
            completed = int(record.get("occurrences_completed", 0) or 0)
            priority = int(((record.get("governance") or {}).get("priority", 50)))
            self.plan_tree.insert(
                "", "end", iid=schedule_id,
                values=(schedule_display_time(record), schedule_recurrence_label(record), priority_label(priority), record.get("status", "–"), f"{completed}/{maximum}"),
            )
        operations = self.load_operations(int(self.horizon_value.get()))
        blackout = operations.get("active_blackout")
        blackout_text = f" · Wartungsfenster aktiv: {blackout.get('label')}" if blackout else ""
        simulation = operations.get("simulation", {})
        self.summary_value.set(
            f"Aktiv {operations.get('active_count', 0)} · Pausiert {operations.get('paused_count', 0)} · "
            f"Dead-Letter {operations.get('dead_letter_count', 0)} · Queue {operations.get('queue_size', 0)} · "
            f"{self.horizon_value.get()}h-Prognose {simulation.get('event_count', 0)} Termine / {simulation.get('risk_count', 0)} Risiken{blackout_text}"
        )
        for row in operations.get("rows", []):
            schedule_id = str(row.get("schedule_id", ""))
            forecast = row.get("forecast", {}) if isinstance(row.get("forecast"), dict) else {}
            self.ops_tree.insert(
                "", "end", iid=f"op-{schedule_id}",
                values=(
                    priority_label(int(row.get("priority", 50))),
                    str(row.get("next_run_at") or "–").replace("T", " ")[:19],
                    row.get("status", "–"),
                    _clock(forecast.get("runtime_seconds_p50")),
                    str(row.get("reason", ""))[:180],
                    str(row.get("next_action", ""))[:180],
                ),
            )
        for index, event in enumerate(simulation.get("events", []), start=1):
            forecast = event.get("forecast", {}) if isinstance(event.get("forecast"), dict) else {}
            self.forecast_tree.insert(
                "", "end", iid=f"forecast-{index}",
                values=(
                    str(event.get("planned_at") or "–").replace("T", " ")[:19],
                    str(event.get("projected_start") or "–").replace("T", " ")[:19],
                    str(event.get("projected_end") or "–").replace("T", " ")[:19],
                    event.get("priority", "–"),
                    forecast.get("confidence", "none"),
                    _bytes_label(forecast.get("output_bytes_p75")),
                    event.get("status", "–"),
                    str(event.get("reason", ""))[:220],
                ),
            )
        self._refresh_quality(operations)
        for entry in self.load_history():
            self.history_tree.insert(
                "", "end",
                values=(str(entry.get("finished_at", "–")).replace("T", " ")[:19], entry.get("outcome", "–"), entry.get("occurrence_index", "–"), str(entry.get("detail", ""))[:260]),
            )

    def _refresh_quality(self, operations: dict) -> None:
        quality = operations.get("forecast_quality", {}) if isinstance(operations.get("forecast_quality"), dict) else {}
        error_drift = quality.get("error_drift", {}) if isinstance(quality.get("error_drift"), dict) else {}
        runtime_drift = quality.get("runtime_drift", {}) if isinstance(quality.get("runtime_drift"), dict) else {}
        direct = quality.get("actual_vs_predicted", {}) if isinstance(quality.get("actual_vs_predicted"), dict) else {}
        direct_metrics = direct.get("metrics", {}) if isinstance(direct.get("metrics"), dict) else {}
        environment = quality.get("environment", {}) if isinstance(quality.get("environment"), dict) else {}
        current_environment = environment.get("current", {}) if isinstance(environment.get("current"), dict) else {}
        epoch_id = str(current_environment.get("epoch_id", ""))
        self.quality_summary_value.set(
            f"Rolling-Origin {quality.get('backtest_count', 0)} Prognosen · Fehlerdrift {error_drift.get('status', 'insufficient')} · "
            f"Laufzeitdrift {runtime_drift.get('status', 'insufficient')} · Ursache {quality.get('drift_cause', 'stable')} · "
            f"Umgebungen {environment.get('environment_count', 0)} · Epoche {epoch_id[:18] or 'legacy'} · "
            f"echte Scheduler-Vergleiche {direct_metrics.get('count', 0)}"
        )
        for window in ("30", "90", "180"):
            metrics = (quality.get("windows") or {}).get(window, {})
            median_error = metrics.get("median_abs_pct_error")
            p90_error = metrics.get("p90_abs_pct_error")
            bias = metrics.get("bias_pct")
            self.quality_tree.insert(
                "", "end", values=(
                    f"letzte {window}", metrics.get("count", 0), _clock(metrics.get("mae_seconds")),
                    f"{float(median_error) * 100:.1f}%" if median_error is not None else "–",
                    f"{float(p90_error) * 100:.1f}%" if p90_error is not None else "–",
                    f"{float(bias) * 100:+.1f}%" if bias is not None else "–",
                ),
            )
        self._refresh_quality_segments(quality)
        self._refresh_actual_history(direct)

    def _refresh_quality_segments(self, quality: dict) -> None:
        for segment in quality.get("segments", []):
            median_error = segment.get("median_abs_pct_error")
            p90_error = segment.get("p90_abs_pct_error")
            output_error = segment.get("output_median_abs_pct_error")
            self.segment_tree.insert(
                "", "end", values=(
                    f"{segment.get('codec', '–')} / {segment.get('profile', '–')} / {segment.get('resolution', '–')}",
                    segment.get("count", 0),
                    f"{float(median_error) * 100:.1f}%" if median_error is not None else "–",
                    f"{float(p90_error) * 100:.1f}%" if p90_error is not None else "–",
                    f"{float(output_error) * 100:.1f}%" if output_error is not None else "–",
                ),
            )

    def _refresh_actual_history(self, direct: dict) -> None:
        for entry in direct.get("recent", []):
            prediction = entry.get("prediction", {}) if isinstance(entry.get("prediction"), dict) else {}
            actual = entry.get("actual", {}) if isinstance(entry.get("actual"), dict) else {}
            error = entry.get("error", {}) if isinstance(entry.get("error"), dict) else {}
            segment = entry.get("segment", {}) if isinstance(entry.get("segment"), dict) else {}
            environment = entry.get("environment", {}) if isinstance(entry.get("environment"), dict) else {}
            abs_error = error.get("runtime_abs_pct")
            environment_label = f"{str(environment.get('fingerprint_sha256', 'legacy'))[:8]} / {str(environment.get('epoch_id', 'legacy'))[:12]}"
            self.actual_tree.insert(
                "", "end", values=(
                    str(entry.get("finished_at", "–")).replace("T", " ")[:19],
                    f"{segment.get('codec', '–')} / {segment.get('profile', '–')} / {segment.get('resolution', '–')}",
                    environment_label, _clock(prediction.get("runtime_seconds_p50")), _clock(actual.get("runtime_seconds")),
                    f"{float(abs_error) * 100:.1f}%" if abs_error is not None else "–", prediction.get("confidence", "none"),
                ),
            )

    def _selected(self, tree=None) -> dict | None:
        source = tree or self.plan_tree
        selected = source.selection()
        if not selected:
            return None
        schedule_id = str(selected[0]).removeprefix("op-")
        return self.records.get(schedule_id)

    def _wait_editor(self, record: dict | None, *, replace: bool) -> None:
        child = self.open_editor(record, replace)
        if child is not None:
            self.window.wait_window(child)
        self.refresh()

    def _new(self) -> None:
        self._wait_editor(None, replace=False)

    def _edit_from(self, tree) -> None:
        record = self._selected(tree)
        if record is not None:
            self._wait_editor(record, replace=True)

    def _edit(self) -> None:
        record = self._selected()
        if record is None:
            messagebox.showinfo("Zeitplan auswählen", "Bitte zuerst einen Zeitplan auswählen.", parent=self.window)
            return
        self._wait_editor(record, replace=True)

    def _duplicate(self) -> None:
        record = self._selected()
        if record is None:
            messagebox.showinfo("Zeitplan auswählen", "Bitte zuerst einen Zeitplan auswählen.", parent=self.window)
            return
        self._wait_editor(record, replace=False)

    def _toggle_pause(self) -> None:
        record = self._selected()
        if record is None:
            messagebox.showinfo("Zeitplan auswählen", "Bitte zuerst einen Zeitplan auswählen.", parent=self.window)
            return
        try:
            if str(record.get("status")) == "paused":
                self.resume_schedule(str(record["schedule_id"]))
            else:
                self.pause_schedule(str(record["schedule_id"]))
        except (OSError, ValueError, RuntimeError) as exc:
            messagebox.showerror("Scheduler-Aktion fehlgeschlagen", str(exc), parent=self.window)
        self.refresh()

    def _cancel(self) -> None:
        record = self._selected()
        if record is None:
            messagebox.showinfo("Zeitplan auswählen", "Bitte zuerst einen Zeitplan auswählen.", parent=self.window)
            return
        if not messagebox.askyesno("Zeitplan löschen", "Den ausgewählten Zeitplan wirklich löschen?", parent=self.window):
            return
        self.cancel_schedule(str(record.get("schedule_id", "")))
        self.refresh()

    def _policy(self) -> None:
        self.open_policy()
        self.refresh()

    def _reconcile(self) -> None:
        report = self.reconcile_state()
        messagebox.showinfo(
            "Scheduler-Abgleich",
            f"Geprüft: {report.get('schedules_checked', 0)} · Probleme: {report.get('issues', 0)} · Repariert: {report.get('repaired', 0)}",
            parent=self.window,
        )
        self.refresh()

    def _export(self) -> None:
        try:
            path = self.export_state()
        except (OSError, ValueError) as exc:
            messagebox.showerror("Export fehlgeschlagen", str(exc), parent=self.window)
            return
        if path:
            messagebox.showinfo("Scheduler exportiert", f"Export erstellt:\n{path}", parent=self.window)

    def _cleanup(self) -> None:
        report = self.cleanup_completed()
        messagebox.showinfo("Scheduler aufgeräumt", f"Entfernte abgeschlossene Pläne: {report.get('removed_count', 0)}", parent=self.window)
        self.refresh()
