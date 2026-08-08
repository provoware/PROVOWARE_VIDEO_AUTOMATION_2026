from __future__ import annotations

from tkinter import StringVar, TclError, ttk

from .startup_readiness import StartupStep, build_startup_readiness
from .theme import COLORS, best_text_color, safe_text_color


class CanonicalStartCheckMixin:
    """Visible start guidance backed by the existing preparation checks."""

    _START_KEYS = ("project", "media", "effects", "output", "pairing", "render")

    def _configure_start_check_styles(self) -> None:
        style = ttk.Style(self.root)
        panel = COLORS["panel"]
        panel2 = COLORS["panel2"]
        style.configure(
            "StartCheck.TFrame",
            background=panel,
            relief="solid",
            borderwidth=2,
            bordercolor=COLORS["attention"],
        )
        style.configure(
            "StartCheckTitle.TLabel",
            background=panel,
            foreground=safe_text_color(panel, COLORS["text"]),
            font=("DejaVu Sans", 12, "bold"),
        )
        for name, color in (
            ("Ok", COLORS["success"]),
            ("Warning", COLORS["warning"]),
            ("Error", COLORS["danger"]),
            ("Idle", COLORS["disabled"]),
        ):
            style.configure(
                f"Start{name}.TFrame",
                background=panel2,
                relief="solid",
                borderwidth=2,
                bordercolor=color,
            )
            style.configure(
                f"Start{name}.TLabel",
                background=panel2,
                foreground=safe_text_color(panel2, color),
                font=("DejaVu Sans", 10, "bold"),
            )
            style.configure(
                f"Start{name}Pill.TLabel",
                background=color,
                foreground=best_text_color(color),
                padding=(8, 4),
                font=("DejaVu Sans", 10, "bold"),
            )
        action = COLORS["attention"]
        style.configure(
            "StartAction.TButton",
            background=action,
            foreground=best_text_color(action),
            padding=(14, 8),
            font=("DejaVu Sans", 11, "bold"),
            borderwidth=1,
        )

    def _build_shell_start_check(self, parent) -> None:
        self._configure_start_check_styles()
        card = ttk.Frame(parent, style="StartCheck.TFrame", padding=(10, 8))
        card.grid(row=3, column=0, sticky="ew", pady=(0, 9))
        card.columnconfigure(0, weight=1)
        self._shell_start_check = card

        header = ttk.Frame(card, style="StartCheck.TFrame")
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(0, weight=1)
        ttk.Label(
            header,
            text="STARTRoutine / START-CHECK",
            style="StartCheckTitle.TLabel",
        ).grid(row=0, column=0, sticky="w")
        self._start_summary = StringVar(value="Prüfung wird aufgebaut")
        self._start_summary_label = ttk.Label(
            header,
            textvariable=self._start_summary,
            style="StartIdlePill.TLabel",
        )
        self._start_summary_label.grid(row=0, column=1, sticky="e", padx=(8, 0))

        host = ttk.Frame(card, style="StartCheck.TFrame")
        host.grid(row=1, column=0, sticky="ew", pady=(7, 7))
        self._start_steps_host = host
        self._start_step_widgets = {}
        for index, key in enumerate(self._START_KEYS, start=1):
            frame = ttk.Frame(host, style="StartIdle.TFrame", padding=(8, 5))
            status = ttk.Label(frame, text="● PRÜFUNG", style="StartIdle.TLabel")
            status.pack(anchor="w")
            title = StringVar(value=f"{index}. Prüfung")
            ttk.Label(frame, textvariable=title, style="StartIdle.TLabel").pack(
                anchor="w", pady=(2, 0)
            )
            detail = StringVar(value="Wird geprüft")
            detail_label = ttk.Label(
                frame,
                textvariable=detail,
                style="StartIdle.TLabel",
                justify="left",
                wraplength=190,
            )
            detail_label.pack(anchor="w", fill="x", pady=(2, 0))
            self._start_step_widgets[key] = (frame, status, title, detail, detail_label)

        next_row = ttk.Frame(card, style="StartCheck.TFrame")
        next_row.grid(row=2, column=0, sticky="ew")
        next_row.columnconfigure(0, weight=1)
        self._start_next_action = StringVar(value="Nächster Schritt wird ermittelt")
        ttk.Label(next_row, text="NÄCHSTER SCHRITT", style="StartWarning.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(
            next_row,
            textvariable=self._start_next_action,
            style="StartCheckTitle.TLabel",
        ).grid(row=1, column=0, sticky="w", pady=(1, 0))
        self._start_next_button = ttk.Button(
            next_row,
            text="→ Aktion öffnen",
            style="StartAction.TButton",
            command=self._run_shell_next_action,
        )
        self._start_next_button.grid(row=0, column=1, rowspan=2, sticky="e", padx=(12, 0))

        card.bind("<Configure>", self._layout_shell_start_check, add="+")
        self._refresh_shell_start_check()
        self._start_check_poll_id = self.root.after(1000, self._poll_shell_start_check)

    def _layout_shell_start_check(self, event=None) -> None:
        width = max(1, int(getattr(event, "width", self._shell_start_check.winfo_width())))
        columns = 6 if width >= 1220 else 3 if width >= 720 else 2 if width >= 480 else 1
        for column in range(6):
            self._start_steps_host.columnconfigure(
                column, weight=1 if column < columns else 0, uniform="startcheck"
            )
        for index, key in enumerate(self._START_KEYS):
            frame = self._start_step_widgets[key][0]
            frame.grid_forget()
            frame.grid(
                row=index // columns,
                column=index % columns,
                sticky="nsew",
                padx=3,
                pady=3,
            )

    @staticmethod
    def _start_style(status: str) -> str:
        return {"ok": "Ok", "warning": "Warning", "error": "Error"}.get(status, "Idle")

    def _apply_start_step(self, index: int, step: StartupStep) -> None:
        frame, status, title, detail, detail_label = self._start_step_widgets[step.key]
        style = self._start_style(step.status)
        frame.configure(style=f"Start{style}.TFrame")
        status.configure(
            text={"ok": "● BEREIT", "warning": "● PRÜFEN", "error": "● BLOCKIERT"}[step.status],
            style=f"Start{style}.TLabel",
        )
        title.set(f"{index}. {step.title}")
        detail.set(step.detail)
        detail_label.configure(style=f"Start{style}.TLabel")

    def _refresh_shell_start_check(self) -> None:
        if not hasattr(self, "_start_step_widgets"):
            return
        project_name = self.project_name.get().strip() if hasattr(self, "project_name") else ""
        model = build_startup_readiness(
            project_name=project_name,
            checks=self._preparation_checks(),
        )
        self._shell_start_readiness = model
        for index, step in enumerate(model.steps, start=1):
            self._apply_start_step(index, step)

        overall = self._start_style(model.overall_status)
        self._start_summary.set(
            f"{model.ready_count}/{len(model.steps)} bereit · "
            f"{model.warning_count} Warnung(en) · {model.error_count} Fehler"
        )
        self._start_summary_label.configure(style=f"Start{overall}Pill.TLabel")
        next_step = next(step for step in model.steps if step.key == model.next_step_key)
        if model.ready:
            self._start_next_action.set("Alle Startprüfungen grün · Queue kann gestartet werden")
            self._start_next_button.configure(text="▶ Queue starten")
        else:
            self._start_next_action.set(f"{next_step.title}: {next_step.detail}")
            self._start_next_button.configure(text=f"→ {next_step.title} prüfen")

    def _run_shell_next_action(self) -> None:
        model = getattr(self, "_shell_start_readiness", None)
        if model is None:
            return
        if model.ready:
            self._start()
            return
        next_step = next(step for step in model.steps if step.key == model.next_step_key)
        actions = {
            "add_audio": self._add_audio,
            "add_media": self._add_media,
            "choose_output": lambda: self._choose_directory(self.output_dir),
            "repair_settings": self._repair_settings_and_retry,
            "switch_to_slideshow": self._switch_to_slideshow,
            "show_pairing": self._focus_pairing,
            "create_project_folder": self._create_project_folder,
            "focus_waveform": lambda: self.main_notebook.select(2),
        }
        callback = actions.get(next_step.action)
        if callback is not None:
            callback()
            self.root.after_idle(self._refresh_shell_start_check)
            return
        self._show_dashboard_view("assistant")
        self.root.after_idle(self._refresh_preparation_assistant)

    def _poll_shell_start_check(self) -> None:
        try:
            if not self.root.winfo_exists():
                return
            self._refresh_shell_start_check()
            self._start_check_poll_id = self.root.after(1000, self._poll_shell_start_check)
        except TclError:
            return
