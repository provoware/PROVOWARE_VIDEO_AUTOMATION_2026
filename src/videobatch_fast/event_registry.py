from __future__ import annotations

import importlib
import re
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Literal

EventPayloadMode = Literal["typed", "mapping", "legacy"]
_EVENT_NAME_RE = re.compile(r"^[a-z][a-z0-9_.-]{1,79}$")


class EventRegistryError(ValueError):
    """Raised when an event violates the central registry contract."""


@dataclass(frozen=True, slots=True)
class EventSpec:
    name: str
    handler: str
    payload_type: str
    modes: frozenset[EventPayloadMode]
    required_fields: tuple[str, ...]
    terminal: bool = False
    noisy: bool = False

    def __post_init__(self) -> None:
        if not _EVENT_NAME_RE.fullmatch(self.name):
            raise EventRegistryError(f"Ungültige registrierte Ereigniskennung: {self.name!r}")
        if not self.handler.startswith("_handle_"):
            raise EventRegistryError(f"Ungültiger Handler für {self.name}: {self.handler!r}")
        if not self.payload_type or "." not in self.payload_type:
            raise EventRegistryError(f"Ungültiger Payloadtyp für {self.name}: {self.payload_type!r}")
        if not self.modes:
            raise EventRegistryError(f"Ereignis {self.name} benötigt mindestens einen Erzeugungsmodus.")
        if self.terminal and self.noisy:
            raise EventRegistryError(f"Terminales Ereignis {self.name} darf nicht verrauscht sein.")
        if len(set(self.required_fields)) != len(self.required_fields):
            raise EventRegistryError(f"Doppelte Pflichtfelder für {self.name}.")


def _spec(
    name: str,
    handler: str,
    payload_type: str,
    modes: tuple[EventPayloadMode, ...],
    required_fields: tuple[str, ...],
    *,
    terminal: bool = False,
    noisy: bool = False,
) -> EventSpec:
    return EventSpec(
        name=name,
        handler=handler,
        payload_type=payload_type,
        modes=frozenset(modes),
        required_fields=required_fields,
        terminal=terminal,
        noisy=noisy,
    )


_SPECS = (
    _spec(
        "batch_started",
        "_handle_batch_started",
        "videobatch_fast.runner_events.BatchStartedPayload",
        ("typed",),
        ("total",),
    ),
    _spec(
        "job_started",
        "_handle_job_started",
        "videobatch_fast.runner_events.JobStartedPayload",
        ("typed",),
        ("job", "position", "total"),
    ),
    _spec("command", "_handle_command", "builtins.dict", ("mapping",), ("command",)),
    _spec(
        "progress",
        "_handle_progress_event",
        "builtins.dict",
        ("mapping",),
        ("snapshot", "job"),
        noisy=True,
    ),
    _spec(
        "log",
        "_handle_log_event",
        "builtins.dict",
        ("mapping", "legacy"),
        ("message",),
        noisy=True,
    ),
    _spec(
        "job_finished",
        "_handle_job_finished",
        "videobatch_fast.runner_events.JobFinishedPayload",
        ("typed",),
        ("result", "position", "total"),
        terminal=True,
    ),
    _spec(
        "job_failed_internal",
        "_handle_job_internal_error",
        "builtins.dict",
        ("mapping",),
        (
            "job",
            "position",
            "total",
            "message",
            "traceback",
            "protection",
            "recoverable",
            "consecutive_failures",
            "failure_limit",
        ),
    ),
    _spec(
        "batch_failed_internal",
        "_handle_batch_internal_error",
        "videobatch_fast.runner_events.BatchFailedInternalPayload",
        ("typed",),
        ("job", "position", "total", "message", "traceback", "protection"),
    ),
    _spec(
        "batch_finished",
        "_handle_batch_finished",
        "videobatch_fast.runner_events.BatchFinishedPayload",
        ("typed",),
        (
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
        ),
        terminal=True,
    ),
    _spec(
        "retry_queue_updated",
        "_handle_retry_queue_updated",
        "builtins.dict",
        ("mapping",),
        ("entry", "summary"),
    ),
    _spec(
        "preview_ready",
        "_handle_preview_ready",
        "builtins.dict",
        ("legacy",),
        ("request_id", "path", "preview"),
        terminal=True,
    ),
    _spec(
        "preview_failed",
        "_handle_preview_failed",
        "builtins.dict",
        ("legacy",),
        ("request_id", "message"),
        terminal=True,
    ),
    _spec(
        "selection_preview_ready",
        "_handle_selection_preview_ready",
        "videobatch_fast.selection_preview_events.SelectionPreviewReadyPayload",
        ("typed",),
        ("token", "path", "preview", "info", "size_bytes", "include_image"),
        terminal=True,
    ),
    _spec(
        "selection_preview_failed",
        "_handle_selection_preview_failed",
        "videobatch_fast.selection_preview_events.SelectionPreviewFailedPayload",
        ("typed",),
        ("token", "path", "message", "include_image"),
        terminal=True,
    ),
    _spec(
        "archive_finished",
        "_handle_archive_finished",
        "builtins.dict",
        ("legacy",),
        ("message", "failures"),
        terminal=True,
    ),
    _spec(
        "update_finished",
        "_handle_update_finished",
        "builtins.dict",
        ("legacy",),
        ("result",),
        terminal=True,
    ),
    _spec(
        "assurance_finished",
        "_handle_assurance_finished",
        "builtins.dict",
        ("legacy",),
        ("results",),
        terminal=True,
    ),
    _spec(
        "fault_lab_finished",
        "_handle_fault_lab_finished",
        "builtins.dict",
        ("legacy",),
        ("results",),
        terminal=True,
    ),
    _spec(
        "waveform_ready",
        "_handle_waveform_ready",
        "builtins.dict",
        ("legacy",),
        ("path", "analysis"),
        terminal=True,
    ),
    _spec(
        "waveform_failed",
        "_handle_waveform_failed",
        "builtins.dict",
        ("legacy",),
        ("path", "message"),
        terminal=True,
    ),
)

