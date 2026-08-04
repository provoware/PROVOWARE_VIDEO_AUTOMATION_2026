from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from tkinter import StringVar, Toplevel, ttk
from typing import Any

ENTRY_TYPE_LABELS = {
    "note": "Notiz",
    "task": "Aufgabe",
    "reminder": "Erinnerung",
    "deadline": "Termin",
    "appointment": "Termin",
}
COLOR_LABELS = {
    "none": "Neutral",
    "success": "Erledigt",
    "warning": "Beachten",
    "error": "Blockiert",
    "info": "Information",
    "active": "Aktiv",
}
FILTER_LABELS = {
    "all": "Alle Einträge",
    "today": "Heute",
    "week": "Nächste 7 Tage",
    "month": "Aktueller Monat",
    "tasks": "Nur Aufgaben",
    "appointments": "Nur Termine",
    "open": "Offen / aktiv",
}


@dataclass(frozen=True, slots=True)
class CalendarTask:
    date_key: str
    day: date
    entry_type: str
    color: str
    note: str

    @property
    def type_label(self) -> str:
        return ENTRY_TYPE_LABELS.get(self.entry_type, self.entry_type)

    @property
    def status_label(self) -> str:
        return COLOR_LABELS.get(self.color, self.color)


def collect_calendar_tasks(notes: dict[str, Any]) -> list[CalendarTask]:
    tasks: list[CalendarTask] = []
    for date_key, raw in notes.items():
        if not isinstance(raw, dict):
            continue
        try:
            day = datetime.strptime(str(date_key), "%Y-%m-%d").date()
        except ValueError:
            continue
        note = str(raw.get("note", "") or "").strip()
        if not note:
            continue
        tasks.append(CalendarTask(str(date_key), day, str(raw.get("entry_type", "note")), str(raw.get("color", "none")), note))
    return sorted(tasks, key=lambda item: (item.day, item.entry_type, item.note.casefold()))


def filter_calendar_tasks(tasks: list[CalendarTask], mode: str, today: date | None = None) -> list[CalendarTask]:
    current = today or date.today()
    if mode == "today":
        return [item for item in tasks if item.day == current]
    if mode == "week":
        end = current + timedelta(days=6)
        return [item for item in tasks if current <= item.day <= end]
    if mode == "month":
        return [item for item in tasks if item.day.year == current.year and item.day.month == current.month]
    if mode == "tasks":
        return [item for item in tasks if item.entry_type == "task"]
    if mode == "appointments":
        return [item for item in tasks if item.entry_type in {"deadline", "appointment"}]
    if mode == "open":
        return [item for item in tasks if item.color in {"none", "warning", "error", "info", "active"}]
    return list(tasks)


class CalendarTaskOverview:
    def __init__(self, parent, notes: dict[str, Any], *, modal: bool = True) -> None:
        self.notes = notes
        self.tasks = collect_calendar_tasks(notes)
        self.window = Toplevel(parent)
        self.window.title("Kalender · Aufgabenübersicht")
        self.window.geometry("900x620")
        self.window.minsize(720, 460)
        self.window.transient(parent)
        if modal:
            self.window.grab_set()
        outer = ttk.Frame(self.window, padding=14)
        outer.pack(fill="both", expand=True)
        ttk.Label(outer, text="Aufgaben, Termine und Erinnerungen", style="DialogTitle.TLabel").pack(anchor="w")
        ttk.Label(outer, text="Die kompakte Monatsansicht bleibt unverändert. Hier werden gespeicherte Kalendereinträge filterbar zusammengefasst.", style="Hint.TLabel", wraplength=840).pack(anchor="w", pady=(3, 10))
        filter_row = ttk.Frame(outer)
        filter_row.pack(fill="x")
        ttk.Label(filter_row, text="Ansicht:").pack(side="left")
        self.filter_var = StringVar(value=FILTER_LABELS["all"])
        combo = ttk.Combobox(filter_row, textvariable=self.filter_var, values=list(FILTER_LABELS.values()), state="readonly", width=24)
        combo.pack(side="left", padx=6)
        combo.bind("<<ComboboxSelected>>", lambda _event: self.refresh())
        self.summary = StringVar(value="")
        ttk.Label(filter_row, textvariable=self.summary, style="Status.TLabel").pack(side="right")
        self.tree = ttk.Treeview(outer, columns=("date", "type", "status", "note"), show="headings", height=16)
        for key, label, width in (
            ("date", "Datum", 110),
            ("type", "Typ", 120),
            ("status", "Status", 130),
            ("note", "Notiz / Auftrag / Erinnerung", 500),
        ):
            self.tree.heading(key, text=label)
            self.tree.column(key, width=width, stretch=key == "note")
        self.tree.pack(fill="both", expand=True, pady=(10, 8))
        actions = ttk.Frame(outer)
        actions.pack(fill="x")
        ttk.Button(actions, text="Schließen", command=self.window.destroy).pack(side="right")
        self.refresh()

    def refresh(self) -> None:
        reverse = {label: key for key, label in FILTER_LABELS.items()}
        mode = reverse.get(self.filter_var.get(), "all")
        rows = filter_calendar_tasks(self.tasks, mode)
        self.tree.delete(*self.tree.get_children())
        for item in rows:
            self.tree.insert("", "end", values=(item.day.strftime("%d.%m.%Y"), item.type_label, item.status_label, item.note))
        self.summary.set(f"{len(rows)} von {len(self.tasks)} Einträgen")
