from __future__ import annotations

from tkinter import StringVar, Toplevel, messagebox, ttk

from .scheduler_policy import load_scheduler_policy, save_scheduler_policy
from .scheduler_recurrence import local_timezone_name

_DAY_PRESETS = {
    "Täglich": list(range(7)),
    "Mo–Fr": [0, 1, 2, 3, 4],
    "Sa–So": [5, 6],
}


class SchedulerPolicyDialog:
    def __init__(self, owner, *, on_saved=None) -> None:
        self.owner = owner
        self.on_saved = on_saved
        self.policy = load_scheduler_policy()
        self.windows = list(self.policy.get("blackout_windows", []))
        self.window = Toplevel(owner.root)
        self.window.title("Scheduler-Betriebsregeln")
        self.window.transient(owner.root)
        self.window.geometry("720x520")
        self.window.minsize(640, 460)
        self.min_free_value = StringVar(value=str(int(self.policy.get("min_free_output_bytes", 0)) // (1024 * 1024)))
        self.retry_value = StringVar(value=str(self.policy.get("conflict_retry_minutes", 5)))
        self.label_value = StringVar(value="Wartungsfenster")
        self.start_value = StringVar(value="02:00")
        self.end_value = StringVar(value="05:00")
        self.days_value = StringVar(value="Täglich")
        self._build()
        self._refresh_windows()
        self.window.grab_set()
        self.window.focus_set()

    def _build(self) -> None:
        shell = ttk.Frame(self.window, padding=14)
        shell.pack(fill="both", expand=True)
        ttk.Label(shell, text="Scheduler-Betriebsregeln", style="SectionHeader.TLabel").pack(anchor="w")
        ttk.Label(
            shell,
            text="Globale Regeln gelten für alle geplanten Renderläufe. Parallelität bleibt sicher auf einen Renderprozess begrenzt.",
            style="Hint.TLabel", wraplength=670, justify="left",
        ).pack(anchor="w", pady=(3, 10))
        resources = ttk.LabelFrame(shell, text="Ressourcen & Queue", padding=8)
        resources.pack(fill="x")
        ttk.Label(resources, text="Mindestens freier Speicher (MiB)").grid(row=0, column=0, sticky="w", pady=3)
        ttk.Entry(resources, textvariable=self.min_free_value, width=12).grid(row=0, column=1, sticky="w", padx=(8, 20))
        ttk.Label(resources, text="Queue-Prüfintervall (Minuten)").grid(row=0, column=2, sticky="w", pady=3)
        ttk.Combobox(resources, textvariable=self.retry_value, values=("1", "2", "5", "10", "15", "30", "60"), state="readonly", width=8).grid(row=0, column=3, sticky="w", padx=(8, 0))

        maintenance = ttk.LabelFrame(shell, text="Blackout-/Wartungsfenster", padding=8)
        maintenance.pack(fill="both", expand=True, pady=(10, 0))
        self.tree = ttk.Treeview(maintenance, columns=("label", "days", "time", "tz"), show="headings", height=7)
        for key, label, width in (("label", "Bezeichnung", 180), ("days", "Tage", 100), ("time", "Zeit", 130), ("tz", "Zeitzone", 150)):
            self.tree.heading(key, text=label)
            self.tree.column(key, width=width, anchor="w")
        self.tree.pack(fill="both", expand=True)
        form = ttk.Frame(maintenance)
        form.pack(fill="x", pady=(8, 0))
        ttk.Entry(form, textvariable=self.label_value, width=20).pack(side="left")
        ttk.Combobox(form, textvariable=self.days_value, values=tuple(_DAY_PRESETS), state="readonly", width=10).pack(side="left", padx=5)
        ttk.Entry(form, textvariable=self.start_value, width=7).pack(side="left")
        ttk.Label(form, text="bis").pack(side="left", padx=4)
        ttk.Entry(form, textvariable=self.end_value, width=7).pack(side="left")
        ttk.Button(form, text="＋ Fenster", command=self._add_window).pack(side="left", padx=(8, 0))
        ttk.Button(form, text="Entfernen", command=self._remove_window).pack(side="left", padx=(5, 0))
        buttons = ttk.Frame(shell)
        buttons.pack(fill="x", pady=(10, 0))
        ttk.Button(buttons, text="Speichern", style="Success.TButton", command=self._save).pack(side="left")
        ttk.Button(buttons, text="Schließen", command=self.window.destroy).pack(side="right")

    def _refresh_windows(self) -> None:
        for item in self.tree.get_children():
            self.tree.delete(item)
        reverse = {tuple(days): label for label, days in _DAY_PRESETS.items()}
        for index, window in enumerate(self.windows):
            days = reverse.get(tuple(window.get("days", [])), ",".join(str(value) for value in window.get("days", [])))
            self.tree.insert("", "end", iid=str(index), values=(
                window.get("label", "Wartungsfenster"), days,
                f"{window.get('start', '–')}–{window.get('end', '–')}", window.get("timezone", "–"),
            ))

    def _add_window(self) -> None:
        candidate = {
            "label": self.label_value.get().strip() or "Wartungsfenster",
            "days": _DAY_PRESETS.get(self.days_value.get(), list(range(7))),
            "start": self.start_value.get().strip(),
            "end": self.end_value.get().strip(),
            "timezone": local_timezone_name(),
        }
        try:
            from .scheduler_policy import normalize_blackout_window
            candidate = normalize_blackout_window(candidate)
        except ValueError as exc:
            messagebox.showerror("Wartungsfenster ungültig", str(exc), parent=self.window)
            return
        self.windows.append(candidate)
        self._refresh_windows()

    def _remove_window(self) -> None:
        selected = self.tree.selection()
        if not selected:
            return
        index = int(selected[0])
        if 0 <= index < len(self.windows):
            self.windows.pop(index)
            self._refresh_windows()

    def _save(self) -> None:
        try:
            minimum = int(self.min_free_value.get()) * 1024 * 1024
            retry = int(self.retry_value.get())
            save_scheduler_policy({
                "schema_version": 1,
                "max_parallel_renders": 1,
                "min_free_output_bytes": minimum,
                "conflict_retry_minutes": retry,
                "blackout_windows": self.windows,
            })
        except (ValueError, OSError) as exc:
            messagebox.showerror("Betriebsregeln ungültig", str(exc), parent=self.window)
            return
        if self.on_saved is not None:
            self.on_saved()
        self.window.destroy()