if len({spec.name for spec in _SPECS}) != len(_SPECS):
    raise EventRegistryError("Das Ereignisregister enthält doppelte Kennungen.")

EVENT_REGISTRY: Mapping[str, EventSpec] = MappingProxyType({spec.name: spec for spec in _SPECS})


def registered_event_names() -> frozenset[str]:
    return frozenset(EVENT_REGISTRY)


def terminal_event_names() -> frozenset[str]:
    return frozenset(spec.name for spec in _SPECS if spec.terminal)


def noisy_event_names() -> frozenset[str]:
    return frozenset(spec.name for spec in _SPECS if spec.noisy)


def get_event_spec(name: str) -> EventSpec:
    try:
        return EVENT_REGISTRY[name]
    except KeyError as exc:
        raise EventRegistryError(f"Unbekanntes AppEvent: {name!r}") from exc


def payload_type_name(payload: object) -> str:
    cls = type(payload)
    return f"{cls.__module__}.{cls.__qualname__}"


def resolve_payload_type(spec: EventSpec) -> type[object]:
    module_name, _, attribute = spec.payload_type.rpartition(".")
    module = importlib.import_module(module_name)
    resolved = getattr(module, attribute)
    if not isinstance(resolved, type):
        raise EventRegistryError(f"Payloadtyp von {spec.name} ist keine Klasse: {spec.payload_type}")
    return resolved


def validate_event_payload(
    name: str,
    payload: Mapping[str, object],
    *,
    mode: EventPayloadMode,
) -> EventSpec:
    spec = get_event_spec(name)
    if mode not in spec.modes:
        allowed = ", ".join(sorted(spec.modes))
        raise EventRegistryError(
            f"Ereignis {name!r} erlaubt Modus {mode!r} nicht; erlaubt: {allowed}."
        )
    missing = tuple(field for field in spec.required_fields if field not in payload)
    if missing:
        raise EventRegistryError(f"Ereignis {name!r} ohne Pflichtfelder: {', '.join(missing)}")
    if mode == "typed" and payload_type_name(payload) != spec.payload_type:
        raise EventRegistryError(
            f"Ereignis {name!r} erwartet {spec.payload_type}, erhalten: {payload_type_name(payload)}."
        )
    return spec


def build_event_handlers(target: object) -> dict[str, object]:
    handlers: dict[str, object] = {}
    for spec in _SPECS:
        handler = getattr(target, spec.handler, None)
        if callable(handler):
            handlers[spec.name] = handler
    return handlers
