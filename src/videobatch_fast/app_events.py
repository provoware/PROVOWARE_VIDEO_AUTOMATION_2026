from __future__ import annotations

import re
import time
from collections.abc import Iterator, Mapping
from dataclasses import dataclass, replace
from types import MappingProxyType
from typing import Any, TypeAlias, overload

EVENT_SCHEMA_VERSION = 1
_EVENT_NAME_RE = re.compile(r"^[a-z][a-z0-9_.-]{1,79}$")

NOISY_EVENT_NAMES = frozenset({"log", "progress"})
TERMINAL_EVENT_NAMES = frozenset(
    {
        "archive_finished",
        "assurance_finished",
        "batch_finished",
        "fault_lab_finished",
        "job_finished",
        "preview_failed",
        "preview_ready",
        "selection_preview_failed",
        "selection_preview_ready",
        "update_finished",
        "waveform_failed",
        "waveform_ready",
    }
)

LegacyEvent: TypeAlias = tuple[str, dict[str, Any]]


class AppEventError(ValueError):
    """Raised when an event violates the in-process event contract."""


def _event_name(value: object) -> str:
    name = str(value).strip()
    if not _EVENT_NAME_RE.fullmatch(name):
        raise AppEventError(f"Ungültige Ereigniskennung: {name!r}")
    return name


def _operation_id(payload: Mapping[str, object]) -> str:
    value = str(payload.get("operation_id", "general") or "general").strip()
    return value[:120] or "general"


@dataclass(frozen=True, slots=True)
class AppEvent:
    """Immutable, versioned event passed between workers and the UI thread.

    The top-level payload is copied and exposed read-only. Existing consumers may
    still unpack or index an event like the historic ``(name, payload)`` tuple.
    """

    name: str
    payload: Mapping[str, object]
    operation_id: str = ""
    sequence: int = 0
    created_monotonic_ns: int = 0
    schema_version: int = EVENT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        name = _event_name(self.name)
        if self.schema_version != EVENT_SCHEMA_VERSION:
            raise AppEventError(
                f"Nicht unterstützte Ereignisschema-Version {self.schema_version}; "
                f"erwartet wird {EVENT_SCHEMA_VERSION}."
            )
        if self.sequence < 0:
            raise AppEventError("Ereignissequenz darf nicht negativ sein.")
        if not isinstance(self.payload, Mapping):
            raise AppEventError("Ereignisnutzdaten müssen eine Zuordnung sein.")
        payload = MappingProxyType(dict(self.payload))
        operation_id = str(self.operation_id or _operation_id(payload)).strip()[:120] or "general"
        created = int(self.created_monotonic_ns or time.monotonic_ns())
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "payload", payload)
        object.__setattr__(self, "operation_id", operation_id)
        object.__setattr__(self, "created_monotonic_ns", created)

    @classmethod
    def from_legacy(cls, name: str, payload: Mapping[str, object]) -> AppEvent:
        copied = dict(payload)
        return cls(name=name, payload=copied, operation_id=_operation_id(copied))

    def with_sequence(self, sequence: int) -> AppEvent:
        if sequence < 1:
            raise AppEventError("Gepufferte Ereignisse benötigen eine positive Sequenz.")
        return replace(self, sequence=sequence)

    @property
    def is_noisy(self) -> bool:
        return self.name in NOISY_EVENT_NAMES

    @property
    def is_terminal(self) -> bool:
        return self.name in TERMINAL_EVENT_NAMES

    def legacy_pair(self) -> LegacyEvent:
        return self.name, dict(self.payload)

    def __iter__(self) -> Iterator[object]:
        yield self.name
        yield dict(self.payload)

    @overload
    def __getitem__(self, index: int) -> str | dict[str, Any]: ...

    @overload
    def __getitem__(self, index: slice) -> tuple[object, ...]: ...

    def __getitem__(self, index: int | slice) -> object:
        pair = self.legacy_pair()
        return pair[index]

    def __len__(self) -> int:
        return 2


EventInput: TypeAlias = AppEvent | LegacyEvent


def normalize_event(item: EventInput, *, sequence: int) -> AppEvent:
    if isinstance(item, AppEvent):
        return item.with_sequence(sequence)
    if not isinstance(item, tuple) or len(item) != 2:
        raise AppEventError("Ereignis muss AppEvent oder ein Paar aus Kennung und Nutzdaten sein.")
    name, payload = item
    if not isinstance(name, str) or not isinstance(payload, dict):
        raise AppEventError("Legacy-Ereignis benötigt str-Kennung und dict-Nutzdaten.")
    return AppEvent.from_legacy(name, payload).with_sequence(sequence)
