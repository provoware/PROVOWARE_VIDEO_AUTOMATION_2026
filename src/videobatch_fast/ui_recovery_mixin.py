from __future__ import annotations

from pathlib import Path
from tkinter import messagebox

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
        accepted = messagebox.askyesno(
            text("recovery.dialog.title"),
            text("recovery.dialog.body", batches=len(payloads), jobs=count),
        )
        if not accepted:
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
        archived = 0
        for payload in payloads:
            journal_path = payload.get("journal_path")
            if not journal_path:
                continue
            try:
                acknowledge_recovery(Path(str(journal_path)), action="controlled_requeue")
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
