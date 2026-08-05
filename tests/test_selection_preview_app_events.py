from __future__ import annotations

import threading
from pathlib import Path

from videobatch_fast.app_events import AppEvent
from videobatch_fast.models import MediaInfo
from videobatch_fast.selection_preview_controller import SelectionPreviewController
from videobatch_fast.selection_preview_events import (
    SelectionPreviewFailedPayload,
    SelectionPreviewReadyPayload,
)


def _wait_for_event(done: threading.Event, controller: SelectionPreviewController) -> None:
    assert done.wait(2.0)
    assert controller.shutdown(timeout=2.0)


def test_selection_preview_ready_is_a_typed_app_event(tmp_path: Path) -> None:
    source = tmp_path / "image.png"
    source.write_bytes(b"image-data")
    preview = tmp_path / "preview.png"
    events: list[AppEvent] = []
    done = threading.Event()

    def emit(event: AppEvent) -> None:
        events.append(event)
        done.set()

    controller = SelectionPreviewController(
        emit,
        preview_builder=lambda _path, _width: preview,
        media_prober=lambda path: MediaInfo(path, "image", width=640, height=360, size_bytes=10),
    )
    token = controller.request(source, 640, include_image=True)
    _wait_for_event(done, controller)

    assert len(events) == 1
    event = events[0]
    assert event.name == "selection_preview_ready"
    assert event.operation_id == f"selection-preview-{token}"
    assert event.is_terminal
    assert isinstance(event.payload, SelectionPreviewReadyPayload)
    assert event.payload.path == source
    assert event.payload.preview == preview
    assert event.payload.size_bytes == source.stat().st_size
    assert event.payload.include_image is True


def test_selection_preview_failed_is_a_typed_app_event(tmp_path: Path) -> None:
    source = tmp_path / "broken.png"
    source.write_bytes(b"broken")
    events: list[AppEvent] = []
    done = threading.Event()

    def emit(event: AppEvent) -> None:
        events.append(event)
        done.set()

    def fail(_path: Path, _width: int) -> Path:
        raise RuntimeError("preview failed")

    controller = SelectionPreviewController(
        emit,
        preview_builder=fail,
        media_prober=lambda path: MediaInfo(path, "image"),
    )
    token = controller.request(source, 640, include_image=True)
    _wait_for_event(done, controller)

    event = events[0]
    assert event.name == "selection_preview_failed"
    assert event.operation_id == f"selection-preview-{token}"
    assert isinstance(event.payload, SelectionPreviewFailedPayload)
    assert event.payload.path == source
    assert "RuntimeError: preview failed" in event.payload.message


def test_audio_selection_does_not_build_an_image_preview(tmp_path: Path) -> None:
    source = tmp_path / "audio.wav"
    source.write_bytes(b"audio")
    events: list[AppEvent] = []
    done = threading.Event()

    def forbidden_builder(_path: Path, _width: int) -> Path:
        raise AssertionError("audio must not call preview builder")

    def emit(event: AppEvent) -> None:
        events.append(event)
        done.set()

    controller = SelectionPreviewController(
        emit,
        preview_builder=forbidden_builder,
        media_prober=lambda path: MediaInfo(path, "audio", duration=3.0, size_bytes=5),
    )
    controller.request(source, 640, include_image=False)
    _wait_for_event(done, controller)

    payload = events[0].payload
    assert isinstance(payload, SelectionPreviewReadyPayload)
    assert payload.preview is None
    assert payload.include_image is False


def test_stale_selection_preview_is_not_published(tmp_path: Path) -> None:
    first = tmp_path / "first.png"
    second = tmp_path / "second.png"
    first.write_bytes(b"first")
    second.write_bytes(b"second")
    entered = threading.Event()
    release = threading.Event()
    done = threading.Event()
    events: list[AppEvent] = []

    def builder(path: Path, _width: int) -> Path:
        if path == first:
            entered.set()
            assert release.wait(2.0)
        return tmp_path / f"{path.stem}-preview.png"

    def emit(event: AppEvent) -> None:
        events.append(event)
        done.set()

    controller = SelectionPreviewController(
        emit,
        preview_builder=builder,
        media_prober=lambda path: MediaInfo(path, "image", size_bytes=path.stat().st_size),
    )
    controller.request(first, 640, include_image=True)
    assert entered.wait(2.0)
    latest_token = controller.request(second, 640, include_image=True)
    release.set()
    _wait_for_event(done, controller)

    assert len(events) == 1
    assert events[0].payload["token"] == latest_token
    assert events[0].payload["path"] == second


def test_callback_failure_is_isolated_and_recorded(tmp_path: Path) -> None:
    source = tmp_path / "image.png"
    source.write_bytes(b"image")
    callback_called = threading.Event()

    def emit(_event: AppEvent) -> None:
        callback_called.set()
        raise RuntimeError("ui buffer failed")

    controller = SelectionPreviewController(
        emit,
        preview_builder=lambda _path, _width: tmp_path / "preview.png",
        media_prober=lambda path: MediaInfo(path, "image", size_bytes=5),
    )
    controller.request(source, 640, include_image=True)
    assert callback_called.wait(2.0)
    assert controller.shutdown(timeout=2.0)
    assert controller.callback_errors == ("RuntimeError: ui buffer failed",)
