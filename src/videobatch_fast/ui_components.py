from __future__ import annotations

from tkinter import BOTH, LEFT, RIGHT, X, Button, Canvas, Label, StringVar, TclError, Text, Toplevel, ttk
from typing import Callable

from .error_handling import ErrorDefinition
from .text_resources import text


class Tooltip:
    """Accessible delayed tooltip that never blocks or escapes the visible screen."""

    def __init__(
        self,
        widget,
        message: str,
        *,
        delay_ms: int = 350,
        wraplength: int = 420,
    ) -> None:
        self.widget = widget
        self.message = message.strip()
        self.delay_ms = max(0, int(delay_ms))
        self.wraplength = max(180, int(wraplength))
        self.window = None
        self._after_id = None
        widget.bind("<Enter>", self._schedule, add=True)
        widget.bind("<Leave>", self._hide, add=True)
        widget.bind("<FocusIn>", self._schedule, add=True)
        widget.bind("<FocusOut>", self._hide, add=True)
        widget.bind("<Destroy>", self._hide, add=True)

    def _schedule(self, _event=None) -> None:
        if self.window or self._after_id is not None or not self.message:
            return
        try:
            self._after_id = self.widget.after(self.delay_ms, self._show)
        except TclError:
            self._after_id = None

    def _show(self) -> None:
        self._after_id = None
        if self.window or not self.message:
            return
        try:
            if not self.widget.winfo_exists():
                return
            window = Toplevel(self.widget)
            window.wm_overrideredirect(True)
            label = Label(
                window,
                text=self.message,
                justify="left",
                background="#fff7cf",
                foreground="#1a1a1a",
                relief="solid",
                borderwidth=1,
                padx=8,
                pady=6,
                wraplength=self.wraplength,
            )
            label.pack()
            window.update_idletasks()
            screen_width = max(1, self.widget.winfo_screenwidth())
            screen_height = max(1, self.widget.winfo_screenheight())
            width = window.winfo_reqwidth()
            height = window.winfo_reqheight()
            x = self.widget.winfo_rootx() + 12
            y = self.widget.winfo_rooty() + self.widget.winfo_height() + 6
            if x + width > screen_width - 8:
                x = max(8, screen_width - width - 8)
            if y + height > screen_height - 8:
                y = max(8, self.widget.winfo_rooty() - height - 6)
            window.wm_geometry(f"+{x}+{y}")
            self.window = window
        except TclError:
            self.window = None

    def _hide(self, _event=None) -> None:
        if self._after_id is not None:
            try:
                self.widget.after_cancel(self._after_id)
            except TclError:
                pass
            self._after_id = None
        if self.window is not None:
            try:
                self.window.destroy()
            except TclError:
                pass
            self.window = None


