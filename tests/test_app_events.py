from __future__ import annotations

import queue
import threading

import pytest

from videobatch_fast.app_events import (
    EVENT_SCHEMA_VERSION,
    AppEvent,
    AppEventError,
    normalize_event,
)
from videobatch_fast.event_buffer import EventBuffer


def test_legacy_event_is_copied_versioned_and_read_only() -> None:
    original = {"operation_id": "op-17", "value": 1}
    event = normalize_event(("job_started", original), sequence=4)
    original["value"] = 99

    assert event.schema_version == EVENT_SCHEMA_VERSION
    assert event.name == "job_started"
    assert event.operation_id == "op-17"
    assert event.sequence == 4
    assert event.payload["value"] == 1
    with pytest.raises(TypeError):
        event.payload["value"] = 2  # type: ignore[index]


def test_event_keeps_legacy_unpacking_and_indexing_compatible() -> None:
    event = AppEvent.from_legacy("log", {"message": "ok"}).with_sequence(1)
    name, payload = event

    assert name == "log"
    assert payload == {"message": "ok"}
    assert event[0] == "log"
    assert event[1] == {"message": "ok"}
    assert len(event) == 2


def test_buffer_stores_only_app_events_and_sequences_them() -> None:
    buffer = EventBuffer(maxsize=10)
    buffer.put(("log", {"message": "one"}))
    buffer.put(AppEvent.from_legacy("job_started", {"operation_id": "abc"}))

    first = buffer.get_nowait()
    second = buffer.get_nowait()
    assert isinstance(first, AppEvent)
    assert isinstance(second, AppEvent)
    assert (first.sequence, second.sequence) == (1, 2)
    assert second.operation_id == "abc"


def test_progress_coalescing_keeps_latest_sequence_and_terminal_event() -> None:
    buffer = EventBuffer(maxsize=10)
    for value in range(30):
        buffer.put(("progress", {"value": value}))
    buffer.put(("batch_finished", {"ok": True}))

    progress = buffer.get_nowait()
    terminal = buffer.get_nowait()
    assert progress.name == "progress"
    assert progress.payload["value"] == 29
    assert progress.sequence == 30
    assert terminal.name == "batch_finished"
    assert terminal.is_terminal
    assert terminal.sequence == 31
    with pytest.raises(queue.Empty):
        buffer.get_nowait()


def test_invalid_event_contract_is_rejected_before_buffering() -> None:
    buffer = EventBuffer(maxsize=10)
    with pytest.raises(AppEventError):
        buffer.put(("INVALID EVENT", {}))
    with pytest.raises(AppEventError):
        normalize_event(("log", []), sequence=1)  # type: ignore[arg-type]
    assert buffer.qsize() == 0


def test_concurrent_producers_receive_unique_monotonic_sequences() -> None:
    buffer = EventBuffer(maxsize=500)

    def produce(worker: int) -> None:
        for index in range(50):
            buffer.put(("job_started", {"worker": worker, "index": index}))

    threads = [threading.Thread(target=produce, args=(worker,)) for worker in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=2.0)
        assert not thread.is_alive()

    events = [buffer.get_nowait() for _ in range(200)]
    sequences = [event.sequence for event in events]
    assert sequences == list(range(1, 201))
    assert len({(event.payload["worker"], event.payload["index"]) for event in events}) == 200
