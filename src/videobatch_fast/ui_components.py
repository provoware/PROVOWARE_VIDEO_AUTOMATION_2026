from __future__ import annotations

from tkinter import BOTH, LEFT, RIGHT, X, Button, Canvas, Label, StringVar, TclError, Text, Toplevel, ttk
from typing import Callable

from .error_handling import ErrorDefinition
from .text_resources import text


def _bounded_solution_dialog_size(
    screen_width: int,
    screen_height: int,
    *,
    preferred_width: int = 760,
    preferred_height: int = 620,
    minimum_width: int = 620,
    minimum_height: int = 480,
    margin: int = 24,
) -> tuple[int, int]:
    """Fit the solution dialog to the visible screen without growing the reference layout."""
    safe_margin = max(8, int(margin))
    available_width = max(320, int(screen_width) - (safe_margin * 2))
    available_height = max(320, int(screen_height) - (safe_margin * 2))
    width = min(int(preferred_width), available_width)
    height = min(int(preferred_height), available_height)
    if available_width >= minimum_width:
        width = max(int(minimum_width), width)
    if available_height >= minimum_height:
        height = max(int(minimum_height), height)
    return max(320, width), max(320, height)


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
        self.window.protocol("WM_DELETE_WINDOW", self.window.destroy)

        width, height = _bounded_solution_dialog_size(
            self.window.winfo_screenwidth(),
            self.window.winfo_screenheight(),
        )
        self.window.minsize(min(620, width), min(480, height))
        self._place_centered(parent, width, height)
        content_wrap = max(320, width - 100)

        outer = ttk.Frame(self.window, padding=14)
        outer.pack(fill=BOTH, expand=True)

        header = ttk.Frame(outer, style="Card.TFrame", padding=(12, 10))
        header.pack(fill=X, pady=(0, 8))
        ttk.Label(
            header,
            text=definition.title,
            style="Section.TLabel",
            wraplength=content_wrap,
            justify="left",
        ).pack(anchor="w")
        severity_label, severity_style = self._severity_badge(definition.severity)
        ttk.Label(
            header,
            text=f"{severity_label} · Fehlercode: {definition.code}",
            style=severity_style,
        ).pack(anchor="w", pady=(3, 2))
        ttk.Label(
            header,
            text=self._header_hint(definition.severity),
            style="Hint.TLabel",
            wraplength=content_wrap,
            justify="left",
        ).pack(anchor="w")

        # Explanations can grow, but the action area below remains fixed and reachable.
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
        for index, (title, section_text) in enumerate(sections):
            box = ttk.Frame(body, style="Card.TFrame", padding=7)
            box.pack(fill=X, pady=2, padx=(0, 6))
            title_style = "SectionHeader.TLabel" if index == 3 else "Section.TLabel"
            ttk.Label(box, text=title, style=title_style).pack(anchor="w")
            ttk.Label(
                box,
                text=section_text,
                style="Hint.TLabel",
                wraplength=max(300, content_wrap - 20),
                justify="left",
            ).pack(anchor="w")
        if detail:
            details = ttk.LabelFrame(body, text=text("ui.components.technische_details"), padding=7)
            details.pack(fill=X, pady=(5, 3), padx=(0, 6))
            viewer = Text(details, height=3, wrap="word")
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
        self.primary_button = None
        if available:
            action_box = ttk.Frame(outer, style="Card.TFrame", padding=9)
            action_box.pack(fill=X, pady=(8, 4))
            action_box.columnconfigure(0, weight=1)
            action_box.columnconfigure(1, weight=1)
            ttk.Label(
                action_box,
                text="Direkte Lösungen",
                style="SectionHeader.TLabel",
            ).grid(row=0, column=0, columnspan=2, sticky="w")
            ttk.Label(
                action_box,
                text="Empfohlen: zuerst die hervorgehobene Aktion ausführen.",
                style="Hint.TLabel",
            ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(1, 4))
            for index, (action_id, callback) in enumerate(available):
                button = ttk.Button(
                    action_box,
                    text=self._label(action_id),
                    style="Accent.TButton" if index == 0 else "TButton",
                    command=lambda cb=callback: self._run(cb),
                )
                if index == 0:
                    button.grid(row=2, column=0, columnspan=2, sticky="ew", padx=4, pady=(3, 5))
                    self.primary_button = button
                else:
                    secondary = index - 1
                    button.grid(
                        row=3 + (secondary // 2),
                        column=secondary % 2,
                        sticky="ew",
                        padx=4,
                        pady=3,
                    )

        buttons = ttk.Frame(outer)
        buttons.pack(fill=X, pady=(5, 0))
        close_label = text("ui.solutions.close_without_change") if available else text("ui.components.losung_gelesen")
        close_button = ttk.Button(
            buttons,
            text=close_label,
            style="Ghost.TButton",
            command=self.window.destroy,
        )
        close_button.pack(side=RIGHT)
        self.window.bind("<Escape>", lambda _event: self.window.destroy())
        if self.primary_button is not None:
            self.primary_button.bind("<Return>", lambda _event: self.primary_button.invoke())
            self.primary_button.bind("<KP_Enter>", lambda _event: self.primary_button.invoke())
            self.window.after_idle(self.primary_button.focus_set)
        else:
            self.window.after_idle(close_button.focus_set)

    def _place_centered(self, parent, width: int, height: int) -> None:
        try:
            parent.update_idletasks()
            x = parent.winfo_rootx() + max(0, (parent.winfo_width() - width) // 2)
            y = parent.winfo_rooty() + max(0, (parent.winfo_height() - height) // 2)
        except Exception:
            x = max(0, (self.window.winfo_screenwidth() - width) // 2)
            y = max(0, (self.window.winfo_screenheight() - height) // 2)
        max_x = max(0, self.window.winfo_screenwidth() - width)
        max_y = max(0, self.window.winfo_screenheight() - height)
        self.window.geometry(f"{width}x{height}+{max(0, min(x, max_x))}+{max(0, min(y, max_y))}")

    def _run(self, callback: Callable[[], None]) -> None:
        self.window.destroy()
        callback()

    @staticmethod
    def _header_hint(severity: str) -> str:
        if severity == "blocking":
            return "Sicher gestoppt · keine unsichere Änderung wurde ausgeführt. Wähle unten den nächsten Schritt."
        if severity == "warning":
            return "Prüfung erforderlich · die Oberfläche bleibt bedienbar. Wähle unten eine passende Lösung."
        return "Hinweis · du kannst direkt eine passende Aktion auswählen oder den Dialog schließen."

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
