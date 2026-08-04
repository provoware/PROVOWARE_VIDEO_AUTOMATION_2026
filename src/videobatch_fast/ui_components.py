from __future__ import annotations

from tkinter import BOTH, LEFT, RIGHT, X, Button, Canvas, Label, StringVar, Text, Toplevel, ttk
from typing import Callable

from .error_handling import ErrorDefinition
from .text_resources import text


class Tooltip:
    def __init__(self, widget, message: str) -> None:
        self.widget = widget
        self.message = message
        self.window = None
        widget.bind("<Enter>", self._show, add=True)
        widget.bind("<Leave>", self._hide, add=True)
        widget.bind("<FocusIn>", self._show, add=True)
        widget.bind("<FocusOut>", self._hide, add=True)

    def _show(self, _event=None) -> None:
        if self.window or not self.message:
            return
        self.window = Toplevel(self.widget)
        self.window.wm_overrideredirect(True)
        x = self.widget.winfo_rootx() + 12
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 6
        self.window.wm_geometry(f"+{x}+{y}")
        Label(self.window, text=self.message, justify="left", background="#fff7cf", foreground="#1a1a1a", relief="solid", borderwidth=1, padx=8, pady=6, wraplength=420).pack()

    def _hide(self, _event=None) -> None:
        if self.window:
            self.window.destroy()
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
        ttk.Label(outer, text=f"Fehlercode: {definition.code}", style="Hint.TLabel").pack(anchor="w", pady=(0, 8))

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
    def _label(action_id: str) -> str:
        return {
            "retry_runtime": "Erneut prüfen",
            "open_install_help": "Installationshilfe",
            "focus_file_lists": "Dateilisten öffnen",
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
        ttk.Button(buttons, text=text("help_center.refresh"), command=self._refresh).pack(side=LEFT)
        self.copy_label = StringVar(value=text("help_center.copy_status"))
        ttk.Button(buttons, textvariable=self.copy_label, command=self._copy_status).pack(side=LEFT, padx=(6, 0))
        ttk.Button(buttons, text=text("help_center.logs"), command=on_open_logs).pack(side=LEFT, padx=(6, 0))
        ttk.Button(buttons, text=text("help_center.manual"), command=on_open_manual).pack(side=LEFT, padx=(6, 0))
        if on_run_fault_lab is not None:
            ttk.Button(buttons, text=text("help_center.fault_lab"), command=on_run_fault_lab).pack(side=LEFT, padx=(6, 0))
        ttk.Button(buttons, text=text("help_center.close"), style="Accent.TButton", command=self.window.destroy).pack(side=RIGHT)
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
