from __future__ import annotations

from datetime import datetime, timedelta
from tkinter import BooleanVar, StringVar, Toplevel, messagebox, ttk
from zoneinfo import ZoneInfo

from .scheduler_recurrence import local_timezone_name, resolve_local_wall_time

_RECURRENCE_LABELS = {"Einmalig": "once", "Täglich": "daily", "Wöchentlich": "weekly"}
_CATCHUP_LABELS = {"Einmal nachholen": "run_once", "Verspäteten Termin überspringen": "skip"}
_PRIORITY_LABELS = {"Niedrig": 20, "Normal": 50, "Hoch": 80}


class SchedulerDialog:
    def __init__(self, owner, *, on_save, on_cancel=None, active_schedule=None, title: str | None = None) -> None:
        self.owner = owner
        self.on_save = on_save
        self.on_cancel = on_cancel
        self.active_schedule = active_schedule
        self.window = Toplevel(owner.root)
        self.window.title(title or ("Zeitplan bearbeiten" if active_schedule else "Zeitplan anlegen"))
        self.window.transient(owner.root)
        self.window.resizable(False, False)
        self.window.protocol("WM_DELETE_WINDOW", self.window.destroy)

        recurrence = active_schedule.get("recurrence", {}) if isinstance(active_schedule, dict) else {}
        self.timezone_name = str(recurrence.get("timezone") or local_timezone_name())
        default = datetime.now(ZoneInfo(self.timezone_name)) + timedelta(minutes=10)
        if active_schedule:
            raw = active_schedule.get("next_run_at") or active_schedule.get("scheduled_at")
            try:
                default = datetime.fromisoformat(str(raw)).astimezone(ZoneInfo(self.timezone_name))
            except (TypeError, ValueError):
                pass
        kind = str(recurrence.get("kind", "once"))
        reverse_recurrence = {value: label for label, value in _RECURRENCE_LABELS.items()}
        catchup = str(recurrence.get("catch_up_policy", "run_once"))
        reverse_catchup = {value: label for label, value in _CATCHUP_LABELS.items()}
        self.date_value = StringVar(value=default.strftime("%Y-%m-%d"))
        self.time_value = StringVar(value=default.strftime("%H:%M"))
        self.recurrence_value = StringVar(value=reverse_recurrence.get(kind, "Einmalig"))
        self.interval_value = StringVar(value=str(recurrence.get("interval", 1)))
        self.occurrence_value = StringVar(value=str(recurrence.get("max_occurrences", 1 if kind == "once" else 10)))
        self.catchup_value = StringVar(value=reverse_catchup.get(catchup, "Einmal nachholen"))
        self.inhibit_value = BooleanVar(value=bool(active_schedule.get("inhibit_sleep", True)) if active_schedule else True)
        self.after_value = StringVar(value="Energiesparen" if active_schedule and active_schedule.get("after_action") == "suspend" else "Keine")
        self.lateness_value = StringVar(value=str(active_schedule.get("max_lateness_minutes", 180)) if active_schedule else "180")
        current_priority = int(((active_schedule or {}).get("governance") or {}).get("priority", 50))
        priority_label = min(_PRIORITY_LABELS, key=lambda label: abs(_PRIORITY_LABELS[label] - current_priority))
        self.priority_value = StringVar(value=priority_label)
        self.status_value = StringVar(value=self._active_summary())
        self._build()
        self._sync_recurrence_controls()
        self.window.grab_set()
        self.window.focus_set()

    def _active_summary(self) -> str:
        if not self.active_schedule:
            return f"Neuer Zeitplan · Zeitzone {self.timezone_name}"
        return (
            f"Plan {self.active_schedule.get('schedule_id', '–')} · "
            f"Status {self.active_schedule.get('status', '–')} · Zeitzone {self.timezone_name}"
        )

    def _build(self) -> None:
        shell = ttk.Frame(self.window, padding=16)
        shell.pack(fill="both", expand=True)
        ttk.Label(shell, text="Scheduler", style="SectionHeader.TLabel").grid(row=0, column=0, columnspan=2, sticky="w")
        ttk.Label(shell, textvariable=self.status_value, justify="left", wraplength=470).grid(row=1, column=0, columnspan=2, sticky="ew", pady=(4, 12))

        labels = (
            ("Datum (YYYY-MM-DD)", self.date_value),
            ("Uhrzeit (HH:MM)", self.time_value),
        )
        for row, (label, variable) in enumerate(labels, start=2):
            ttk.Label(shell, text=label).grid(row=row, column=0, sticky="w", pady=4)
            ttk.Entry(shell, textvariable=variable, width=20).grid(row=row, column=1, sticky="ew", pady=4)

        ttk.Label(shell, text="Wiederholung").grid(row=4, column=0, sticky="w", pady=4)
        recurrence_combo = ttk.Combobox(shell, textvariable=self.recurrence_value, values=tuple(_RECURRENCE_LABELS), state="readonly", width=25)
        recurrence_combo.grid(row=4, column=1, sticky="ew", pady=4)
        recurrence_combo.bind("<<ComboboxSelected>>", lambda _event: self._sync_recurrence_controls())

        ttk.Label(shell, text="Intervall").grid(row=5, column=0, sticky="w", pady=4)
        self.interval_combo = ttk.Combobox(shell, textvariable=self.interval_value, values=tuple(str(value) for value in range(1, 31)), state="readonly", width=12)
        self.interval_combo.grid(row=5, column=1, sticky="ew", pady=4)
        ttk.Label(shell, text="Maximale Läufe").grid(row=6, column=0, sticky="w", pady=4)
        self.occurrence_combo = ttk.Combobox(shell, textvariable=self.occurrence_value, values=("2", "3", "5", "10", "20", "50", "100", "366"), state="readonly", width=12)
        self.occurrence_combo.grid(row=6, column=1, sticky="ew", pady=4)

        ttk.Label(shell, text="Bei verspätetem Termin").grid(row=7, column=0, sticky="w", pady=4)
        ttk.Combobox(shell, textvariable=self.catchup_value, values=tuple(_CATCHUP_LABELS), state="readonly", width=28).grid(row=7, column=1, sticky="ew", pady=4)
        ttk.Label(shell, text="Catch-up-Fenster (Minuten)").grid(row=8, column=0, sticky="w", pady=4)
        ttk.Combobox(shell, textvariable=self.lateness_value, values=("30", "60", "180", "360", "720", "1440"), state="readonly", width=15).grid(row=8, column=1, sticky="ew", pady=4)
        ttk.Label(shell, text="Priorität").grid(row=9, column=0, sticky="w", pady=4)
        ttk.Combobox(shell, textvariable=self.priority_value, values=tuple(_PRIORITY_LABELS), state="readonly", width=18).grid(row=9, column=1, sticky="ew", pady=4)
        ttk.Checkbutton(shell, text="Schlafmodus während des Renderns verhindern", variable=self.inhibit_value).grid(row=10, column=0, columnspan=2, sticky="w", pady=(8, 4))
        ttk.Label(shell, text="Nach erfolgreichem Lauf").grid(row=11, column=0, sticky="w", pady=4)
        ttk.Combobox(shell, textvariable=self.after_value, values=("Keine", "Energiesparen"), state="readonly", width=18).grid(row=11, column=1, sticky="ew", pady=4)

        note = (
            "Wiederholungen sind absichtlich begrenzt. Nicht existente DST-Uhrzeiten werden übersprungen; "
            "bei der doppelten Winterzeitstunde verwendet VideoBatch deterministisch den späteren Zeitpunkt. "
            "Änderungen an renderrelevanten Quellen blockieren den Plan."
        )
        ttk.Label(shell, text=note, justify="left", wraplength=480).grid(row=12, column=0, columnspan=2, sticky="ew", pady=(10, 12))

        buttons = ttk.Frame(shell)
        buttons.grid(row=13, column=0, columnspan=2, sticky="ew")
        ttk.Button(buttons, text="Speichern", style="Success.TButton", command=self._save).pack(side="left")
        if self.active_schedule and self.on_cancel is not None:
            ttk.Button(buttons, text="Plan löschen", style="Danger.TButton", command=self._cancel).pack(side="left", padx=(6, 0))
        ttk.Button(buttons, text="Schließen", command=self.window.destroy).pack(side="right")
        shell.columnconfigure(1, weight=1)

    def _sync_recurrence_controls(self) -> None:
        recurring = _RECURRENCE_LABELS.get(self.recurrence_value.get(), "once") != "once"
        state = "readonly" if recurring else "disabled"
        self.interval_combo.configure(state=state)
        self.occurrence_combo.configure(state=state)
        if not recurring:
            self.interval_value.set("1")
            self.occurrence_value.set("1")

    def _save(self) -> None:
        try:
            naive = datetime.strptime(
                f"{self.date_value.get().strip()} {self.time_value.get().strip()}",
                "%Y-%m-%d %H:%M",
            )
            when = resolve_local_wall_time(naive.date(), naive.time(), self.timezone_name, dst_policy="later")
            if when is None:
                raise ValueError("Diese lokale Uhrzeit existiert wegen der Sommerzeitumstellung nicht.")
            kind = _RECURRENCE_LABELS.get(self.recurrence_value.get(), "once")
            recurrence = {
                "kind": kind,
                "interval": int(self.interval_value.get()),
                "max_occurrences": int(self.occurrence_value.get()),
                "catch_up_policy": _CATCHUP_LABELS.get(self.catchup_value.get(), "run_once"),
                "timezone": self.timezone_name,
                "dst_policy": "later",
            }
            self.on_save(
                when,
                inhibit_sleep=bool(self.inhibit_value.get()),
                after_action="suspend" if self.after_value.get() == "Energiesparen" else "none",
                max_lateness_minutes=int(self.lateness_value.get()),
                recurrence=recurrence,
                timezone_name=self.timezone_name,
                priority=_PRIORITY_LABELS.get(self.priority_value.get(), 50),
            )
        except ValueError as exc:
            messagebox.showerror("Zeitplan ungültig", str(exc), parent=self.window)
            return
        self.window.destroy()

    def _cancel(self) -> None:
        if not self.active_schedule or self.on_cancel is None:
            return
        if not messagebox.askyesno("Plan löschen", "Diesen Zeitplan wirklich löschen?", parent=self.window):
            return
        self.on_cancel(str(self.active_schedule.get("schedule_id", "")))
        self.window.destroy()
