from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .preparation_assistant import PreparationCheck

_VALID_STATES = {"ok", "warning", "error"}
_STATE_RANK = {"error": 0, "warning": 1, "ok": 2}


@dataclass(frozen=True, slots=True)
class StartupStep:
    key: str
    title: str
    status: str
    detail: str
    action: str = ""

    def __post_init__(self) -> None:
        if self.status not in _VALID_STATES:
            raise ValueError(f"Ungültiger Startstatus: {self.status}")


@dataclass(frozen=True, slots=True)
class StartupReadiness:
    steps: tuple[StartupStep, ...]
    ready_count: int
    warning_count: int
    error_count: int
    next_step_key: str

    @property
    def ready(self) -> bool:
        return self.error_count == 0 and self.warning_count == 0

    @property
    def overall_status(self) -> str:
        if self.error_count:
            return "error"
        if self.warning_count:
            return "warning"
        return "ok"


def _worst(checks: Iterable[PreparationCheck]) -> PreparationCheck | None:
    available = tuple(checks)
    if not available:
        return None
    return min(available, key=lambda item: _STATE_RANK.get(item.status, -1))


def _group_step(
    index: dict[str, PreparationCheck],
    *,
    key: str,
    title: str,
    members: tuple[str, ...],
    ok_detail: str,
) -> StartupStep:
    checks = tuple(index[name] for name in members if name in index)
    worst = _worst(checks)
    if worst is None:
        return StartupStep(key, title, "warning", "Prüfung noch nicht verfügbar")
    if worst.status == "ok":
        return StartupStep(key, title, "ok", ok_detail)
    return StartupStep(key, title, worst.status, worst.detail, worst.action)


def build_startup_readiness(
    *,
    project_name: str,
    checks: Iterable[PreparationCheck],
) -> StartupReadiness:
    """Derive the visible start routine only from checks already performed."""

    index = {item.key: item for item in checks}
    steps = [
        StartupStep(
            "project",
            "Projekt",
            "ok" if project_name.strip() else "warning",
            project_name.strip() or "Projektname fehlt",
        ),
        _group_step(
            index,
            key="media",
            title="Medien",
            members=("audio", "media", "analysis"),
            ok_detail="Audio und Medien bereit",
        ),
        _group_step(
            index,
            key="effects",
            title="Effekte & Modus",
            members=("settings",),
            ok_detail="Geprüfter Modus aktiv",
        ),
        _group_step(
            index,
            key="output",
            title="Ausgabe",
            members=("output", "archive"),
            ok_detail="Ausgabeziel bereit",
        ),
        _group_step(
            index,
            key="pairing",
            title="Zuordnung",
            members=("pairing",),
            ok_detail="Aufträge vorbereitet",
        ),
    ]

    precursor_errors = sum(step.status == "error" for step in steps)
    precursor_warnings = sum(step.status == "warning" for step in steps)
    if precursor_errors:
        render_status, render_detail = "error", "Blockiert durch offene Pflichtangaben"
    elif precursor_warnings:
        render_status, render_detail = "warning", "Prüfung empfohlen"
    else:
        render_status, render_detail = "ok", "Render bereit"
    steps.append(StartupStep("render", "Render bereit", render_status, render_detail))

    ready_count = sum(step.status == "ok" for step in steps)
    warning_count = sum(step.status == "warning" for step in steps)
    error_count = sum(step.status == "error" for step in steps)
    next_step = next((step for step in steps[:-1] if step.status != "ok"), steps[-1])
    return StartupReadiness(
        tuple(steps),
        ready_count,
        warning_count,
        error_count,
        next_step.key,
    )
