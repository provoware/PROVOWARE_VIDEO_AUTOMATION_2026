from __future__ import annotations

import json
from pathlib import Path
from tkinter import END, StringVar, Text, messagebox, ttk

from .text_resources import text
from .theme import COLORS
from .versioning import build_label


class UiDebugFooterMixin:
    def _build_debug_footer(self, parent):
        footer = ttk.Frame(parent, style="Card.TFrame", padding=8)
        header = ttk.Frame(footer, style="Card.TFrame")
        header.pack(fill="x")
        ttk.Label(header, text=text('ui.debug_footer.profi_debugging_und_profilogging'), style="Section.TLabel").pack(side="left")
        self.debug_summary = StringVar(value=f"Build {build_label()} · Sitzung {self.logger.session_id} · bereit")
        ttk.Label(header, textvariable=self.debug_summary, style="Hint.TLabel").pack(side="left", padx=(10, 0))
        ttk.Button(header, text=text('ui.debug_footer.logordner_offnen'), command=self._open_logs).pack(side="right")
        ttk.Button(header, text=text('ui.debug_footer.diagnosebericht'), command=self._create_diagnostic_report).pack(side="right", padx=(0, 5))

        notebook = ttk.Notebook(footer)
        self.debug_notebook = notebook
        self.monitor_notebook = notebook
        notebook.pack(fill="both", expand=True, pady=(6, 0))

        human = ttk.Frame(notebook, style="Card.TFrame", padding=6)
        self.event_tree = ttk.Treeview(human, columns=("time", "status", "event", "solution"), show="headings", height=5)
        for key, label, width in (("time", "Zeit", 85), ("status", "Status", 90), ("event", "Ereignis in einfacher Sprache", 360), ("solution", "Lösung / nächster Schritt", 560)):
            self.event_tree.heading(key, text=label)
            self.event_tree.column(key, width=width, stretch=key in {"event", "solution"})
        self.event_tree.pack(fill="both", expand=True)

        machine = ttk.Frame(notebook, style="Card.TFrame", padding=6)
        ttk.Label(machine, text=text('ui.debug_footer.maschinensprache_jsonl'), style="Section.TLabel").pack(anchor="w", pady=(0, 3))
        self.machine_log_text = Text(machine, wrap="none", height=5, bg=COLORS["preview"], fg=COLORS["text"], insertbackground=COLORS["text"], relief="flat", padx=8, pady=8)
        self.machine_log_text.pack(fill="both", expand=True)
        self.machine_log_text.configure(state="disabled")

        technical = ttk.Frame(notebook, style="Card.TFrame", padding=6)
        self.log_text = Text(technical, wrap="word", height=5, bg=COLORS["panel"], fg=COLORS["text"], insertbackground=COLORS["text"], relief="flat", padx=8, pady=8)
        self.log_text.pack(fill="both", expand=True)
        self.log_text.configure(state="disabled")

        diagnosis = ttk.Frame(notebook, style="Card.TFrame", padding=8)
        self.debug_detail = StringVar(
            value=(
                f"Tool: provoware - videoautomation - 2026\n"
                f"Build: {build_label()}\n"
                f"Sitzung: {self.logger.session_id}\n"
                f"Menschenprotokoll: {self.logger.human_path}\n"
                f"Maschinenprotokoll: {self.logger.jsonl_path}"
            )
        )
        ttk.Label(diagnosis, textvariable=self.debug_detail, style="Hint.TLabel", justify="left", wraplength=1050).pack(anchor="w")
        self.last_machine_event = StringVar(value=text('ui.debug_footer.noch_kein_ereignis_aufgezeichnet'))
        ttk.Label(diagnosis, text=text('ui.debug_footer.letztes_strukturiertes_ereignis'), style="Section.TLabel").pack(anchor="w", pady=(8, 2))
        ttk.Label(diagnosis, textvariable=self.last_machine_event, style="Hint.TLabel", justify="left", wraplength=1050).pack(anchor="w")
        health = getattr(self, "transaction_health", None)
        if health is None:
            recovery_value = "Recovery-Status: nicht verfügbar"
        elif health.healthy:
            recovery_value = f"Recovery-Status: OK · Quarantäne {health.quarantined_count} · keine offenen Inkonsistenzen"
        else:
            recovery_value = f"Recovery-Status: EINGESCHRÄNKT · Quarantäne {health.quarantined_count} · " + "; ".join(health.issues)
        recovery_report = getattr(self, "recovery_report", None)
        if recovery_report is not None:
            recovery_value += f" · Health {recovery_report.health_score}/100 · Policy {recovery_report.decision.action}"
        self.transaction_recovery_status = StringVar(value=recovery_value)
        ttk.Label(diagnosis, text=text("ui.debug_footer.transaction_recovery_status"), style="Section.TLabel").pack(anchor="w", pady=(8, 2))
        ttk.Label(diagnosis, textvariable=self.transaction_recovery_status, style="Hint.TLabel", justify="left", wraplength=1050).pack(anchor="w")
        try:
            from .project_backup import project_backup_directory
            from .transaction_store import transaction_audit_timeline

            timeline = transaction_audit_timeline(project_backup_directory(), limit=5)
            rows = [f"{item.get('event', 'UNKNOWN')} · {item.get('transaction_id', '-') or '-'}" for item in timeline]
            audit_value = "\n".join(rows) if rows else text("ui.debug_footer.transaction_audit_empty")
        except Exception:
            audit_value = text("ui.debug_footer.transaction_audit_unavailable")
        self.transaction_audit_summary = StringVar(value=audit_value)
        ttk.Label(diagnosis, text=text("ui.debug_footer.transaction_audit_timeline"), style="Section.TLabel").pack(anchor="w", pady=(8, 2))
        ttk.Label(diagnosis, textvariable=self.transaction_audit_summary, style="Hint.TLabel", justify="left", wraplength=1050).pack(anchor="w")

        checkpoint_row = ttk.Frame(diagnosis, style="Card.TFrame")
        checkpoint_row.pack(fill="x", pady=(8, 0))
        ttk.Label(checkpoint_row, text=text("ui.debug_footer.checkpoint_restore_preview"), style="Section.TLabel").pack(side="left")
        ttk.Button(checkpoint_row, text=text("ui.debug_footer.checkpoint_preview_button"), command=self._show_checkpoint_restore_preview).pack(side="right")
        self.checkpoint_restore_summary = StringVar(value=self._checkpoint_restore_preview_summary())
        ttk.Label(diagnosis, textvariable=self.checkpoint_restore_summary, style="Hint.TLabel", justify="left", wraplength=1050).pack(anchor="w", pady=(2, 0))

        notebook.add(human, text=text('ui.debug_footer.menschenlog'))
        notebook.add(machine, text=text('ui.debug_footer.jsonl'))
        notebook.add(technical, text=text('ui.debug_footer.technik'))
        notebook.add(diagnosis, text=text('ui.debug_footer.diagnose'))
        return footer

    def _checkpoint_restore_preview_summary(self) -> str:
        try:
            from .checkpoint_store import default_checkpoint_root
            from .checkpoint_forensics import restore_dry_run, select_best_recovery_checkpoint
            from .checkpoint_trust_chain import inspect_trust_chain

            record = select_best_recovery_checkpoint(
                default_checkpoint_root(), required_domains=("project", "config", "queue", "backup")
            )
            dry = restore_dry_run(default_checkpoint_root(), record.generation_id)
            trust_report = inspect_trust_chain(default_checkpoint_root())
            trust = next((item.trust_level for item in trust_report.generations if item.generation_id == record.generation_id), "unknown")
            if not dry.ok:
                return text("ui.debug_footer.checkpoint_preview_failed", issues="; ".join(dry.issues))
            return text(
                "ui.debug_footer.checkpoint_preview_summary",
                generation=record.generation_id, changed=dry.changed_count, unchanged=dry.unchanged_count,
                fingerprint=dry.fingerprint_sha256[:16], trust=trust,
            )
        except Exception:
            return text("ui.debug_footer.checkpoint_preview_unavailable")

    def _show_checkpoint_restore_preview(self) -> None:
        try:
            from .checkpoint_store import default_checkpoint_root
            from .checkpoint_forensics import checkpoint_forensics_timeline, restore_dry_run, select_best_recovery_checkpoint
            from .checkpoint_trust_chain import inspect_trust_chain

            root = default_checkpoint_root()
            record = select_best_recovery_checkpoint(root, required_domains=("project", "config", "queue", "backup"))
            dry = restore_dry_run(root, record.generation_id)
            if not dry.ok:
                messagebox.showwarning(
                    text("ui.debug_footer.checkpoint_preview_dialog_title"),
                    text("ui.debug_footer.checkpoint_preview_failed", issues="; ".join(dry.issues)),
                )
                return
            actions = {"replace": 0, "create": 0, "delete": 0, "unchanged": 0}
            for item in dry.files:
                actions[item.action] = actions.get(item.action, 0) + 1
            timeline = checkpoint_forensics_timeline(root, limit=3)
            recent = ", ".join(str(item.get("event", "UNKNOWN")) for item in timeline) or "-"
            trust_report = inspect_trust_chain(root)
            trust = next((item.trust_level for item in trust_report.generations if item.generation_id == record.generation_id), "unknown")
            body = text(
                "ui.debug_footer.checkpoint_preview_dialog_body", generation=record.generation_id,
                fingerprint=dry.fingerprint_sha256, changed=dry.changed_count, unchanged=dry.unchanged_count,
                replace=actions["replace"], create=actions["create"], delete=actions["delete"],
                bytes=dry.total_restore_bytes, recent=recent, trust=trust,
            )
            messagebox.showinfo(text("ui.debug_footer.checkpoint_preview_dialog_title"), body)
            self.checkpoint_restore_summary.set(self._checkpoint_restore_preview_summary())
        except Exception as exc:
            messagebox.showwarning(
                text("ui.debug_footer.checkpoint_preview_dialog_title"),
                text("ui.debug_footer.checkpoint_preview_failed", issues=str(exc)),
            )

    def _append_machine_event(self, payload: dict) -> None:
        encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        self.machine_log_text.configure(state="normal")
        self.machine_log_text.insert(END, encoded + "\n")
        self.machine_log_text.see(END)
        self.machine_log_text.configure(state="disabled")
        self.last_machine_event.set(encoded[:1500])
        self.debug_summary.set(f"Build {build_label()} · Sitzung {self.logger.session_id} · letztes Ereignis {payload.get('event_id', 'UNKNOWN')}")

    def _create_diagnostic_report(self) -> None:
        from .diagnostics_service import write_diagnostic_report

        report = write_diagnostic_report(
            session_id=self.logger.session_id,
            project_file=Path(self.project_file),
            human_log=self.logger.human_path,
            machine_log=self.logger.jsonl_path,
        )
        self._event(
            "DIAGNOSTIC_REPORT_CREATED",
            "Diagnosebericht erstellt",
            str(report),
            level="success",
            solution="Bericht über den Logordner öffnen oder an den Support weitergeben.",
        )
