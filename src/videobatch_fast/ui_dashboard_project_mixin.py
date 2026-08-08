from __future__ import annotations

import calendar as calendar_module
from datetime import datetime
from pathlib import Path
from tkinter import Canvas, StringVar, Toplevel, filedialog, messagebox, ttk

from .calendar_tasks import CalendarTaskOverview
from .project_state import CALENDAR_ENTRY_TYPES, DEFAULT_CALENDAR_COLORS, default_project_file, load_project_state, save_project_state
from .text_resources import text
from .theme import COLORS
from .versioning import build_label


class UiDashboardProjectMixin:
    def _build_header(self, parent) -> None:
        header = ttk.Frame(parent, style="Header.TFrame", padding=10)
        header.pack(fill="x")
        header.columnconfigure(0, weight=5)
        header.columnconfigure(1, weight=3)

        left = ttk.Frame(header, style="Header.TFrame")
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        title_row = ttk.Frame(left, style="Header.TFrame")
        title_row.pack(fill="x")
        ttk.Label(title_row, text=text("app.title"), style="Title.TLabel").pack(side="left")
        ttk.Label(title_row, text=f"Version {build_label()}", style="VersionBadge.TLabel").pack(side="left", padx=(12, 0))
        ttk.Label(left, text=text("app.subtitle"), style="Subtitle.TLabel", wraplength=700).pack(anchor="w")

        note_row = ttk.Frame(left, style="Header.TFrame")
        note_row.pack(fill="x", pady=(7, 0))
        ttk.Label(note_row, textvariable=self.project_name, style="Section.TLabel").pack(side="left", padx=(0, 6))
        ttk.Entry(note_row, textvariable=self.quick_note).pack(side="left", fill="x", expand=True)
        ttk.Button(note_row, text=text("header.save_note"), style="Accent.TButton", command=self._save_quick_note).pack(side="left", padx=(6, 6))
        ttk.Label(note_row, textvariable=self.datetime_text, style="Status.TLabel").pack(side="right")

        status_row = ttk.Frame(left, style="Header.TFrame")
        status_row.pack(fill="x", pady=(5, 0))
        ttk.Label(status_row, textvariable=self.status_text, style="StatusPill.TLabel", wraplength=500).pack(side="left")
        ttk.Button(status_row, text=text('ui.dashboard_project.plugin_freigaben'), command=self._manage_plugin_approvals).pack(side="right")

        right = ttk.Frame(header, style="Header.TFrame", padding=(6, 2))
        right.grid(row=0, column=1, sticky="nsew")
        self._build_calendar(right)

    def _build_calendar(self, parent) -> None:
        top = ttk.Frame(parent, style="Header.TFrame")
        top.pack(fill="x")
        ttk.Button(top, text=text('ui.dashboard_project.symbol'), width=3, command=lambda: self._shift_calendar(-1)).pack(side="left")
        ttk.Label(top, textvariable=self.calendar_title, style="Status.TLabel").pack(side="left", fill="x", expand=True)
        ttk.Button(top, text=text('ui.dashboard_project.aufgaben'), command=self._open_calendar_overview).pack(side="right", padx=(4, 0))
        ttk.Button(top, text=text('ui.dashboard_project.symbol_2'), width=3, command=lambda: self._shift_calendar(1)).pack(side="right")
        self.calendar_canvas = Canvas(
            parent,
            height=154,
            background=COLORS["panel"],
            highlightbackground=COLORS["border"],
            highlightthickness=1,
            borderwidth=0,
        )
        self.calendar_canvas.pack(fill="x", pady=(4, 0))
        self.calendar_canvas.bind("<Configure>", lambda _event: self._refresh_calendar())
        self._refresh_calendar()


    def _open_calendar_overview(self) -> None:
        CalendarTaskOverview(self.root, self.calendar_notes)
        self._event(
            "CALENDAR_OVERVIEW_OPENED",
            "Kalenderübersicht geöffnet",
            f"{len(self.calendar_notes)} gespeicherte Kalendertage",
            solution="Ansicht nach Tag, Woche, Monat, Aufgaben oder Terminen filtern.",
        )

    def _refresh_calendar(self) -> None:
        if not hasattr(self, "calendar_canvas"):
            return
        self.calendar_title.set(f"{calendar_module.month_name[self.calendar_month]} {self.calendar_year}")
        canvas = self.calendar_canvas
        canvas.delete("all")
        width = max(280, canvas.winfo_width() or 360)
        height = 154
        cell_w = width / 7.0
        header_h = 20
        row_h = (height - header_h) / 6.0
        for col, label in enumerate(("Mo", "Di", "Mi", "Do", "Fr", "Sa", "So")):
            x = col * cell_w + cell_w / 2
            canvas.create_text(x, header_h / 2, text=label, fill=COLORS["muted"], font=("DejaVu Sans", 9, "bold"))
        matrix = calendar_module.monthcalendar(self.calendar_year, self.calendar_month)
        while len(matrix) < 6:
            matrix.append([0] * 7)
        color_map = {
            "none": COLORS["panel"],
            "success": COLORS["success"],
            "warning": COLORS["warning"],
            "error": COLORS["danger"],
            "info": COLORS["accent2"],
            "active": COLORS["active"],
        }
        dark_text_marks = {"success", "warning", "error", "info", "active"}
        for row in range(6):
            for col in range(7):
                day = matrix[row][col]
                x0 = col * cell_w + 1
                y0 = header_h + row * row_h + 1
                x1 = (col + 1) * cell_w - 1
                y1 = header_h + (row + 1) * row_h - 1
                if not day:
                    continue
                date_key = f"{self.calendar_year:04d}-{self.calendar_month:02d}-{day:02d}"
                mark = self.calendar_marks.get(date_key, "none")
                tag = f"day:{date_key}"
                canvas.create_rectangle(x0, y0, x1, y1, fill=color_map.get(mark, COLORS["panel"]), outline=COLORS["border"], tags=(tag, "calendar_day"))
                text_color = "#10140d" if mark in dark_text_marks else COLORS["text"]
                note_entry = self.calendar_notes.get(date_key, {})
                if str(note_entry.get("note", "")).strip():
                    canvas.create_oval(x1 - 8, y0 + 3, x1 - 3, y0 + 8, fill=COLORS["accent"], outline="", tags=(tag, "calendar_day"))
                canvas.create_text((x0 + x1) / 2, (y0 + y1) / 2, text=str(day), fill=text_color, font=("DejaVu Sans", 9), tags=(tag, "calendar_day"))
                canvas.tag_bind(tag, "<Button-1>", lambda _event, key=date_key: self._open_calendar_day(key))
                canvas.tag_bind(tag, "<Enter>", lambda event, key=date_key: self._show_calendar_tooltip(event, key))
                canvas.tag_bind(tag, "<Leave>", lambda _event: self._hide_calendar_tooltip())

    def _show_calendar_tooltip(self, event, date_key: str) -> None:
        self._hide_calendar_tooltip()
        entry = self.calendar_notes.get(date_key, {})
        note = str(entry.get("note", "")).strip() or "Keine Notiz gespeichert."
        entry_type = str(entry.get("entry_type", "note"))
        mark = str(entry.get("color", self.calendar_marks.get(date_key, "none")))
        window = Toplevel(self.root)
        window.overrideredirect(True)
        window.attributes("-topmost", True)
        window.geometry(f"+{event.x_root + 12}+{event.y_root + 12}")
        frame = ttk.Frame(window, style="Card.TFrame", padding=8)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text=date_key, style="Section.TLabel").pack(anchor="w")
        ttk.Label(frame, text=f"Typ: {entry_type} · Markierung: {mark}", style="Hint.TLabel").pack(anchor="w")
        ttk.Label(frame, text=note, style="Hint.TLabel", wraplength=320, justify="left").pack(anchor="w", pady=(4, 0))
        self._calendar_tooltip = window

    def _hide_calendar_tooltip(self) -> None:
        window = getattr(self, "_calendar_tooltip", None)
        if window is not None:
            try:
                window.destroy()
            except Exception:
                pass
        self._calendar_tooltip = None

    def _open_calendar_day(self, date_key: str) -> None:
        self._hide_calendar_tooltip()
        current = dict(self.calendar_notes.get(date_key, {}))
        dialog = Toplevel(self.root)
        dialog.title(f"Kalendertag · {date_key}")
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.resizable(False, False)
        body = ttk.Frame(dialog, style="Card.TFrame", padding=14)
        body.pack(fill="both", expand=True)
        ttk.Label(body, text=f"Notiz für {date_key}", style="Section.TLabel").pack(anchor="w")
        ttk.Label(body, text=text('ui.dashboard_project.wahle_typ_und_farbe_die_eingabe_wird_in'), style="Hint.TLabel", wraplength=430).pack(anchor="w", pady=(3, 10))
        type_labels = {"note": "Notiz", "task": "Aufgabe", "reminder": "Erinnerung", "deadline": "Termin"}
        color_labels = {"none": "Neutral", "success": "Erledigt / Erfolg", "warning": "Beachten", "error": "Blockiert", "info": "Information", "active": "Aktiv"}
        reverse_types = {value: key for key, value in type_labels.items()}
        reverse_colors = {value: key for key, value in color_labels.items()}
        type_var = StringVar(value=type_labels.get(str(current.get("entry_type", "note")), "Notiz"))
        color_var = StringVar(value=color_labels.get(str(current.get("color", self.calendar_marks.get(date_key, "none"))), "Neutral"))
        note_var = StringVar(value=str(current.get("note", "")))
        ttk.Label(body, text=text('ui.dashboard_project.art')).pack(anchor="w")
        ttk.Combobox(body, textvariable=type_var, values=list(type_labels.values()), state="readonly").pack(fill="x", pady=(2, 7))
        ttk.Label(body, text=text('ui.dashboard_project.markierung')).pack(anchor="w")
        ttk.Combobox(body, textvariable=color_var, values=list(color_labels.values()), state="readonly").pack(fill="x", pady=(2, 7))
        ttk.Label(body, text=text('ui.dashboard_project.kurze_notiz')).pack(anchor="w")
        entry = ttk.Entry(body, textvariable=note_var, width=58)
        entry.pack(fill="x", pady=(2, 10))
        entry.focus_set()
        actions = ttk.Frame(body, style="Card.TFrame")
        actions.pack(fill="x")

        def save() -> None:
            note = note_var.get().strip()[:500]
            entry_type = reverse_types.get(type_var.get(), "note")
            color = reverse_colors.get(color_var.get(), "none")
            if note or color != "none":
                self.calendar_notes[date_key] = {"note": note, "entry_type": entry_type, "color": color}
            else:
                self.calendar_notes.pop(date_key, None)
            if color == "none":
                self.calendar_marks.pop(date_key, None)
            else:
                self.calendar_marks[date_key] = color
            self._refresh_calendar()
            self._autosave_project(force=True)
            self._event("CALENDAR_NOTE_SAVED", "Kalendernotiz gespeichert", f"{date_key} · {type_labels[entry_type]}", level="success", solution="Notiz ist beim nächsten Projektstart wieder verfügbar.")
            dialog.destroy()

        def remove() -> None:
            self.calendar_notes.pop(date_key, None)
            self.calendar_marks.pop(date_key, None)
            self._refresh_calendar()
            self._autosave_project(force=True)
            self._event("CALENDAR_NOTE_REMOVED", "Kalendernotiz entfernt", date_key, level="success", solution="Keine weitere Aktion nötig.")
            dialog.destroy()

        ttk.Button(actions, text=text('ui.dashboard_project.notiz_loschen'), style="Danger.TButton", command=remove).pack(side="left")
        ttk.Button(actions, text=text('ui.dashboard_project.abbrechen'), command=dialog.destroy).pack(side="right")
        ttk.Button(actions, text=text('ui.dashboard_project.speichern'), style="Accent.TButton", command=save).pack(side="right", padx=(0, 6))
        dialog.bind("<Return>", lambda _event: save())
        dialog.bind("<Escape>", lambda _event: dialog.destroy())

    def _shift_calendar(self, delta: int) -> None:
        month = self.calendar_month + delta
        year = self.calendar_year
        while month < 1:
            year -= 1
            month += 12
        while month > 12:
            year += 1
            month -= 12
        self.calendar_year, self.calendar_month = year, month
        self._refresh_calendar()
        self._autosave_project()

    def _build_prototype_panel(self, parent) -> None:
        shell = ttk.Frame(parent, style="GoldCard.TFrame", padding=9)
        shell.pack(fill="x", pady=(8, 0))
        top = ttk.Frame(shell, style="Card.TFrame")
        top.pack(fill="x")
        ttk.Label(top, text=text("header.question"), style="Section.TLabel").pack(side="left")
        ttk.Button(top, text=text("header.help"), style="Ghost.TButton", command=self._show_help_center).pack(side="right")

        tiles = ttk.Frame(shell, style="Card.TFrame")
        tiles.pack(fill="x", pady=(6, 0))
        for column in range(4):
            tiles.columnconfigure(column, weight=1)
        self._tile(tiles, 0, 0, "＋\n" + text("project.new") + "\nSchnell starten", self._new_project, "TileGold.TButton")
        self._tile(tiles, 0, 1, "◆\n" + text("project.save") + "\nStand sichern", self._save_project_dialog, "TilePink.TButton")
        self._tile(tiles, 0, 2, "✓\n" + text("header.save_note") + "\nInfo merken", self._save_quick_note, "TileGreen.TButton")
        self._tile(tiles, 0, 3, "▶\n" + text("project.audio") + "\nDirekt vorhören", self._play_playlist, "TileBlue.TButton")

        middle = ttk.Frame(shell, style="Card.TFrame")
        middle.pack(fill="x", pady=(6, 0))
        middle.columnconfigure(0, weight=3)
        middle.columnconfigure(1, weight=2)

        assistant = ttk.Frame(middle, style="Card.TFrame", padding=7)
        assistant.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        ttk.Label(assistant, text=text("prototype.assistant_title"), style="SectionHeader.TLabel").pack(anchor="w")
        ttk.Label(assistant, text=text("prototype.assistant_body"), style="Hint.TLabel").pack(anchor="w", pady=(2, 6))
        assistant_body = "✓ 1. Projekt anlegen oder öffnen\n✓ 2. Audio und Medien prüfen\n✓ 3. Schnellmodus und Ausgabe starten"
        ttk.Label(assistant, text=assistant_body, style="Hint.TLabel", justify="left").pack(anchor="w")
        ttk.Label(assistant, text=text('ui.dashboard_project.erweiterungsflache_frei_assistent_plugins_status'), style="Hint.TLabel").pack(anchor="w", pady=(3, 0))

        tips = ttk.Frame(middle, style="Card.TFrame", padding=7)
        tips.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        ttk.Label(tips, text=text("prototype.tips_title"), style="SectionHeader.TLabel").pack(anchor="w")
        tips_body = "• Projekt regelmäßig speichern\n• Vorschau groß prüfen\n• Plugins nur signiert aktivieren"
        ttk.Label(tips, text=tips_body, style="Hint.TLabel", justify="left").pack(anchor="w", pady=(4, 0))
        ttk.Label(tips, text=text('ui.dashboard_project.erweiterungsflache_frei_hilfe_recovery_prufung'), style="Hint.TLabel").pack(anchor="w", pady=(3, 0))

        quick = ttk.Frame(shell, style="Card.TFrame")
        quick.pack(fill="x", pady=(6, 0))
        for column in range(4):
            quick.columnconfigure(column, weight=1)
        ttk.Button(quick, text=text("prototype.quick_help"), style="Ghost.TButton", command=self._show_help_center).grid(row=0, column=0, sticky="ew", padx=3)
        ttk.Button(quick, text=text("prototype.quick_random"), style="Ghost.TButton", command=lambda: self.guidance_text.set("Zufalls-Idee: Erst ein kleines Testprojekt mit 2 Dateien starten.")).grid(row=0, column=1, sticky="ew", padx=3)
        ttk.Button(quick, text=text("prototype.quick_templates"), style="Ghost.TButton", command=self._open_project_file).grid(row=0, column=2, sticky="ew", padx=3)
        ttk.Button(quick, text=text("prototype.quick_settings"), style="Ghost.TButton", command=self._open_settings).grid(row=0, column=3, sticky="ew", padx=3)

    def _tile(self, parent, row: int, column: int, label: str, command, style: str) -> None:
        ttk.Button(parent, text=label, style=style, command=command).grid(row=row, column=column, sticky="nsew", padx=4, pady=4)

    def _update_clock(self) -> None:
        self.datetime_text.set(datetime.now().strftime("%d.%m.%Y · %H:%M:%S"))
        self.root.after(1000, self._update_clock)

    def _collect_project_state(self) -> dict:
        return {
            "project_name": self.project_name.get().strip() or "Neues Projekt",
            "quick_note": self.quick_note.get(),
            "audio_paths": [str(path) for path in self.audios],
            "media_paths": [str(path) for path in self.media],
            "media_tags": dict(getattr(self, "media_tags", {})),
            "playlist_paths": [str(path) for path in self.playlist.items],
            "output_dir": self.output_dir.get(),
            "quick_mode": self.quick_mode.get(),
            "assignment_mode": self.assignment_mode.get(),
            "slideshow_transition": self.slideshow_transition.get(),
            "slideshow_scene_sync": self.slideshow_scene_sync.get(),
            "slideshow_order_mode": self.slideshow_order_mode.get(),
            "slideshow_random_seed": self.slideshow_random_seed.get(),
            "slideshow_start_image": self.slideshow_start_image.get(),
            "slideshow_end_image": self.slideshow_end_image.get(),
            "audio_sort": self.audio_sort.get(),
            "media_sort": self.media_sort.get(),
            "archive_used": self.archive_used.get(),
            "archive_project_dir": self.archive_project_dir.get(),
            "archive_suffix": self.archive_suffix.get(),
            "calendar_year": self.calendar_year,
            "calendar_month": self.calendar_month,
            "calendar_marks": dict(self.calendar_marks),
            "calendar_notes": dict(self.calendar_notes),
            "workspace_layout_profiles": dict(self.workspace_layout_profiles),
            "meta": {"updated_by": f"provoware - videoautomation - 2026 · {build_label()}"},
        }

    def _apply_project_state(self, state: dict) -> None:
        self.project_name.set(str(state.get("project_name", "Neues Projekt") or "Neues Projekt"))
        self.quick_note.set(str(state.get("quick_note", "") or ""))
        self.output_dir.set(str(state.get("output_dir", self.output_dir.get()) or self.output_dir.get()))
        self.quick_mode.set(str(state.get("quick_mode", self.quick_mode.get()) or self.quick_mode.get()))
        self.assignment_mode.set(str(state.get("assignment_mode", self.assignment_mode.get()) or self.assignment_mode.get()))
        self.slideshow_transition.set(str(state.get("slideshow_transition", self.slideshow_transition.get()) or self.slideshow_transition.get()))
        self.slideshow_scene_sync.set(bool(state.get("slideshow_scene_sync", self.slideshow_scene_sync.get())))
        self.slideshow_order_mode.set(str(state.get("slideshow_order_mode", self.slideshow_order_mode.get()) or self.slideshow_order_mode.get()))
        self.slideshow_random_seed.set(int(state.get("slideshow_random_seed", self.slideshow_random_seed.get()) or 0))
        self.slideshow_start_image.set(str(state.get("slideshow_start_image", self.slideshow_start_image.get()) or ""))
        self.slideshow_end_image.set(str(state.get("slideshow_end_image", self.slideshow_end_image.get()) or ""))
        if hasattr(self, "slideshow_transition_combo"):
            self.slideshow_transition_combo.set(self.slideshow_transition_display.get(self.slideshow_transition.get(), self.slideshow_transition_display.get("auto", "")))
        self.audio_sort.set(str(state.get("audio_sort", self.audio_sort.get()) or self.audio_sort.get()))
        self.media_sort.set(str(state.get("media_sort", self.media_sort.get()) or self.media_sort.get()))
        self.archive_used.set(bool(state.get("archive_used", self.archive_used.get())))
        self.archive_project_dir.set(str(state.get("archive_project_dir", self.archive_project_dir.get()) or self.archive_project_dir.get()))
        self.archive_suffix.set(str(state.get("archive_suffix", self.archive_suffix.get()) or self.archive_suffix.get()))
        self.calendar_year = int(state.get("calendar_year", self.calendar_year))
        self.calendar_month = int(state.get("calendar_month", self.calendar_month))
        self.calendar_marks = dict(state.get("calendar_marks", self.calendar_marks))
        self.calendar_notes = dict(state.get("calendar_notes", self.calendar_notes))
        self.media_tags = {key: list(value) for key, value in state.get("media_tags", {}).items()}
        self._initialize_workspace_layout_store(state.get("workspace_layout_profiles", {}))
        self.audios = [Path(item) for item in state.get("audio_paths", [])]
        self.media = [Path(item) for item in state.get("media_paths", [])]
        self.playlist.items = [Path(item) for item in state.get("playlist_paths", [])]
        self.playlist.current = 0 if self.playlist.items else -1
        self._refresh_calendar()
        self._refresh_file_trees()
        self._rebuild_pairs()
        self._refresh_playlist()
        self.root.after_idle(self._restore_workspace_layout_profile)

    def _autosave_project(self, force: bool = False, capture_layout: bool = True) -> None:
        if not force and self.runner.running:
            return
        if capture_layout and hasattr(self, "_capture_workspace_layout_profile"):
            self._capture_workspace_layout_profile()
        self.project_name.set(self.project_name.get().strip() or "Neues Projekt")
        save_project_state(self.project_file, self._collect_project_state())
        self.project_dirty = False

    def _save_project_dialog(self) -> None:
        selected = filedialog.asksaveasfilename(
            title=text('ui.dashboard_project.projektdatei_speichern'),
            defaultextension=".vbfast.json",
            initialfile=Path(self.project_file).name,
            filetypes=[("VideoBatch-Projekt", "*.vbfast.json"), ("JSON", "*.json")],
        )
        if not selected:
            return
        self.project_file = Path(selected).expanduser()
        self._autosave_project(force=True)
        self.guidance_text.set(f"Projekt gespeichert: {self.project_file.name}")
        self._event("PROJECT_SAVED", "Projekt gespeichert", str(self.project_file), level="success", solution="Projekt kann jetzt jederzeit wieder geöffnet werden.")

    def _open_project_file(self) -> None:
        selected = filedialog.askopenfilename(title=text('ui.dashboard_project.projektdatei_offnen'), filetypes=[("VideoBatch-Projekt", "*.vbfast.json"), ("JSON", "*.json")])
        if not selected:
            return
        self.project_file = Path(selected).expanduser()
        _path, state, healed = load_project_state(self.project_file)
        self._apply_project_state(state)
        self.guidance_text.set(f"Projekt geöffnet: {self.project_file.name}")
        self._event("PROJECT_OPENED", "Projekt geöffnet", str(self.project_file), level="success", solution="Dateilisten, Kalender und Notizen wurden wiederhergestellt.")
        if healed:
            self._event("PROJECT_HEALED", "Projektdatei repariert", "Die gewählte Projektdatei war beschädigt und wurde sicher zurückgesetzt.", level="warning", solution="Projektinhalt kurz prüfen.")

    def _new_project(self) -> None:
        self.audio_player.stop()
        self.project_file = default_project_file()
        self.project_state = {"project_name": "Neues Projekt"}
        self.calendar_marks = {}
        self.calendar_notes = {}
        self.media_tags = {}
        self._clear_workspace_layout_profiles()
        self.calendar_year = datetime.now().year
        self.calendar_month = datetime.now().month
        self.project_name.set("Neues Projekt")
        self.quick_note.set("")
        self.playlist.items = []
        self.playlist.current = -1
        self._clear_lists()
        self._refresh_playlist()
        self._refresh_calendar()
        self._autosave_project(force=True)
        self.guidance_text.set("Neues Projekt angelegt. Jetzt Dateien hinzufügen oder Notizen speichern.")
        self._event("PROJECT_NEW", "Neues Projekt angelegt", str(self.project_file), level="success", solution="Dateien auswählen oder bestehendes Projekt öffnen.")

    def _save_quick_note(self) -> None:
        self._autosave_project(force=True)
        self.guidance_text.set("Entwickler-Info wurde in der Projektdatei gespeichert.")
        self._event("PROJECT_NOTE_SAVED", "Entwickler-Info gespeichert", self.quick_note.get()[:120] or "Leere Notiz gespeichert", level="success", solution="Info kann beim nächsten Start automatisch wiederhergestellt werden.")
