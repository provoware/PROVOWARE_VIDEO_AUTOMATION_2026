from __future__ import annotations

from dataclasses import dataclass
from tkinter import BOTH, LEFT, RIGHT, X, BooleanVar, Text, Toplevel, messagebox, ttk
from typing import Iterable


@dataclass(frozen=True, slots=True)
class DialogSection:
    title: str
    body: str


class GuidedDecisionDialog:
    """Reusable modal dialog for security-sensitive, user-guided decisions."""

    def __init__(
        self,
        parent,
        *,
        title: str,
        heading: str,
        intro: str,
        sections: Iterable[DialogSection],
        primary_label: str,
        secondary_label: str = "Abbrechen",
        warning: str = "",
        remember_label: str = "",
        width: int = 760,
        height: int = 640,
        modal: bool = True,
    ) -> None:
        self.result = False
        self.remember = BooleanVar(value=False)
        self.window = Toplevel(parent)
        self.window.title(title)
        self.window.geometry(f"{width}x{height}")
        self.window.minsize(min(620, width), min(480, height))
        self.window.transient(parent)
        if modal:
            self.window.grab_set()
        outer = ttk.Frame(self.window, padding=18)
        outer.pack(fill=BOTH, expand=True)
        ttk.Label(outer, text=heading, style="DialogTitle.TLabel", wraplength=width - 60).pack(anchor="w")
        ttk.Label(outer, text=intro, style="Hint.TLabel", wraplength=width - 60, justify="left").pack(anchor="w", pady=(4, 12))
        if warning:
            warning_box = ttk.Frame(outer, style="Card.TFrame", padding=10)
            warning_box.pack(fill=X, pady=(0, 8))
            ttk.Label(warning_box, text=text('ui.workflow_dialogs.wichtiger_hinweis'), style="Warning.TLabel").pack(anchor="w")
            ttk.Label(warning_box, text=warning, style="Hint.TLabel", wraplength=width - 90, justify="left").pack(anchor="w", pady=(3, 0))
        content = ttk.Frame(outer)
        content.pack(fill=BOTH, expand=True)
        for section in sections:
            box = ttk.Frame(content, style="Card.TFrame", padding=10)
            box.pack(fill=X, pady=4)
            ttk.Label(box, text=section.title, style="Section.TLabel").pack(anchor="w")
            ttk.Label(box, text=section.body, style="Hint.TLabel", wraplength=width - 90, justify="left").pack(anchor="w", pady=(2, 0))
        if remember_label:
            ttk.Checkbutton(outer, text=remember_label, variable=self.remember).pack(anchor="w", pady=(8, 0))
        buttons = ttk.Frame(outer)
        buttons.pack(fill=X, pady=(12, 0))
        ttk.Button(buttons, text=secondary_label, command=self._cancel).pack(side=RIGHT)
        ttk.Button(buttons, text=primary_label, style="Accent.TButton", command=self._approve).pack(side=RIGHT, padx=(0, 8))
        self.window.protocol("WM_DELETE_WINDOW", self._cancel)

    def _approve(self) -> None:
        self.result = True
        self.window.destroy()

    def _cancel(self) -> None:
        self.result = False
        self.window.destroy()

    def wait(self) -> bool:
        self.window.wait_window()
        return self.result


