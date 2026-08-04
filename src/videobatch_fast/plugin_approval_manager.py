from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from tkinter import END, StringVar, Toplevel, messagebox, ttk
from typing import Callable, Iterable

from .plugin_approvals import build_identity, list_approvals, revoke_approval, validate_approval
from .plugin_permissions import permission_summary
from .plugins import PluginCheck, scan_plugins


@dataclass(frozen=True, slots=True)
class PluginApprovalRow:
    plugin_id: str
    status: str
    version: str
    payload_sha256: str
    capability: str
    publisher: str
    approved_at: str
    updated_at: str
    reason: str
    installed: bool

    @property
    def short_hash(self) -> str:
        return self.payload_sha256[:16] + ("…" if len(self.payload_sha256) > 16 else "")


def synchronize_plugin_approvals(path: Path | None = None, checks: Iterable[PluginCheck] | None = None) -> list[PluginApprovalRow]:
    installed_checks = list(checks) if checks is not None else scan_plugins(quarantine_invalid=False)
    installed = {item.plugin_id: item for item in installed_checks if item.plugin_id and item.plugin_id != "unknown"}
    for item in installed_checks:
        if not item.valid:
            continue
        permissions = permission_summary(item.capability, item.key_id)
        identity = build_identity(
            plugin_id=item.plugin_id,
            version=item.version,
            payload_sha256=item.payload_sha256,
            key_id=item.key_id,
            capability=item.capability,
            permissions=permissions,
        )
        validate_approval(identity, path, persist_expiry=True)

    rows: list[PluginApprovalRow] = []
    for record in list_approvals(path):
        plugin_id = str(record.get("plugin_id", ""))
        permission_data = record.get("permissions", {}) if isinstance(record.get("permissions"), dict) else {}
        rows.append(
            PluginApprovalRow(
                plugin_id=plugin_id,
                status=str(record.get("status", "expired")),
                version=str(record.get("version", "0.0.0")),
                payload_sha256=str(record.get("payload_sha256", "")),
                capability=str(record.get("capability", "")),
                publisher=str(permission_data.get("publisher", "Unbekannt")),
                approved_at=str(record.get("approved_at", "")),
                updated_at=str(record.get("updated_at", "")),
                reason=str(record.get("reason", "")),
                installed=plugin_id in installed,
            )
        )
    return sorted(rows, key=lambda row: (row.status != "active", row.plugin_id.casefold()))


def filter_approval_rows(rows: Iterable[PluginApprovalRow], search: str = "", status: str = "all") -> list[PluginApprovalRow]:
    query = str(search).strip().casefold()
    wanted = str(status).strip().casefold()
    result: list[PluginApprovalRow] = []
    for row in rows:
        if wanted not in {"", "all"} and row.status.casefold() != wanted:
            continue
        haystack = " ".join((row.plugin_id, row.version, row.payload_sha256, row.capability, row.publisher, row.reason)).casefold()
        if query and query not in haystack:
            continue
        result.append(row)
    return result


