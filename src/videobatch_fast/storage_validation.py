from __future__ import annotations

import shutil
from .models import PairJob, BatchOptions
from typing import Callable

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .validation import ValidationIssue


def _validate_storage(jobs: list[PairJob], options: BatchOptions,
                      estimate: Callable) -> list[ValidationIssue]:
    from .validation import ValidationIssue

    issues: list[ValidationIssue] = []
    for requirement in estimate(jobs, options):
        directory = requirement.directories[0]
        try:
            free = shutil.disk_usage(directory).free
        except OSError as exc:
            issues.append(ValidationIssue(
                "DISK_CHECK_UNKNOWN", "Freien Speicher nicht überprüfbar",
                f"{directory}: {exc}",
                "Ziel-Laufwerk prüfen und genügend freien Speicher bereitstellen.",
                blocking=False,
            ))
            continue
        if free < requirement.required_bytes:
            targets = ", ".join(str(path) for path in requirement.directories)
            issues.append(ValidationIssue(
                "DISK_LOW",
                "Wenig freier Speicher",
                (
                    f"Ziel-Dateisystem für {targets} · frei: {free / 1024**3:.1f} GB · "
                    f"mit Sicherheitsreserve benötigt: {requirement.required_bytes / 1024**3:.1f} GB"
                ),
                "Wähle einen anderen Ordner oder erstelle einen Ausgabeordner auf einem Laufwerk mit mehr Platz.",
                actions=("choose_output", "create_output_folder"),
            ))
    return issues
