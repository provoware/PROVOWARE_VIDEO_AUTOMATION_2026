from __future__ import annotations

import json
from pathlib import Path
from tkinter import END, StringVar, Text, ttk

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

        notebook.add(human, text=text('ui.debug_footer.menschenlog'))
        notebook.add(machine, text=text('ui.debug_footer.jsonl'))
        notebook.add(technical, text=text('ui.debug_footer.technik'))
        notebook.add(diagnosis, text=text('ui.debug_footer.diagnose'))
        return footer

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
