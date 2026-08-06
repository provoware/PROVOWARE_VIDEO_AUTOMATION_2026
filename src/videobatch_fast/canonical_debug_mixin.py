from __future__ import annotations

from tkinter import BooleanVar, ttk

from .debug_runtime import RUNTIME


class CanonicalDebugMixin:
    """Persist and expose the human-readable debug mode inside the canonical UI."""

    def _build_variables(self) -> None:
        super()._build_variables()
        self.debug_mode = BooleanVar(value=bool(self.config.get("debug_mode", True)))
        RUNTIME.set_enabled(self.debug_mode.get())
        RUNTIME.set_context_provider(self._debug_context)

    def _build_dashboard_appearance_card(self, parent):
        card = super()._build_dashboard_appearance_card(parent)
        separator = ttk.Separator(card)
        separator.grid(row=4, column=0, sticky="ew", pady=(11, 8))
        ttk.Checkbutton(
            card,
            text="Debugmodus · ausführliche verständliche Diagnose",
            variable=self.debug_mode,
            command=self._toggle_debug_mode,
        ).grid(row=5, column=0, sticky="w")
        ttk.Label(
            card,
            text=(
                "Aktiv: Start und Fehler werden in der Konsole mit WAS, WIE, WO und LÖSUNG erklärt. "
                "Absturzberichte landen automatisch im Projektordner debugging."
            ),
            style="Hint.TLabel",
            wraplength=360,
            justify="left",
        ).grid(row=6, column=0, sticky="ew", pady=(4, 8))
        actions = ttk.Frame(card, style="ShellCard.TFrame")
        actions.grid(row=7, column=0, sticky="ew")
        actions.columnconfigure(0, weight=1)
        actions.columnconfigure(1, weight=1)
        ttk.Button(
            actions,
            text="Debugbericht jetzt erstellen",
            command=self._create_manual_debug_report,
        ).grid(row=0, column=0, sticky="ew", padx=(0, 3))
        ttk.Button(
            actions,
            text="Debugging-Ordner öffnen",
            command=self._open_debug_folder,
        ).grid(row=0, column=1, sticky="ew", padx=(3, 0))
        return card

    def _toggle_debug_mode(self) -> None:
        enabled = bool(self.debug_mode.get())
        self.config["debug_mode"] = enabled
        RUNTIME.set_enabled(enabled)
        self._save_settings()
        self.guidance_text.set(
            "Debugmodus ist aktiv. Fehler werden ausführlich erklärt und lokal protokolliert."
            if enabled
            else "Debugmodus ist ausgeschaltet. Die ausführliche Konsolenausgabe ist deaktiviert."
        )

    def _create_manual_debug_report(self) -> None:
        incident = RUNTIME.capture_message(
            what="Ein manueller Debugbericht wurde im Tool angefordert.",
            how="Der Benutzer hat die Funktion „Debugbericht jetzt erstellen“ gewählt.",
            where="Dashboard → Darstellung → Debugmodus",
            solutions=(
                "Den automatisch geöffneten Bericht prüfen.",
                "Bei einem reproduzierbaren Fehler die letzten Schritte zusammen mit diesem Bericht festhalten.",
            ),
            extra_context=self._debug_context(),
            auto_open=True,
            force=True,
            prefix="DEBUGBERICHT",
        )
        if incident is not None:
            self.guidance_text.set(f"Debugbericht gespeichert: {incident.path}")

    def _open_debug_folder(self) -> None:
        if RUNTIME.open_debug_folder():
            self.guidance_text.set("Debugging-Ordner wurde geöffnet.")
        else:
            self.guidance_text.set(
                "Debugging-Ordner konnte nicht automatisch geöffnet werden. Der Pfad steht im Konsolenprotokoll."
            )

    def _debug_context(self) -> dict[str, object]:
        context: dict[str, object] = {
            "Debugmodus": bool(getattr(self, "debug_mode", None).get())
            if hasattr(self, "debug_mode")
            else bool(self.config.get("debug_mode", True)),
            "Projekt": getattr(self, "project_name_value", ""),
            "Projektdatei": getattr(self, "project_file", ""),
            "Audio-Dateien": len(getattr(self, "audios", ())),
            "Medien-Dateien": len(getattr(self, "media", ())),
            "Queue-Aufträge": len(getattr(self, "jobs", ())),
            "Letzte Ergebnisse": len(getattr(self, "last_results", ())),
            "Safe-Mode": bool(getattr(self, "safe_mode", False)),
        }
        for label, attribute in (
            ("Theme", "theme_name"),
            ("Schriftgröße", "global_font_scale"),
            ("Ausgabeordner", "output_dir"),
            ("Auflösung", "resolution"),
            ("Codec", "codec"),
            ("Schnellmodus", "quick_mode"),
        ):
            variable = getattr(self, attribute, None)
            try:
                context[label] = variable.get() if variable is not None else ""
            except Exception:
                context[label] = "<nicht lesbar>"
        try:
            context["Fenstergeometrie"] = self.root.geometry()
            context["Aktiver Tab"] = int(self.main_notebook.index(self.main_notebook.select()))
        except Exception:
            pass
        return context

    def _close(self) -> None:
        RUNTIME.verbose(
            "VideoBatch wird regulär geschlossen.",
            "Der Benutzer oder die Anwendung hat den vorgesehenen Schließpfad ausgelöst.",
            "CanonicalDebugMixin._close",
            "Keine Reparatur nötig. Der Sitzungsabschluss wird als regulär markiert.",
        )
        RUNTIME.mark_clean_shutdown()
        super()._close()