class SolutionDialog:
    def __init__(self, parent, definition: ErrorDefinition, detail: str = "", actions: dict[str, Callable[[], None]] | None = None) -> None:
        self.window = Toplevel(parent)
        self.window.title(f"{definition.code} · {definition.title}")
        self.window.transient(parent)
        self.window.grab_set()
        self.window.geometry("760x620")
        self.window.minsize(620, 480)

        outer = ttk.Frame(self.window, padding=18)
        outer.pack(fill=BOTH, expand=True)
        ttk.Label(outer, text=definition.title, style="DialogTitle.TLabel", wraplength=700).pack(anchor="w")
        severity_label, severity_style = self._severity_badge(definition.severity)
        ttk.Label(outer, text=f"{severity_label} · Fehlercode: {definition.code}", style=severity_style).pack(anchor="w", pady=(2, 8))

        # Explanations can grow, but solution actions must remain reachable at all times.
        body_host = ttk.Frame(outer)
        body_host.pack(fill=BOTH, expand=True)
        body_host.rowconfigure(0, weight=1)
        body_host.columnconfigure(0, weight=1)
        canvas = Canvas(body_host, highlightthickness=0, borderwidth=0)
        scrollbar = ttk.Scrollbar(body_host, orient="vertical", command=canvas.yview)
        body = ttk.Frame(canvas)
        body_window = canvas.create_window((0, 0), window=body, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        body.bind("<Configure>", lambda _event: canvas.configure(scrollregion=canvas.bbox("all")), add=True)
        canvas.bind("<Configure>", lambda event: canvas.itemconfigure(body_window, width=event.width), add=True)

        sections = (
            (text("dialog.error.what", "Was ist passiert?"), definition.cause),
            (text("dialog.error.effect", "Was bedeutet das?"), definition.effect),
            (text("dialog.error.action", "Was hat VideoBatch getan?"), definition.automatic_action),
            (text("dialog.error.solution", "Empfohlene Lösung"), definition.solution),
            (text("dialog.error.alternative", "Sichere Alternative"), definition.alternative),
        )
        for title, section_text in sections:
            box = ttk.Frame(body, style="Card.TFrame", padding=8)
            box.pack(fill=X, pady=3, padx=(0, 6))
            ttk.Label(box, text=title, style="Section.TLabel").pack(anchor="w")
            ttk.Label(box, text=section_text, style="Hint.TLabel", wraplength=660, justify="left").pack(anchor="w")
        if detail:
            details = ttk.LabelFrame(body, text=text("ui.components.technische_details"), padding=8)
            details.pack(fill=X, pady=(6, 4), padx=(0, 6))
            viewer = Text(details, height=4, wrap="word")
            viewer.insert("1.0", detail)
            viewer.configure(state="disabled")
            viewer.pack(fill=X, expand=False)

        def scroll_body(event) -> str:
            delta = int(getattr(event, "delta", 0))
            if delta:
                canvas.yview_scroll(-1 if delta > 0 else 1, "units")
            elif getattr(event, "num", None) in {4, 5}:
                canvas.yview_scroll(-1 if event.num == 4 else 1, "units")
            return "break"

        canvas.bind("<MouseWheel>", scroll_body, add=True)
        canvas.bind("<Button-4>", scroll_body, add=True)
        canvas.bind("<Button-5>", scroll_body, add=True)

        actions = actions or {}
        available = [(action_id, actions.get(action_id)) for action_id in definition.actions]
        available = [(action_id, callback) for action_id, callback in available if callback]
        if available:
            action_box = ttk.LabelFrame(outer, text=text("ui.solutions.actions_heading"), padding=8)
            action_box.pack(fill=X, pady=(8, 4))
            action_box.columnconfigure(0, weight=1)
            action_box.columnconfigure(1, weight=1)
            for index, (action_id, callback) in enumerate(available):
                style = "Accent.TButton" if index == 0 else "TButton"
                ttk.Button(
                    action_box,
                    text=self._label(action_id),
                    style=style,
                    command=lambda cb=callback: self._run(cb),
                ).grid(row=index // 2, column=index % 2, sticky="ew", padx=4, pady=4)

        buttons = ttk.Frame(outer)
        buttons.pack(fill=X, pady=(6, 0))
        close_label = text("ui.solutions.close_without_change") if available else text("ui.components.losung_gelesen")
        ttk.Button(buttons, text=close_label, command=self.window.destroy).pack(side=RIGHT)

    def _run(self, callback: Callable[[], None]) -> None:
        self.window.destroy()
        callback()

    @staticmethod
    def _severity_badge(severity: str) -> tuple[str, str]:
        return {
            "information": ("Hinweis", "Status.TLabel"),
            "warning": ("Warnung", "Warning.TLabel"),
            "blocking": ("Vorgang gestoppt", "Error.TLabel"),
        }.get(severity, ("Vorgang gestoppt", "Error.TLabel"))

    @staticmethod
    def _label(action_id: str) -> str:
        return {
            "retry_runtime": "Erneut prüfen",
            "open_install_help": "Installationshilfe",
            "focus_file_lists": "Dateilisten öffnen",
            "focus_missing_audio": "Fehlende Zuordnung anzeigen",
            "show_pairing": "Zuordnung anzeigen",
            "reselect_file": "Datei erneut auswählen",
            "remove_missing": "Fehlenden Eintrag entfernen",
            "choose_output": "Anderen Ausgabeordner wählen",
            "retry_validation": "Erneut prüfen",
            "probe_selected": "Datei technisch prüfen",
            "open_external": "Extern öffnen",
            "retry_archive": "Ablage erneut versuchen",
            "open_archive_report": "Aufräumbericht öffnen",
            "open_plugin_report": "Plugin-Bericht öffnen",
            "disable_plugin": "Plugin deaktiviert lassen",
            "choose_update": "Anderes Update wählen",
            "open_update_report": "Update-Bericht öffnen",
            "open_logs": "Protokolle öffnen",
            "use_safe_output": "Sicheren Ausgabeordner verwenden",
            "create_output_folder": "Neuen Ausgabeordner erstellen",
            "add_audio": "Audiodateien ergänzen",
            "add_media": "Bilder oder Videos ergänzen",
            "switch_to_slideshow": "Diashowmodus automatisch aktivieren",
            "repair_settings": "Empfohlene Einstellungen reparieren",
            "create_project_folder": "Projektordner automatisch erstellen",
            "choose_project_folder": "Projektordner selbst auswählen",
            "disable_archive": "Dateiablage für diesen Lauf deaktivieren",
        }.get(action_id, action_id.replace("_", " ").title())


class HelpCenterDialog:
    def __init__(
        self,
        parent,
        *,
        system_status: str,
        on_refresh: Callable[[], str],
        on_open_logs: Callable[[], None],
        on_open_manual: Callable[[], None],
        on_run_fault_lab: Callable[[], None] | None = None,
    ) -> None:
        self.on_refresh = on_refresh
        self.window = Toplevel(parent)
        self.window.title(text("help_center.title"))
        self.window.transient(parent)
        self.window.geometry("860x680")
        self.window.minsize(680, 520)
        outer = ttk.Frame(self.window, padding=16)
        outer.pack(fill=BOTH, expand=True)
        ttk.Label(outer, text=text("help_center.heading"), style="DialogTitle.TLabel").pack(anchor="w")
        ttk.Label(
            outer,
            text=text("help_center.intro"),
            style="Hint.TLabel",
            wraplength=800,
            justify="left",
        ).pack(anchor="w", pady=(3, 10))

        notebook = ttk.Notebook(outer)
        notebook.pack(fill=BOTH, expand=True)
        notebook.add(self._text_tab(notebook, text("help_center.quick_title"), text("help_center.quick_body")), text=text("help_center.quick_tab"))
        notebook.add(self._text_tab(notebook, text("help_center.status_title"), text("help_center.status_body")), text=text("help_center.status_tab"))
        notebook.add(self._text_tab(notebook, text("help_center.solve_title"), text("help_center.solve_body")), text=text("help_center.solve_tab"))
        notebook.add(self._text_tab(notebook, text("help_center.errors_title"), text("help_center.errors_body")), text=text("help_center.errors_tab"))

        status_box = ttk.LabelFrame(outer, text=text("help_center.system_title"), padding=8)
        status_box.pack(fill=X, pady=(10, 0))
        self.status_value = StringVar(value=system_status)
        ttk.Label(status_box, textvariable=self.status_value, style="Status.TLabel", wraplength=790, justify="left").pack(anchor="w")

        buttons = ttk.Frame(outer)
        buttons.pack(fill=X, pady=(10, 0))
        refresh_button = ttk.Button(buttons, text=text("help_center.refresh"), command=self._refresh)
        refresh_button.pack(side=LEFT)
        Tooltip(refresh_button, text("help_center.tooltip.refresh"))
        self.copy_label = StringVar(value=text("help_center.copy_status"))
        copy_button = ttk.Button(buttons, textvariable=self.copy_label, command=self._copy_status)
        copy_button.pack(side=LEFT, padx=(6, 0))
        Tooltip(copy_button, text("help_center.tooltip.copy"))
        logs_button = ttk.Button(buttons, text=text("help_center.logs"), command=on_open_logs)
        logs_button.pack(side=LEFT, padx=(6, 0))
        Tooltip(logs_button, text("help_center.tooltip.logs"))
        manual_button = ttk.Button(buttons, text=text("help_center.manual"), command=on_open_manual)
        manual_button.pack(side=LEFT, padx=(6, 0))
        Tooltip(manual_button, text("help_center.tooltip.manual"))
        if on_run_fault_lab is not None:
            fault_button = ttk.Button(buttons, text=text("help_center.fault_lab"), command=on_run_fault_lab)
            fault_button.pack(side=LEFT, padx=(6, 0))
            Tooltip(fault_button, text("help_center.tooltip.fault_lab"))
        close_button = ttk.Button(buttons, text=text("help_center.close"), style="Accent.TButton", command=self.window.destroy)
        close_button.pack(side=RIGHT)
        Tooltip(close_button, text("help_center.tooltip.close"))
        self.window.bind("<Escape>", lambda _event: self.window.destroy())

    @staticmethod
    def _text_tab(parent, heading: str, body: str):
        frame = ttk.Frame(parent, padding=12)
        ttk.Label(frame, text=heading, style="SectionHeader.TLabel").pack(anchor="w")
        ttk.Label(frame, text=body, style="Hint.TLabel", wraplength=760, justify="left").pack(anchor="w", pady=(6, 0))
        return frame

    def _refresh(self) -> None:
        self.status_value.set(self.on_refresh())
        self.copy_label.set(text("help_center.copy_status"))

    def _copy_status(self) -> None:
        self.window.clipboard_clear()
        self.window.clipboard_append(self.status_value.get())
        self.copy_label.set(text("help_center.status_copied"))
