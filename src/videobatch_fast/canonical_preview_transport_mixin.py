from __future__ import annotations

from pathlib import Path
from tkinter import TclError

from .preview_player import PreviewPlayer, PreviewPlayerError
from .probe import VIDEO_EXTENSIONS, probe_media


class CanonicalPreviewTransportMixin:
    """Bind the dashboard preview controls to one real ffplay transport."""

    def _ensure_dashboard_preview_player(self) -> PreviewPlayer:
        player = getattr(self, "_dashboard_preview_player", None)
        if player is None:
            player = PreviewPlayer()
            self._dashboard_preview_player = player
        return player

    def _set_dashboard_transport_source(self, source: Path | None) -> None:
        player = self._ensure_dashboard_preview_player()
        current = getattr(self, "_dashboard_transport_source", None)
        if current != source and player.running:
            player.stop()
        self._dashboard_transport_source = source
        duration = 0.0
        enabled = False
        if source is not None and source.suffix.lower() in VIDEO_EXTENSIONS and source.is_file():
            try:
                info = probe_media(source)
                duration = max(0.0, float(getattr(info, "duration", 0.0) or 0.0))
                enabled = player.available
            except Exception:
                enabled = False
        self._dashboard_transport_duration = duration
        scale = getattr(self, "_dashboard_seek_scale", None)
        if scale is not None:
            scale.configure(to=max(1.0, duration), state="normal" if enabled else "disabled")
            self._dashboard_seek_value.set(0.0)
        for name in ("_dashboard_play_button", "_dashboard_pause_button", "_dashboard_stop_button"):
            button = getattr(self, name, None)
            if button is not None:
                button.configure(state="normal" if enabled else "disabled")
        label = getattr(self, "_dashboard_transport_time", None)
        if label is not None:
            label.set(f"00:00 / {self._duration(duration)}" if enabled else "Kein Video ausgewählt")

    def _dashboard_transport_play(self) -> None:
        source = getattr(self, "_dashboard_transport_source", None)
        if source is None:
            return
        try:
            player = self._ensure_dashboard_preview_player()
            player.play(source, start_seconds=float(self._dashboard_seek_value.get()))
            self._dashboard_pause_button.configure(text="Pause")
            self._schedule_dashboard_transport_poll()
        except PreviewPlayerError as exc:
            self.guidance_text.set(str(exc))

    def _dashboard_transport_pause(self) -> None:
        try:
            player = self._ensure_dashboard_preview_player()
            paused = player.toggle_pause()
            self._dashboard_pause_button.configure(text="Weiter" if paused else "Pause")
        except PreviewPlayerError as exc:
            self.guidance_text.set(str(exc))

    def _dashboard_transport_stop(self) -> None:
        player = self._ensure_dashboard_preview_player()
        player.stop()
        self._dashboard_pause_button.configure(text="Pause")
        self._dashboard_seek_value.set(0.0)
        self._update_dashboard_transport_time(0.0)

    def _dashboard_transport_seek(self, _event=None) -> None:
        player = self._ensure_dashboard_preview_player()
        if not player.running:
            return
        try:
            player.seek(float(self._dashboard_seek_value.get()))
            self._dashboard_pause_button.configure(text="Pause")
            self._schedule_dashboard_transport_poll()
        except PreviewPlayerError as exc:
            self.guidance_text.set(str(exc))

    def _schedule_dashboard_transport_poll(self) -> None:
        previous = getattr(self, "_dashboard_transport_poll_id", None)
        if previous is not None:
            try:
                self.root.after_cancel(previous)
            except TclError:
                pass
        self._dashboard_transport_poll_id = self.root.after(300, self._poll_dashboard_transport)

    def _poll_dashboard_transport(self) -> None:
        self._dashboard_transport_poll_id = None
        player = self._ensure_dashboard_preview_player()
        if not player.running:
            return
        position = min(
            max(0.0, player.position_seconds),
            max(1.0, float(getattr(self, "_dashboard_transport_duration", 0.0) or 0.0)),
        )
        self._dashboard_seek_value.set(position)
        self._update_dashboard_transport_time(position)
        self._dashboard_transport_poll_id = self.root.after(300, self._poll_dashboard_transport)

    def _update_dashboard_transport_time(self, position: float) -> None:
        label = getattr(self, "_dashboard_transport_time", None)
        if label is None:
            return
        duration = float(getattr(self, "_dashboard_transport_duration", 0.0) or 0.0)
        label.set(f"{self._duration(position)} / {self._duration(duration)}")

    def _close(self) -> None:
        poll_id = getattr(self, "_dashboard_transport_poll_id", None)
        if poll_id is not None:
            try:
                self.root.after_cancel(poll_id)
            except TclError:
                pass
            self._dashboard_transport_poll_id = None
        player = getattr(self, "_dashboard_preview_player", None)
        if player is not None:
            player.stop()
        super()._close()
