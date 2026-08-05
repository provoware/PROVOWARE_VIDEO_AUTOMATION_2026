from __future__ import annotations

import queue
import threading

import pytest

from videobatch_fast.app_events import EVENT_SCHEMA_VERSION, AppEvent, AppEventError
from videobatch_fast.event_buffer import EventBuffer


def test_legacy_adapter_copies_versions_and_protects_payload() -> None:
    original = {"operation_id": "op-17", "value": 1}
    buffer = EventBuffer(maxsize=10)
    buffer.put_legacy("job_started", original)
    original["value"] = 99
    event = buffer.get_nowait()

    assert event.schema_version == EVENT_SCHEMA_VERSION
    assert event.name == "job_started"
    assert event.operation_id == "op-17"
    assert event.sequence == 1
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


def test_buffer_accepts_only_app_events_outside_legacy_adapter() -> None:
    buffer = EventBuffer(maxsize=10)
    buffer.put(AppEvent("log", {"message": "one"}))
    buffer.put_legacy("job_started", {"operation_id": "abc"})

    first = buffer.get_nowait()
    second = buffer.get_nowait()
    assert isinstance(first, AppEvent)
    assert isinstance(second, AppEvent)
    assert (first.sequence, second.sequence) == (1, 2)
    assert second.operation_id == "abc"
    with pytest.raises(TypeError, match="put_legacy"):
        buffer.put(("log", {"message": "forbidden"}))  # type: ignore[arg-type]


def test_progress_coalescing_keeps_latest_sequence_and_terminal_event() -> None:
    buffer = EventBuffer(maxsize=10)
    for value in range(30):
        buffer.put(AppEvent("progress", {"value": value}))
    buffer.put(AppEvent("batch_finished", {"ok": True}))

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
        buffer.put_legacy("INVALID EVENT", {})
    with pytest.raises(AppEventError):
        AppEvent("log", [])  # type: ignore[arg-type]
    assert buffer.qsize() == 0


def test_concurrent_producers_receive_unique_monotonic_sequences() -> None:
    buffer = EventBuffer(maxsize=500)

    def produce(worker: int) -> None:
        for index in range(50):
            buffer.put(AppEvent("job_started", {"worker": worker, "index": index}))

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
