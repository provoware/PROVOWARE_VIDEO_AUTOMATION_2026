from __future__ import annotations

import os
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

RECURRENCE_KINDS = {"once", "daily", "weekly"}
CATCH_UP_POLICIES = {"skip", "run_once"}
DST_POLICIES = {"later", "earlier"}
MAX_OCCURRENCES = 366
MAX_INTERVAL = 30
DEFAULT_DST_POLICY = "later"
DEFAULT_CATCH_UP_POLICY = "run_once"
START_GRACE_SECONDS = 120


def local_timezone_name() -> str:
    env_name = os.environ.get("TZ", "").strip()
    if env_name:
        try:
            ZoneInfo(env_name)
            return env_name
        except ZoneInfoNotFoundError:
            pass
    timezone_file = Path("/etc/timezone")
    try:
        candidate = timezone_file.read_text(encoding="utf-8").strip()
        if candidate:
            ZoneInfo(candidate)
            return candidate
    except (OSError, ZoneInfoNotFoundError):
        pass
    try:
        localtime = Path("/etc/localtime")
        resolved = localtime.resolve()
        marker = "/zoneinfo/"
        text = str(resolved)
        if marker in text:
            candidate = text.split(marker, 1)[1]
            ZoneInfo(candidate)
            return candidate
    except (OSError, ZoneInfoNotFoundError):
        pass
    tzinfo = datetime.now().astimezone().tzinfo
    key = getattr(tzinfo, "key", "")
    if key:
        return str(key)
    return "UTC"


def _zone(name: str) -> ZoneInfo:
    try:
        return ZoneInfo(str(name))
    except ZoneInfoNotFoundError as exc:
        raise ValueError(f"Unbekannte Zeitzone: {name}") from exc


def resolve_local_wall_time(
    day: date,
    wall_time: time,
    timezone_name: str,
    *,
    dst_policy: str = DEFAULT_DST_POLICY,
) -> datetime | None:
    if dst_policy not in DST_POLICIES:
        raise ValueError("Unzulässige DST-Regel.")
    zone = _zone(timezone_name)
    naive = datetime.combine(day, wall_time.replace(tzinfo=None))
    valid: list[datetime] = []
    for fold in (0, 1):
        candidate = naive.replace(tzinfo=zone, fold=fold)
        roundtrip = candidate.astimezone(timezone.utc).astimezone(zone)
        if roundtrip.replace(tzinfo=None) == naive and roundtrip.fold == fold:
            valid.append(candidate)
    if not valid:
        return None
    if len(valid) == 1 or valid[0].utcoffset() == valid[-1].utcoffset():
        return valid[0]
    return valid[-1] if dst_policy == "later" else valid[0]


def normalize_recurrence(
    recurrence: dict[str, Any] | None,
    *,
    scheduled_at: datetime,
    timezone_name: str | None = None,
) -> dict[str, Any]:
    source = dict(recurrence or {})
    kind = str(source.get("kind", "once")).strip().lower()
    if kind not in RECURRENCE_KINDS:
        raise ValueError("Wiederholung muss einmalig, täglich oder wöchentlich sein.")
    interval = int(source.get("interval", 1))
    if interval < 1 or interval > MAX_INTERVAL:
        raise ValueError(f"Wiederholungsintervall muss zwischen 1 und {MAX_INTERVAL} liegen.")
    max_occurrences = int(source.get("max_occurrences", 1 if kind == "once" else 10))
    if kind == "once":
        max_occurrences = 1
    if max_occurrences < 1 or max_occurrences > MAX_OCCURRENCES:
        raise ValueError(f"Maximale Läufe müssen zwischen 1 und {MAX_OCCURRENCES} liegen.")
    catch_up_policy = str(source.get("catch_up_policy", DEFAULT_CATCH_UP_POLICY)).strip().lower()
    if catch_up_policy not in CATCH_UP_POLICIES:
        raise ValueError("Catch-up-Regel muss skip oder run_once sein.")
    dst_policy = str(source.get("dst_policy", DEFAULT_DST_POLICY)).strip().lower()
    if dst_policy not in DST_POLICIES:
        raise ValueError("DST-Regel muss later oder earlier sein.")
    tz_name = str(source.get("timezone") or timezone_name or local_timezone_name()).strip()
    zone = _zone(tz_name)
    anchor = scheduled_at.astimezone(zone) if scheduled_at.tzinfo else scheduled_at.replace(tzinfo=zone)
    resolved = resolve_local_wall_time(anchor.date(), anchor.timetz().replace(tzinfo=None), tz_name, dst_policy=dst_policy)
    if resolved is None:
        raise ValueError("Die gewählte lokale Uhrzeit existiert wegen der Sommerzeitumstellung nicht.")
    return {
        "kind": kind,
        "interval": interval,
        "max_occurrences": max_occurrences,
        "catch_up_policy": catch_up_policy,
        "timezone": tz_name,
        "dst_policy": dst_policy,
    }


