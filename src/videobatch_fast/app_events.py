from __future__ import annotations

import time
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, ClassVar, overload

from .event_registry import (
    EventPayloadMode,
    EventRegistryError,
    noisy_event_names,
    terminal_event_names,
    validate_event_payload,
)

EVENT_SCHEMA_VERSION = 1

NOISY_EVENT_NAMES = noisy_event_names()
TERMINAL_EVENT_NAMES = terminal_event_names()


class AppEventError(ValueError):
    """Raised when an event violates the in-process event contract."""


class TypedEventPayload(Mapping[str, object]):
    """Read-only mapping view for frozen payload dataclasses."""

    _field_names: ClassVar[tuple[str, ...]] = ()

    def __iter__(self) -> Iterator[str]:
        return iter(self._field_names)

    def __len__(self) -> int:
        return len(self._field_names)

    def __getitem__(self, key: str) -> object:
        if key not in self._field_names:
            raise KeyError(key)
        return getattr(self, key)

    def as_dict(self) -> dict[str, object]:
        return {name: getattr(self, name) for name in self._field_names}


def _operation_id(payload: Mapping[str, object]) -> str:
    value = str(payload.get("operation_id", "general") or "general").strip()
    return value[:120] or "general"


@dataclass(frozen=True, slots=True)
class AppEvent:
    """Immutable, versioned event passed between workers and the UI thread."""

    name: str
    payload: Mapping[str, object]
    operation_id: str = ""
    sequence: int = 0
    created_monotonic_ns: int = 0
    schema_version: int = EVENT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        name = str(self.name).strip()
        if self.schema_version != EVENT_SCHEMA_VERSION:
            raise AppEventError(
                f"Nicht unterstützte Ereignisschema-Version {self.schema_version}; "
                f"erwartet wird {EVENT_SCHEMA_VERSION}."
            )
        if self.sequence < 0:
            raise AppEventError("Ereignissequenz darf nicht negativ sein.")
        if not isinstance(self.payload, Mapping):
            raise AppEventError("Ereignisnutzdaten müssen eine Zuordnung sein.")
        payload: Mapping[str, object]
        mode: EventPayloadMode
        if isinstance(self.payload, TypedEventPayload):
            payload = self.payload
            mode = "typed"
        else:
            payload = MappingProxyType(dict(self.payload))
            mode = "mapping"
        try:
            validate_event_payload(name, payload, mode=mode)
        except EventRegistryError as exc:
            raise AppEventError(str(exc)) from exc
        operation_id = str(self.operation_id or _operation_id(payload)).strip()[:120] or "general"
        created = int(self.created_monotonic_ns or time.monotonic_ns())
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "payload", payload)
        object.__setattr__(self, "operation_id", operation_id)
        object.__setattr__(self, "created_monotonic_ns", created)

    @classmethod
    def from_legacy(cls, name: str, payload: Mapping[str, object]) -> AppEvent:
        """Compatibility adapter used only by EventBuffer.put_legacy()."""
        copied = dict(payload)
        try:
            validate_event_payload(str(name).strip(), copied, mode="legacy")
        except EventRegistryError as exc:
            raise AppEventError(str(exc)) from exc
        event = cls.__new__(cls)
        object.__setattr__(event, "name", str(name).strip())
        object.__setattr__(event, "payload", MappingProxyType(copied))
        object.__setattr__(event, "operation_id", _operation_id(copied))
        object.__setattr__(event, "sequence", 0)
        object.__setattr__(event, "created_monotonic_ns", time.monotonic_ns())
        object.__setattr__(event, "schema_version", EVENT_SCHEMA_VERSION)
        return event

    def with_sequence(self, sequence: int) -> AppEvent:
        if sequence < 1:
            raise AppEventError("Gepufferte Ereignisse benötigen eine positive Sequenz.")
        event = type(self).__new__(type(self))
        object.__setattr__(event, "name", self.name)
        object.__setattr__(event, "payload", self.payload)
        object.__setattr__(event, "operation_id", self.operation_id)
        object.__setattr__(event, "sequence", sequence)
        object.__setattr__(event, "created_monotonic_ns", self.created_monotonic_ns)
        object.__setattr__(event, "schema_version", self.schema_version)
        return event

    @property
    def is_noisy(self) -> bool:
        return self.name in NOISY_EVENT_NAMES

    @property
    def is_terminal(self) -> bool:
        return self.name in TERMINAL_EVENT_NAMES

    def legacy_pair(self) -> tuple[str, dict[str, Any]]:
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
