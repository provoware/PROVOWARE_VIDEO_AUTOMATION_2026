from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

from .app_events import TypedEventPayload
from .models import JobResult, PairJob


@dataclass(frozen=True, slots=True)
class BatchStartedPayload(TypedEventPayload):
    _field_names = ("total",)

    total: int

    def __post_init__(self) -> None:
        if self.total < 0:
            raise ValueError("Gesamtzahl der Aufträge darf nicht negativ sein.")


@dataclass(frozen=True, slots=True)
class JobStartedPayload(TypedEventPayload):
    _field_names = ("job", "position", "total")

    job: PairJob
    position: int
    total: int

    def __post_init__(self) -> None:
        _validate_position(self.position, self.total)


@dataclass(frozen=True, slots=True)
class JobFinishedPayload(TypedEventPayload):
    _field_names = ("result", "position", "total")

    result: JobResult
    position: int
    total: int

    def __post_init__(self) -> None:
        _validate_position(self.position, self.total)


@dataclass(frozen=True, slots=True)
class BatchFailedInternalPayload(TypedEventPayload):
    _field_names = ("job", "position", "total", "message", "traceback", "protection")

    job: PairJob | None
    position: int
    total: int
    message: str
    traceback: str
    protection: str

    def __post_init__(self) -> None:
        if not self.message.strip():
            raise ValueError("Interner Stapelfehler benötigt eine Meldung.")
        if not self.protection.strip():
            raise ValueError("Interner Stapelfehler benötigt eine Schutzmaßnahme.")
        if self.job is None:
            if self.position != 0 or self.total < 0:
                raise ValueError("Fehler ohne Einzelauftrag benötigt Position 0 und eine nichtnegative Gesamtzahl.")
        else:
            _validate_position(self.position, self.total)


@dataclass(frozen=True, slots=True)
class BatchFinishedPayload(TypedEventPayload):
    _field_names = (
        "terminal_event",
        "cancelled",
        "successes",
        "failures",
        "unprocessed",
        "total",
        "elapsed",
        "results",
        "internal_error",
        "callback_errors",
        "retry_queue",
    )

    terminal_event: str
    cancelled: bool
    successes: int
    failures: int
    unprocessed: int
    total: int
    elapsed: float
    results: tuple[JobResult, ...]
    internal_error: str
    callback_errors: tuple[str, ...]
    retry_queue: Mapping[str, object]

    def __post_init__(self) -> None:
        if not self.terminal_event.strip():
            raise ValueError("Stapelabschluss benötigt ein terminales Ereignis.")
        counts = (self.successes, self.failures, self.unprocessed, self.total)
        if any(value < 0 for value in counts):
            raise ValueError("Stapelzähler dürfen nicht negativ sein.")
        if self.successes + self.failures + self.unprocessed != self.total:
            raise ValueError("Stapelzähler müssen exakt der Gesamtzahl entsprechen.")
        if len(self.results) != self.successes + self.failures:
            raise ValueError("Ergebniszahl stimmt nicht mit Erfolgen und Fehlern überein.")
        if self.elapsed < 0:
            raise ValueError("Stapelzeit darf nicht negativ sein.")
        object.__setattr__(self, "results", tuple(self.results))
        object.__setattr__(self, "callback_errors", tuple(self.callback_errors))
        object.__setattr__(self, "retry_queue", MappingProxyType(dict(self.retry_queue)))


def _validate_position(position: int, total: int) -> None:
    if total < 1 or position < 1 or position > total:
        raise ValueError(f"Ungültige Auftragsposition {position}/{total}.")