def recurrence_label(recurrence: dict[str, Any]) -> str:
    kind = str(recurrence.get("kind", "once"))
    interval = int(recurrence.get("interval", 1) or 1)
    maximum = int(recurrence.get("max_occurrences", 1) or 1)
    if kind == "once":
        return "Einmalig"
    unit = "Tag" if kind == "daily" else "Woche"
    if interval == 1:
        base = "Täglich" if kind == "daily" else "Wöchentlich"
    else:
        plural = "Tage" if kind == "daily" else "Wochen"
        base = f"Alle {interval} {plural}"
    return f"{base} · max. {maximum} Läufe"


def occurrence_at_index(record: dict[str, Any], occurrence_index: int) -> datetime | None:
    if occurrence_index < 1:
        raise ValueError("Occurrence-Index muss mindestens 1 sein.")
    recurrence = record.get("recurrence") if isinstance(record.get("recurrence"), dict) else {}
    kind = str(recurrence.get("kind", "once"))
    maximum = int(recurrence.get("max_occurrences", 1) or 1)
    if occurrence_index > maximum:
        return None
    anchor = datetime.fromisoformat(str(record["scheduled_at"]))
    tz_name = str(recurrence.get("timezone") or local_timezone_name())
    zone = _zone(tz_name)
    local_anchor = anchor.astimezone(zone)
    interval = int(recurrence.get("interval", 1) or 1)
    multiplier = occurrence_index - 1
    if kind == "once":
        if occurrence_index != 1:
            return None
        target_date = local_anchor.date()
    elif kind == "daily":
        target_date = local_anchor.date() + timedelta(days=interval * multiplier)
    elif kind == "weekly":
        target_date = local_anchor.date() + timedelta(days=7 * interval * multiplier)
    else:
        raise ValueError("Unbekannte Wiederholungsregel.")
    wall = time(local_anchor.hour, local_anchor.minute, local_anchor.second)
    return resolve_local_wall_time(
        target_date,
        wall,
        tz_name,
        dst_policy=str(recurrence.get("dst_policy", DEFAULT_DST_POLICY)),
    )


def next_valid_occurrence(record: dict[str, Any], *, after_index: int) -> tuple[int, datetime, list[int]] | None:
    recurrence = record.get("recurrence") if isinstance(record.get("recurrence"), dict) else {}
    maximum = int(recurrence.get("max_occurrences", 1) or 1)
    skipped: list[int] = []
    for index in range(after_index + 1, maximum + 1):
        candidate = occurrence_at_index(record, index)
        if candidate is None:
            skipped.append(index)
            continue
        return index, candidate, skipped
    return None


def should_run_occurrence(record: dict[str, Any], *, now: datetime) -> tuple[bool, str]:
    planned = datetime.fromisoformat(str(record.get("next_run_at") or record["scheduled_at"]))
    current = now.astimezone(planned.tzinfo)
    if current <= planned + timedelta(seconds=START_GRACE_SECONDS):
        return True, "Start liegt im regulären Zeitfenster."
    recurrence = record.get("recurrence") if isinstance(record.get("recurrence"), dict) else {}
    policy = str(recurrence.get("catch_up_policy", DEFAULT_CATCH_UP_POLICY))
    if policy == "skip":
        return False, "Verspätete Ausführung wird laut Catch-up-Regel übersprungen."
    tolerance = timedelta(minutes=int(record.get("max_lateness_minutes", 180)))
    if current <= planned + tolerance:
        return True, "Verpasster Zeitpunkt wird innerhalb des Catch-up-Fensters einmal nachgeholt."
    return False, "Catch-up-Fenster ist überschritten; dieser Termin wird übersprungen."