class PluginApprovalManagerDialog:
    STATUS_LABELS = {
        "all": "Alle",
        "active": "Aktiv",
        "expired": "Abgelaufen",
        "revoked": "Widerrufen",
    }

    def __init__(
        self,
        parent,
        *,
        approvals_path: Path | None = None,
        on_event: Callable[[str, str, str], None] | None = None,
    ) -> None:
        self.approvals_path = approvals_path
        self.on_event = on_event
        self.rows: list[PluginApprovalRow] = []
        self.row_map: dict[str, PluginApprovalRow] = {}
        self.search = StringVar(value="")
        self.status = StringVar(value="Alle")
        self.detail = StringVar(value="Eintrag auswählen, um Details zu sehen.")

        self.window = Toplevel(parent)
        self.window.title("Plugin-Freigabeverwaltung")
        self.window.geometry("1180x700")
        self.window.minsize(900, 560)
        self.window.transient(parent)
        outer = ttk.Frame(self.window, padding=14)
        outer.pack(fill="both", expand=True)

        ttk.Label(outer, text="Plugin-Freigabeverwaltung", style="DialogTitle.TLabel").pack(anchor="w")
        ttk.Label(
            outer,
            text="Aktive, abgelaufene und widerrufene Freigaben. Änderungen an Version, Hash, Schlüssel oder Berechtigungen lassen eine Freigabe automatisch ablaufen.",
            style="Hint.TLabel",
            wraplength=1080,
        ).pack(anchor="w", pady=(3, 10))

        controls = ttk.Frame(outer)
        controls.pack(fill="x")
        ttk.Label(controls, text="Suche").pack(side="left")
        search_entry = ttk.Entry(controls, textvariable=self.search, width=32)
        search_entry.pack(side="left", padx=(5, 12))
        search_entry.bind("<KeyRelease>", lambda _event: self._refresh_table())
        ttk.Label(controls, text="Status").pack(side="left")
        filter_box = ttk.Combobox(controls, textvariable=self.status, values=tuple(self.STATUS_LABELS.values()), state="readonly", width=14)
        filter_box.pack(side="left", padx=5)
        filter_box.bind("<<ComboboxSelected>>", lambda _event: self._refresh_table())
        ttk.Button(controls, text="Neu prüfen", command=self.reload).pack(side="right")

        columns = ("plugin", "status", "version", "hash", "capability", "publisher", "approved", "updated", "installed")
        self.tree = ttk.Treeview(outer, columns=columns, show="headings", selectmode="browse", height=15)
        specs = (
            ("plugin", "Plugin", 165),
            ("status", "Status", 90),
            ("version", "Version", 90),
            ("hash", "Inhalts-Hash", 150),
            ("capability", "Fähigkeit", 115),
            ("publisher", "Herausgeber", 150),
            ("approved", "Freigegeben", 150),
            ("updated", "Aktualisiert", 150),
            ("installed", "Installiert", 80),
        )
        for key, title, width in specs:
            self.tree.heading(key, text=title)
            self.tree.column(key, width=width, stretch=key in {"plugin", "publisher"})
        self.tree.pack(fill="both", expand=True, pady=(10, 8))
        self.tree.bind("<<TreeviewSelect>>", self._selection_changed)

        detail_frame = ttk.Frame(outer, style="Card.TFrame", padding=8)
        detail_frame.pack(fill="x")
        ttk.Label(detail_frame, text="Begründung und Bindung", style="Section.TLabel").pack(anchor="w")
        ttk.Label(detail_frame, textvariable=self.detail, style="Hint.TLabel", wraplength=1080, justify="left").pack(anchor="w", pady=(3, 0))

        actions = ttk.Frame(outer)
        actions.pack(fill="x", pady=(10, 0))
        self.revoke_button = ttk.Button(actions, text="Ausgewählte Freigabe widerrufen", style="Danger.TButton", command=self._revoke_selected, state="disabled")
        self.revoke_button.pack(side="left")
        ttk.Button(actions, text="Schließen", command=self.window.destroy).pack(side="right")
        # Untere Aktionen und Details erhalten garantiert Platz; die Tabelle nutzt nur den Rest.
        self.tree.pack_forget()
        detail_frame.pack_forget()
        actions.pack_forget()
        actions.pack(side="bottom", fill="x", pady=(10, 0))
        detail_frame.pack(side="bottom", fill="x", pady=(8, 0))
        self.tree.pack(fill="both", expand=True, pady=(10, 0))
        self.reload()

    def reload(self) -> None:
        self.rows = synchronize_plugin_approvals(self.approvals_path)
        self._refresh_table()

    def _refresh_table(self) -> None:
        reverse = {label: key for key, label in self.STATUS_LABELS.items()}
        filtered = filter_approval_rows(self.rows, self.search.get(), reverse.get(self.status.get(), "all"))
        self.tree.delete(*self.tree.get_children())
        self.row_map.clear()
        for index, row in enumerate(filtered):
            iid = f"approval:{index}"
            self.row_map[iid] = row
            self.tree.insert(
                "",
                END,
                iid=iid,
                values=(
                    row.plugin_id,
                    row.status,
                    row.version,
                    row.short_hash,
                    row.capability,
                    row.publisher,
                    row.approved_at or "–",
                    row.updated_at or "–",
                    "ja" if row.installed else "nein",
                ),
            )
        self.detail.set(f"{len(filtered)} von {len(self.rows)} Freigaben sichtbar.")
        self.revoke_button.configure(state="disabled")

    def _selection_changed(self, _event=None) -> None:
        selected = self.tree.selection()
        row = self.row_map.get(selected[0]) if selected else None
        if not row:
            self.revoke_button.configure(state="disabled")
            return
        self.detail.set(
            f"{row.plugin_id} · Status {row.status} · Vollständiger Hash {row.payload_sha256 or 'nicht vorhanden'}\n"
            f"Grund: {row.reason or 'Keine zusätzliche Begründung gespeichert.'}"
        )
        self.revoke_button.configure(state="normal" if row.status == "active" else "disabled")

    def _revoke_selected(self) -> None:
        selected = self.tree.selection()
        row = self.row_map.get(selected[0]) if selected else None
        if not row or row.status != "active":
            return
        if not messagebox.askyesno(
            "Plugin-Freigabe widerrufen",
            f"Freigabe für „{row.plugin_id}“ widerrufen?\n\nDas Plugin bleibt danach inaktiv, bis es erneut vollständig geprüft und freigegeben wird.",
            parent=self.window,
        ):
            return
        result = revoke_approval(row.plugin_id, path=self.approvals_path)
        if self.on_event:
            self.on_event("PLUGIN_APPROVAL_REVOKED", row.plugin_id, result.message)
        self.reload()