def plugin_permission_dialog(parent, summary_text: str, approval_status: str, *, modal: bool = True) -> GuidedDecisionDialog:
    status_text = {
        "active": "Eine unveränderte, gültige Freigabe ist gespeichert.",
        "expired": "Die bisherige Freigabe ist wegen einer Plugin- oder Berechtigungsänderung abgelaufen.",
        "revoked": "Die frühere Freigabe wurde widerrufen.",
        "missing": "Für dieses Plugin wurde noch keine Freigabe gespeichert.",
    }.get(approval_status, "Freigabestatus ist unbekannt.")
    return GuidedDecisionDialog(
        parent,
        title=text('ui.workflow_dialogs.plugin_berechtigungen_und_freigabe'),
        heading="Plugin sicher prüfen und freigeben",
        intro=status_text,
        sections=(
            DialogSection("Berechtigungsübersicht", summary_text),
            DialogSection("Freigabebindung", "Die Freigabe wird an Version, signierten Inhalts-Hash, Signaturschlüssel und Berechtigungsprofil gebunden."),
            DialogSection("Automatischer Widerruf", "Sobald sich Plugin-Dateien, Version, Schlüssel, Capability oder Berechtigungen ändern, verfällt die Freigabe automatisch."),
        ),
        warning="Nur freigeben, wenn Herausgeber, Zweck, Datenzugriff und Aktionen vollständig verständlich sind.",
        primary_label="Sandbox-Test erlauben und freigeben",
        secondary_label="Plugin inaktiv lassen",
        width=840,
        height=720,
        modal=modal,
    )


def update_assistant_dialog(parent, version: str, file_count: int, *, modal: bool = True) -> GuidedDecisionDialog:
    return GuidedDecisionDialog(
        parent,
        title=text('ui.workflow_dialogs.gefuhrtes_update'),
        heading=f"Update {version} sicher vorbereiten",
        intro="VideoBatch aktiviert das Update erst, wenn Paket, Kandidat und vollständiger Selbsttest erfolgreich sind.",
        sections=(
            DialogSection("Paketprüfung", f"{file_count} deklarierte Datei(en) werden auf sichere Pfade, Hashwerte und Kompatibilität geprüft."),
            DialogSection("Kandidatenprüfung", "Eine vollständige Kandidatenkopie wird erzeugt. Die laufende Installation bleibt unverändert aktiv."),
            DialogSection("Rückrollschutz", "Vor der Aktivierung bleibt eine Sicherung der aktuellen Installation erhalten."),
        ),
        warning="Die Anwendung muss nach erfolgreicher Installation neu gestartet werden.",
        primary_label="Update-Kandidat erstellen und testen",
        secondary_label="Später aktualisieren",
        width=780,
        height=620,
        modal=modal,
    )


def archive_preview_dialog(parent, file_count: int, project_dir: str, suffix: str, *, modal: bool = True) -> GuidedDecisionDialog:
    return GuidedDecisionDialog(
        parent,
        title=text('ui.workflow_dialogs.verwendete_dateien_sicher_ablegen'),
        heading="Dateiablage vor dem Verschieben prüfen",
        intro=f"{file_count} erfolgreich verwendete Quelldatei(en) sind für die sichere Ablage vorgesehen.",
        sections=(
            DialogSection("Ziel", project_dir or "Kein Projektordner ausgewählt"),
            DialogSection("Namenszusatz", suffix),
            DialogSection("Sicherheitsablauf", "Kopieren oder atomisch verschieben → Größe und SHA-256 prüfen → Original erst danach entfernen → Manifest aktualisieren."),
        ),
        warning="Ein Ablagefehler verändert nicht den Erfolg der bereits erstellten Videos. Originale bleiben bei jeder ungeklärten Abweichung erhalten.",
        primary_label="Dateien geprüft ablegen",
        secondary_label="Später aufräumen",
        width=760,
        height=600,
        modal=modal,
    )


def recovery_dialog(parent, error_code: str, *, modal: bool = True) -> GuidedDecisionDialog:
    return GuidedDecisionDialog(
        parent,
        title=text('ui.workflow_dialogs.recovery_und_sichere_wiederaufnahme'),
        heading="VideoBatch hat einen wiederherstellbaren Zustand erkannt",
        intro=f"Fehlercode: {error_code}",
        sections=(
            DialogSection("Was bleibt geschützt?", "Originaldateien und bereits bestätigte Ausgaben werden nicht überschrieben."),
            DialogSection("Sichere Recovery", "Letzten geprüften Zustand laden, temporäre Reste isolieren und nur den unvollständigen Schritt wiederholen."),
            DialogSection("Nachprüfung", "Die wiederaufgenommene Ausgabe wird erneut technisch validiert, bevor sie als erfolgreich gilt."),
        ),
        warning="Recovery wird höchstens einmal automatisch versucht. Danach ist eine bewusste Entscheidung erforderlich.",
        primary_label="Sichere Wiederaufnahme starten",
        secondary_label="Vorgang beendet lassen",
        width=780,
        height=610,
        modal=modal,
    )

