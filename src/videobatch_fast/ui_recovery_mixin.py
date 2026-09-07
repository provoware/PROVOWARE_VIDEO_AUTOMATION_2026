from __future__ import annotations

from pathlib import Path
from tkinter import StringVar, Toplevel, messagebox, ttk

from .job_journal import acknowledge_recovery, recoverable_batches, recovery_input_paths, recovery_options
from .text_resources import text


class UiRecoveryMixin:
    """Controlled recovery of interrupted batches without automatic execution."""

    def _initialize_recovery(self) -> None:
        self.recoverable_batches = recoverable_batches()
        if not self.recoverable_batches:
            return
        count = sum(int(item.get("recoverable_jobs", 0)) for item in self.recoverable_batches)
        self._event(
            "BATCH_RECOVERY_AVAILABLE",
            "Unterbrochene Verarbeitung erkannt",
            text("recovery.found.detail", batches=len(self.recoverable_batches), jobs=count),
            level="warning",
            solution=text("recovery.found.solution"),
        )
        self.root.after(350, self._offer_batch_recovery)

    def _offer_batch_recovery(self) -> None:
        payloads = list(self.recoverable_batches)
        if not payloads or self.runner.running:
            return
        count = sum(int(item.get("recoverable_jobs", 0)) for item in payloads)
        action = self._choose_recovery_action(payloads, count)
        if action == "clear":
            if self._clear_recoverable_projects(payloads):
                self.recoverable_batches = []
            return
        if action != "restore":
            self._event(
                "BATCH_RECOVERY_DEFERRED",
                text("recovery.deferred.title"),
                text("recovery.deferred.detail"),
                level="warning",
                solution=text("recovery.deferred.solution"),
            )
            return
        audio, media = recovery_input_paths(payloads)
        if not audio or not media:
            self._event(
                "BATCH_RECOVERY_INPUTS_MISSING",
                text("recovery.missing.title"),
                text("recovery.missing.detail"),
                level="error",
                solution=text("recovery.missing.solution"),
            )
            return
        self._apply_recovery_options(recovery_options(payloads))
        self.audios = list(dict.fromkeys([*self.audios, *audio]))
        self.media = list(dict.fromkeys([*self.media, *media]))
        archived = self._archive_recovery_journals(payloads)
        self.recoverable_batches = []
        self._refresh_file_trees()
        self._rebuild_pairs()
        self._autosave_project()
        self.guidance_text.set(text("recovery.restored.guidance", audio=len(audio), media=len(media)))
        self._event(
            "BATCH_RECOVERY_REQUEUED",
            text("recovery.restored.title"),
            text("recovery.restored.detail", jobs=min(len(audio), len(media)), journals=archived),
            level="success",
            solution=text("recovery.restored.solution"),
        )

    def _choose_recovery_action(self, payloads: list[dict[str, object]], count: int) -> str:
        choice = StringVar(value="later")
        dialog = Toplevel(self.root)
        dialog.title(text("recovery.dialog.title"))
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.resizable(False, False)
        body = ttk.Frame(dialog, padding=16)
        body.pack(fill="both", expand=True)
        ttk.Label(body, text="Wiederherstellbare Projekte", style="DialogTitle.TLabel").pack(anchor="w")
        ttk.Label(
            body,
            text=text("recovery.dialog.body", batches=len(payloads), jobs=count),
            style="Hint.TLabel",
            wraplength=520,
            justify="left",
        ).pack(anchor="w", pady=(5, 12))
        actions = ttk.Frame(body)
        actions.pack(fill="x")
        for column in range(3):
            actions.columnconfigure(column, weight=1)
        def finish(value: str) -> None:
            choice.set(value)
            dialog.destroy()
        ttk.Button(actions, text="Wiederherstellen", style="Accent.TButton", command=lambda: finish("restore")).grid(row=0, column=0, sticky="ew", padx=(0, 3))
        ttk.Button(actions, text="Später", command=lambda: finish("later")).grid(row=0, column=1, sticky="ew", padx=3)
        ttk.Button(actions, text="Liste leeren", style="Danger.TButton", command=lambda: finish("clear")).grid(row=0, column=2, sticky="ew", padx=(3, 0))
        dialog.protocol("WM_DELETE_WINDOW", lambda: finish("later"))
        dialog.bind("<Escape>", lambda _event: finish("later"))
        dialog.update_idletasks()
        x = max(0, self.root.winfo_rootx() + (self.root.winfo_width() - dialog.winfo_reqwidth()) // 2)
        y = max(0, self.root.winfo_rooty() + (self.root.winfo_height() - dialog.winfo_reqheight()) // 2)
        dialog.geometry(f"+{x}+{y}")
        self.root.wait_window(dialog)
        return choice.get()

    def _clear_recoverable_projects(self, payloads: list[dict[str, object]]) -> bool:
        if not messagebox.askyesno(
            "Wiederherstellungsliste leeren?",
            "Die Einträge werden aus der aktiven Wiederherstellungsliste entfernt und sicher im Verlauf archiviert. Quelldateien und erzeugte Medien werden nicht gelöscht.",
            parent=self.root,
        ):
            return False
        archived = self._archive_recovery_journals_with_action(payloads, action="dismissed_by_user")
        self.guidance_text.set(f"Wiederherstellungsliste geleert: {archived} Einträge sicher archiviert.")
        self._event(
            "BATCH_RECOVERY_CLEARED",
            "Wiederherstellungsliste geleert",
            f"{archived} Wiederherstellungseinträge wurden in den Verlauf verschoben.",
            level="success",
            solution="Quelldateien bleiben unverändert; bei Bedarf kann der Verlauf geprüft werden.",
        )
        return True

    def _archive_recovery_journals_with_action(self, payloads: list[dict[str, object]], *, action: str) -> int:
        archived = 0
        for payload in payloads:
            journal_path = payload.get("journal_path")
            if not journal_path:
                continue
            try:
                acknowledge_recovery(Path(str(journal_path)), action=action)
                archived += 1
            except (OSError, ValueError) as exc:
                self._event(
                    "BATCH_RECOVERY_JOURNAL_FAILED",
                    text("recovery.journal_error.title"),
                    str(exc),
                    level="error",
                    solution=text("recovery.journal_error.solution"),
                )
        return archived

    def _apply_recovery_options(self, options: dict[str, object]) -> None:
        variables = {
            "output_dir": self.output_dir,
            "output_mode": self.output_mode,
            "resolution": self.resolution,
            "codec": self.codec,
            "profile": self.profile,
            "verification": self.verification,
            "visual_effect": self.visual_effect,
            "transition": self.transition,
            "quick_mode": self.quick_mode,
            "assignment_mode": self.assignment_mode,
            "slideshow_transition": self.slideshow_transition,
            "slideshow_scene_sync": self.slideshow_scene_sync,
        }
        for key, variable in variables.items():
            if key in options:
                variable.set(str(options[key]))
        if "keep_lists" in options:
            self.keep_lists.set(bool(options["keep_lists"]))
        if "slideshow_scene_sync" in options:
            self.slideshow_scene_sync.set(bool(options["slideshow_scene_sync"]))

    def _archive_recovery_journals(self, payloads: list[dict[str, object]]) -> int:
        return self._archive_recovery_journals_with_action(payloads, action="controlled_requeue")
