from __future__ import annotations

import hashlib
import subprocess
import traceback
from dataclasses import FrozenInstanceError, dataclass
from pathlib import Path
from types import TracebackType

from .error_handling import error_definition


@dataclass(frozen=True, slots=True)
class RuntimeExceptionGuidance:
    code: str
    severity: str
    what: str
    how: str
    solutions: tuple[str, ...]


def classify_runtime_exception(
    exc_type: type[BaseException],
    exc: BaseException,
    *,
    scope: str = "runtime",
) -> RuntimeExceptionGuidance:
    """Map a Python exception to one stable, human-facing VideoBatch error contract."""
    message = str(exc).lower()
    if issubclass(exc_type, FrozenInstanceError) or "cannot assign to field" in message:
        code = "INTERNAL_IMMUTABLE_STATE_ERROR"
    elif issubclass(exc_type, PermissionError):
        code = "RUNTIME_PERMISSION_DENIED"
    elif issubclass(exc_type, FileNotFoundError):
        code = "RUNTIME_FILE_OR_TOOL_MISSING"
    elif issubclass(exc_type, MemoryError):
        code = "RUNTIME_MEMORY_LIMIT_REACHED"
    elif issubclass(exc_type, subprocess.CalledProcessError):
        code = "RUNTIME_SUBPROCESS_FAILED"
    elif issubclass(exc_type, (ValueError, TypeError)):
        code = "RUNTIME_INVALID_STATE"
    elif issubclass(exc_type, OSError):
        code = "RUNTIME_OS_ERROR"
    else:
        code = "RUNTIME_UNHANDLED_EXCEPTION"

    definition = error_definition(code)
    context_hint = {
        "tkinter": "Der Fehler wurde in einer Bedienaktion der Oberfläche abgefangen.",
        "thread": "Der Fehler wurde in einem Hintergrundvorgang isoliert.",
        "startup": "Der Fehler wurde während des Programmstarts abgefangen.",
        "runtime": "Der Fehler wurde vom zentralen Laufzeit-Schutz abgefangen.",
    }.get(scope, "Der Fehler wurde vom zentralen Laufzeit-Schutz abgefangen.")
    return RuntimeExceptionGuidance(
        code=code,
        severity=definition.severity,
        what=definition.title,
        how=f"{definition.cause} {context_hint} {definition.automatic_action}",
        solutions=tuple(
            item for item in (definition.solution, definition.alternative) if item.strip()
        ),
    )


def exception_fingerprint(
    exc_type: type[BaseException],
    exc: BaseException,
    tb: TracebackType | None,
    *,
    scope: str = "runtime",
) -> str:
    frames = traceback.extract_tb(tb) if tb is not None else []
    location = ""
    if frames:
        frame = frames[-1]
        location = f"{Path(frame.filename).name}:{frame.lineno}:{frame.name}"
    payload = "|".join((scope, exc_type.__name__, str(exc)[:500], location))
    return hashlib.sha256(payload.encode("utf-8", errors="replace")).hexdigest()[:16].upper()