class PluginPermissionDecisionDialog:
    def __init__(self, parent, summary_text: str, approval_status: str, *, modal: bool = True) -> None:
        self.decision = "cancel"
        status_text = {
            "active": "Eine unveränderte, gültige Freigabe ist gespeichert.",
            "expired": "Die bisherige Freigabe ist nach einer Änderung automatisch abgelaufen.",
            "revoked": "Die frühere Freigabe wurde widerrufen.",
            "missing": "Für dieses Plugin wurde noch keine Freigabe gespeichert.",
        }.get(approval_status, "Freigabestatus ist unbekannt.")
        self.window = Toplevel(parent)
        self.window.title(text('ui.workflow_dialogs.plugin_berechtigungen_und_freigabe'))
        self.window.geometry("860x740")
        self.window.minsize(700, 580)
        self.window.transient(parent)
        if modal:
            self.window.grab_set()
        outer = ttk.Frame(self.window, padding=18)
        outer.pack(fill=BOTH, expand=True)

        buttons = ttk.Frame(outer)
        buttons.pack(side="bottom", fill=X, pady=(12, 0))
        ttk.Button(buttons, text=text('ui.workflow_dialogs.schlieen'), command=lambda: self._finish("cancel")).pack(side=RIGHT)
        if approval_status == "active":
            ttk.Button(buttons, text=text('ui.workflow_dialogs.freigabe_widerrufen'), style="Danger.TButton", command=lambda: self._finish("revoke")).pack(side=LEFT)
        ttk.Button(buttons, text=text('ui.workflow_dialogs.sandbox_test_erlauben_und_freigeben'), style="Accent.TButton", command=lambda: self._finish("approve")).pack(side=RIGHT, padx=(0, 8))

        ttk.Label(outer, text=text('ui.workflow_dialogs.plugin_sicher_prufen_und_freigeben'), style="DialogTitle.TLabel").pack(anchor="w")
        ttk.Label(outer, text=status_text, style="Status.TLabel", wraplength=800).pack(anchor="w", pady=(4, 8))

        permission_box = ttk.Frame(outer, style="Card.TFrame", padding=10)
        permission_box.pack(fill=BOTH, expand=True, pady=4)
        ttk.Label(permission_box, text=text('ui.workflow_dialogs.berechtigungsubersicht'), style="Section.TLabel").pack(anchor="w")
        viewer = Text(permission_box, height=13, wrap="word", relief="flat", padx=6, pady=6)
        viewer.insert("1.0", summary_text)
        viewer.configure(state="disabled")
        viewer.pack(fill=BOTH, expand=True, pady=(4, 0))

        for title, body in (
            ("Freigabebindung", "Version, signierter Inhalts-Hash, Signaturschlüssel, Capability und Berechtigungsprofil werden gemeinsam registriert."),
            ("Automatischer Ablauf", "Ändert sich nur einer dieser Werte, verfällt die Freigabe automatisch und das Plugin bleibt bis zur erneuten Prüfung inaktiv."),
        ):
            box = ttk.Frame(outer, style="Card.TFrame", padding=8)
            box.pack(fill=X, pady=3)
            ttk.Label(box, text=title, style="Section.TLabel").pack(anchor="w")
            ttk.Label(box, text=body, style="Hint.TLabel", wraplength=790, justify="left").pack(anchor="w", pady=(2, 0))
        warning = ttk.Frame(outer, style="Card.TFrame", padding=8)
        warning.pack(fill=X, pady=(5, 0))
        ttk.Label(warning, text=text('ui.workflow_dialogs.nur_freigeben_wenn_alle_zugriffe_und_aktionen_verstandlich'), style="Warning.TLabel", wraplength=790).pack(anchor="w")
        self.window.protocol("WM_DELETE_WINDOW", lambda: self._finish("cancel"))

    def _finish(self, decision: str) -> None:
        self.decision = decision
        self.window.destroy()

    def wait(self) -> str:
        self.window.wait_window()
        return self.decision


