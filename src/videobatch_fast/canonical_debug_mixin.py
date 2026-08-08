from __future__ import annotations

from tkinter import BooleanVar, filedialog, ttk

from .debug_runtime import RUNTIME
from .permission_service import downloads_dir
from .support_bundle import (
    SupportBundleError,
    export_safe_mode_support_bundle,
    support_bundle_filename,
)


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
                "Absturzberichte landen bevorzugt automatisch im Projektordner debugging."
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
        if self.safe_mode:
            self._build_safe_mode_support_export(card)
        return card

    def _build_safe_mode_support_export(self, card) -> None:
        ttk.Separator(card).grid(row=8, column=0, sticky="ew", pady=(11, 8))
        safe = ttk.Frame(card, style="ShellCard.TFrame")
        safe.grid(row=9, column=0, sticky="ew")
        safe.columnconfigure(0, weight=1)
        ttk.Label(
            safe,
            text="Sicherer Startmodus · Supportpaket",
            style="SectionHeader.TLabel",
        ).grid(row=0, column=0, sticky="w")
        ttk.Label(
            safe,
            text=(
                "Exportiert Bootstrap-/Application-Logs, Startup-Prüfungen, Versionsdaten, "
                "aktuelle Vorbereitung und die ermittelte Safe-Mode-Ursache. "
                "Quelldateien werden nur gelesen; das ZIP wird read-only gespeichert."
            ),
            style="Hint.TLabel",
            wraplength=360,
            justify="left",
        ).grid(row=1, column=0, sticky="ew", pady=(4, 7))
        ttk.Button(
            safe,
            text="Diagnose exportieren",
            style="Accent.TButton",
            command=self._export_safe_mode_diagnostics,
        ).grid(row=2, column=0, sticky="ew")

    def _export_safe_mode_diagnostics(self) -> None:
        if not self.safe_mode:
            self.guidance_text.set("Der Safe-Mode-Diagnoseexport ist nur im sicheren Startmodus verfügbar.")
            return
        target = filedialog.asksaveasfilename(
            parent=self.root,
            title="Safe-Mode-Diagnose exportieren",
            initialdir=str(downloads_dir()),
            initialfile=support_bundle_filename(),
            defaultextension=".zip",
            filetypes=(("ZIP-Supportpaket", "*.zip"),),
        )
        if not target:
            self.guidance_text.set("Diagnoseexport abgebrochen; es wurde nichts geschrieben.")
            return
        try:
            path = export_safe_mode_support_bundle(
                target,
                checks=self._preparation_checks(),
                context=self._debug_context(),
            )
        except (OSError, ValueError, SupportBundleError) as exc:
            self.guidance_text.set(f"Diagnoseexport fehlgeschlagen: {exc}")
            self._event(
                "SAFE_MODE_SUPPORT_EXPORT_FAILED",
                "Diagnoseexport fehlgeschlagen",
                str(exc),
                level="error",
                solution="Anderen beschreibbaren Zielordner wählen und Export erneut ausführen.",
            )
            return
        self.guidance_text.set(f"Read-only Diagnosepaket gespeichert: {path}")
        self._event(
            "SAFE_MODE_SUPPORT_EXPORTED",
            "Safe-Mode-Diagnose exportiert",
            str(path),
            level="success",
            solution="ZIP bei Bedarf manuell an den Support weitergeben; es wurde nicht automatisch versendet.",
        )

    def _toggle_debug_mode(self) -> None:
        enabled = bool(self.debug_mode.get())
        self.config["debug_mode"] = enabled
        RUNTIME.set_enabled(enabled)
        self._save_settings()
        self.guidance_text.set(
            (
                "Debugmodus ist aktiv: App-Fehler werden ab sofort ausführlich erklärt. "
                "Der externe Prozesswächter ist ab dem nächsten Programmstart vollständig aktiv."
            )
            if enabled
            else (
                "Debugmodus ist ausgeschaltet. Die ausführliche Konsolenausgabe und der externe Wächter "
                "beenden sich kontrolliert; die Einstellung bleibt gespeichert."
            )
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
                "Debugging-Ordner konnte nicht automatisch geöffnet werden. Die Konsole enthält den technischen Grund."
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
            context["Aktiver Tab"] = int(
                self.main_notebook.index(self.main_notebook.select())
            )
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
