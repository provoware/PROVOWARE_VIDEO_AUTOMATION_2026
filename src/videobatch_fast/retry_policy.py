from __future__ import annotations

from dataclasses import dataclass

from .models import JobResult


@dataclass(frozen=True, slots=True)
class RetryDecision:
    category: str
    automatic_retry_allowed: bool
    safe_fallback_allowed: bool
    reason: str


_CANCEL_MARKERS = (
    "abgebrochen",
    "cancelled",
    "canceled",
    "interrupted",
)
_HARD_BLOCK_MARKERS = (
    "no space left on device",
    "kein speicherplatz",
    "permission denied",
    "keine schreibberechtigung",
    "read-only file system",
    "schreibgeschützt",
    "no such file or directory",
    "datei fehlt",
    "audiodatei fehlt",
    "mediendatei fehlt",
    "ffmpeg fehlt",
    "ffmpeg wurde nicht gefunden",
    "unknown encoder",
    "encoder not found",
)
_INVALID_INPUT_MARKERS = (
    "invalid data found when processing input",
    "invalid argument",
    "moov atom not found",
    "could not find codec parameters",
)
_TRANSIENT_MARKERS = (
    "resource temporarily unavailable",
    "device or resource busy",
    "temporarily unavailable",
    "timed out",
    "timeout",
    "input/output error",
    "i/o error",
    "broken pipe",
)


def classify_retry(result: JobResult) -> RetryDecision:
    """Classify whether repeating the unchanged operation can reasonably help.

    Automatic retries are intentionally fail-closed. Safe fallback encoding is
    broader: format/codec failures may benefit from a different command, while
    environmental blockers such as disk-full or permissions must be fixed first.
    """
    text = str(result.message or "").casefold()
    returncode = int(result.returncode)

    if any(marker in text for marker in _CANCEL_MARKERS) or returncode in {130, 143}:
        return RetryDecision(
            "cancelled",
            False,
            False,
            "Der Auftrag wurde kontrolliert beendet; automatisches Wiederholen würde den Nutzerabbruch missachten.",
        )

    if returncode == 127 or any(marker in text for marker in _HARD_BLOCK_MARKERS):
        return RetryDecision(
            "environment_blocker",
            False,
            False,
            "Die Umgebung muss sich zuerst ändern; eine identische Wiederholung kann den Fehler nicht beheben.",
        )

    if any(marker in text for marker in _INVALID_INPUT_MARKERS):
        return RetryDecision(
            "invalid_input",
            False,
            False,
            "Die Eingabe oder der Auftrag ist ungültig; blindes Wiederholen wäre deterministisch erfolglos.",
        )

    if any(marker in text for marker in _TRANSIENT_MARKERS):
        return RetryDecision(
            "transient",
            True,
            True,
            "Der Fehler kann vorübergehend sein; genau ein begrenzter Wiederholungsversuch ist vertretbar.",
        )

    if returncode == 0 and not result.success:
        return RetryDecision(
            "verification_failed",
            False,
            True,
            "Der Prozess lief durch, aber die Ausgabeprüfung scheiterte; eine sichere Alternativcodierung kann helfen.",
        )

    return RetryDecision(
        "processing",
        False,
        True,
        "Kein transienter Fehler ist belegt; keine identische automatische Wiederholung, aber sichere Alternativcodierung bleibt erlaubt.",
    )


def automatic_retry_allowed(result: JobResult) -> bool:
    return classify_retry(result).automatic_retry_allowed


def safe_fallback_allowed(result: JobResult) -> bool:
    return classify_retry(result).safe_fallback_allowed