class VisualApprovalSignDialog:
    def __init__(self, parent, build_id: str, *, default_reviewer: str = "", modal: bool = True) -> None:
        from tkinter import StringVar

        self.reviewer = ""
        self.window = Toplevel(parent)
        self.window.title(text('ui.workflow_dialogs.manuelle_visuelle_desktop_freigabe'))
        self.window.geometry("760x540")
        self.window.minsize(660, 480)
        self.window.transient(parent)
        if modal:
            self.window.grab_set()
        outer = ttk.Frame(self.window, padding=16)
        outer.pack(fill=BOTH, expand=True)

        actions = ttk.Frame(outer)
        actions.pack(side="bottom", fill=X, pady=(12, 0))
        ttk.Button(actions, text=text('ui.workflow_dialogs.abbrechen'), command=self.window.destroy).pack(side=RIGHT)

        ttk.Label(outer, text=text('ui.workflow_dialogs.visuelle_desktopprufung_signieren'), style="DialogTitle.TLabel").pack(anchor="w")
        ttk.Label(
            outer,
            text=text('ui.workflow_dialogs.die_abnahme_wird_kryptografisch_an_build_prufmanifest_referenzbilder'),
            style="Hint.TLabel",
            wraplength=700,
            justify="left",
        ).pack(anchor="w", pady=(4, 10))

        summary = ttk.Frame(outer, style="Card.TFrame", padding=10)
        summary.pack(fill=X)
        ttk.Label(summary, text=f"Build-ID: {build_id}", style="Section.TLabel").pack(anchor="w")
        ttk.Label(summary, text=text('ui.workflow_dialogs.voraussetzung_alle_visuellen_szenarien_bestanden_keine_vertragsfehler'), style="Hint.TLabel", wraplength=680).pack(anchor="w", pady=(4, 0))
        ttk.Label(summary, text=text('ui.workflow_dialogs.manipulationsschutz_anderungen_an_manifest_referenzbildern_oder_prufberi'), style="Hint.TLabel", wraplength=680).pack(anchor="w", pady=(4, 0))
        ttk.Label(summary, text=text('ui.workflow_dialogs.schlusselschutz_der_private_ed25519_schlussel_bleibt_im_privaten'), style="Hint.TLabel", wraplength=680).pack(anchor="w", pady=(4, 0))

        reviewer_var = StringVar(value=default_reviewer)
        ttk.Label(outer, text=text('ui.workflow_dialogs.prufername_oder_kurzel'), style="Section.TLabel").pack(anchor="w", pady=(12, 3))
        reviewer_entry = ttk.Entry(outer, textvariable=reviewer_var)
        reviewer_entry.pack(fill=X)
        reviewer_entry.focus_set()
        ttk.Label(outer, text=text('ui.workflow_dialogs.mit_der_signatur_bestatigst_du_die_reale_desktop'), style="Warning.TLabel", wraplength=700).pack(anchor="w", pady=(10, 0))

        def approve() -> None:
            value = reviewer_var.get().strip()
            if not value:
                messagebox.showwarning(text('ui.workflow_dialogs.prufername_fehlt'), text('ui.workflow_dialogs.trage_einen_namen_oder_ein_eindeutiges_kurzel_ein'), parent=self.window)
                return
            self.reviewer = value
            self.window.destroy()

        ttk.Button(actions, text=text('ui.workflow_dialogs.prufung_signieren'), style="Accent.TButton", command=approve).pack(side=RIGHT, padx=(0, 8))
        self.window.protocol("WM_DELETE_WINDOW", self.window.destroy)
        self.window.bind("<Return>", lambda _event: approve())
        self.window.bind("<Escape>", lambda _event: self.window.destroy())

    def wait(self) -> str:
        self.window.wait_window()
        return self.reviewer

from .text_resources import text
