from __future__ import annotations

from pathlib import Path
import time
from tkinter import END, messagebox, ttk

from .audio_waveform import WaveformAnalysis, analyze_audio
from .jobs import build_jobs
from .probe import IMAGE_EXTENSIONS
from .slideshow import (
    SLIDESHOW_MODE_ALL_IMAGES,
    SLIDESHOW_MODE_PAIRWISE,
    TRANSITION_LABELS,
    slideshow_summary,
)
from .slideshow_editor import ThumbnailOrderStrip, WaveformSceneView
from .slideshow_sequence import (
    ORDER_ALPHABETICAL,
    ORDER_CAPTURE_DATE,
    ORDER_MANUAL,
    ORDER_RANDOM,
    apply_anchors,
    move_image,
    order_images,
    reverse_images,
)
from .text_resources import text


class UiSlideshowMixin:
    def _set_assignment_mode(self, mode: str) -> None:
        selected = mode if mode in {SLIDESHOW_MODE_PAIRWISE, SLIDESHOW_MODE_ALL_IMAGES} else SLIDESHOW_MODE_PAIRWISE
        self.assignment_mode.set(selected)
        self.config["assignment_mode"] = selected
        if selected == SLIDESHOW_MODE_ALL_IMAGES:
            self._refresh_slideshow_editors()
            self._ensure_scene_analyses()
        self._rebuild_pairs()
        self._autosave_project()

    def _set_slideshow_transition(self, preset: str) -> None:
        selected = preset if preset in TRANSITION_LABELS else "auto"
        self.slideshow_transition.set(selected)
        combo = getattr(self, "slideshow_transition_combo", None)
        display = getattr(self, "slideshow_transition_display", {})
        if combo is not None and selected in display:
            combo.set(display[selected])
        self.config["slideshow_transition"] = selected
        self._rebuild_pairs()
        self._autosave_project()

    def _build_slideshow_order_panel(self, parent) -> None:
        panel = ttk.Frame(parent, style="Card.TFrame", padding=10)
        panel.pack(fill="both", expand=True)
        ttk.Label(panel, text=text("ui.slideshow.order.title"), style="Section.TLabel").pack(anchor="w")
        ttk.Label(
            panel,
            text=text("ui.slideshow.order.help"),
            style="Hint.TLabel",
            wraplength=1100,
        ).pack(anchor="w", pady=(0, 7))

        controls = ttk.Frame(panel, style="Card.TFrame")
        controls.pack(fill="x", pady=(0, 7))
        ttk.Button(controls, text=text("ui.slideshow.order.alpha"), command=lambda: self._apply_slideshow_order(ORDER_ALPHABETICAL)).pack(side="left")
        ttk.Button(controls, text=text("ui.slideshow.order.capture"), command=lambda: self._apply_slideshow_order(ORDER_CAPTURE_DATE)).pack(side="left", padx=4)
        ttk.Button(controls, text=text("ui.slideshow.order.random"), command=lambda: self._apply_slideshow_order(ORDER_RANDOM)).pack(side="left")
        ttk.Button(controls, text=text("ui.slideshow.order.reverse"), command=self._reverse_slideshow_order).pack(side="left", padx=4)
        ttk.Separator(controls, orient="vertical").pack(side="left", fill="y", padx=7)
        ttk.Button(controls, text=text("ui.slideshow.order.start"), style="Success.TButton", command=lambda: self._set_slideshow_anchor("start")).pack(side="left")
        ttk.Button(controls, text=text("ui.slideshow.order.end"), style="Accent.TButton", command=lambda: self._set_slideshow_anchor("end")).pack(side="left", padx=4)
        ttk.Button(controls, text=text("ui.slideshow.order.clear"), command=self._clear_slideshow_anchors).pack(side="left")

        self.slideshow_order_strip = ThumbnailOrderStrip(
            panel,
            on_move=self._move_slideshow_image,
            on_select=self._slideshow_image_selected,
        )
        self.slideshow_order_strip.pack(fill="both", expand=True)
        ttk.Label(panel, textvariable=self.slideshow_order_status, style="ChoiceStatus.TLabel", wraplength=1100).pack(fill="x", pady=(7, 0))

    def _build_waveform_panel(self, parent) -> None:
        panel = ttk.Frame(parent, style="Card.TFrame", padding=10)
        panel.pack(fill="both", expand=True)
        header = ttk.Frame(panel, style="Card.TFrame")
        header.pack(fill="x", pady=(0, 7))
        ttk.Label(header, text=text("ui.slideshow.waveform.title"), style="Section.TLabel").pack(side="left")
        ttk.Checkbutton(
            header,
            text=text("ui.slideshow.waveform.sync"),
            variable=self.slideshow_scene_sync,
            command=self._set_scene_sync,
        ).pack(side="right")

        select = ttk.Frame(panel, style="Card.TFrame")
        select.pack(fill="x", pady=(0, 7))
        ttk.Label(select, text=text("ui.slideshow.waveform.audio")).pack(side="left")
        self.waveform_audio_combo = ttk.Combobox(select, state="readonly", textvariable=self.waveform_audio_display, width=54)
        self.waveform_audio_combo.pack(side="left", fill="x", expand=True, padx=7)
        self.waveform_audio_combo.bind("<<ComboboxSelected>>", lambda _event: self._waveform_audio_changed())
        ttk.Button(select, text=text("ui.slideshow.waveform.analyze"), command=lambda: self._analyze_selected_audio(refresh=True)).pack(side="left")

        self.waveform_view = WaveformSceneView(panel)
        self.waveform_view.pack(fill="both", expand=True)
        ttk.Label(panel, textvariable=self.slideshow_analysis_status, style="ChoiceStatus.TLabel", wraplength=1100).pack(fill="x", pady=(7, 0))
        ttk.Label(
            panel,
            text=text("ui.slideshow.waveform.help"),
            style="Hint.TLabel",
            wraplength=1100,
        ).pack(fill="x", pady=(4, 0))

    def _image_paths(self) -> list[Path]:
        return [path for path in self.media if path.suffix.lower() in IMAGE_EXTENSIONS]

    def _anchor_path(self, variable) -> Path | None:
        raw = str(variable.get() or "").strip()
        if not raw:
            return None
        path = Path(raw)
        return path if path in self._image_paths() else None

    def _replace_image_order(self, ordered: list[Path]) -> None:
        videos = [path for path in self.media if path.suffix.lower() not in IMAGE_EXTENSIONS]
        self.media = list(ordered) + videos
        self.media_sort.set("import")
        self._refresh_file_trees()
        self._rebuild_pairs()
        self._autosave_project()

    def _apply_slideshow_order(self, mode: str) -> None:
        images = self._image_paths()
        if not images:
            self.slideshow_order_status.set(text("ui.slideshow.status.add_images"))
            return
        if mode == ORDER_RANDOM:
            self.slideshow_random_seed.set(int(time.time_ns() & 0x7FFFFFFF))
        ordered = order_images(
            images,
            mode,
            random_seed=self.slideshow_random_seed.get(),
            start_image=self._anchor_path(self.slideshow_start_image),
            end_image=self._anchor_path(self.slideshow_end_image),
        )
        self.slideshow_order_mode.set(mode)
        self._replace_image_order(ordered)
        self.slideshow_order_status.set(text("ui.slideshow.status.reordered", count=len(ordered), mode=mode.replace("_", " ")))

    def _reverse_slideshow_order(self) -> None:
        ordered = reverse_images(
            self._image_paths(),
            start_image=self._anchor_path(self.slideshow_start_image),
            end_image=self._anchor_path(self.slideshow_end_image),
        )
        self.slideshow_order_mode.set(ORDER_MANUAL)
        self._replace_image_order(ordered)
        self.slideshow_order_status.set(text("ui.slideshow.status.reversed", count=len(ordered)))

    def _move_slideshow_image(self, source: int, target: int) -> None:
        ordered = move_image(
            self._image_paths(),
            source,
            target,
            start_image=self._anchor_path(self.slideshow_start_image),
            end_image=self._anchor_path(self.slideshow_end_image),
        )
        self.slideshow_order_mode.set(ORDER_MANUAL)
        self._replace_image_order(ordered)
        self.slideshow_order_status.set(text("ui.slideshow.status.moved", source=source + 1, target=target + 1))

    def _slideshow_image_selected(self, path: Path | None) -> None:
        self._selected_slideshow_image = path
        if path is not None:
            self.slideshow_order_status.set(text("ui.slideshow.status.selected", name=path.name))

    def _set_slideshow_anchor(self, kind: str) -> None:
        path = getattr(self, "_selected_slideshow_image", None)
        if path is None:
            messagebox.showinfo(text("ui.slideshow.order.title"), text("ui.slideshow.order.select_first"), parent=self.root)
            return
        if kind == "start":
            self.slideshow_start_image.set(str(path))
            if self.slideshow_end_image.get() == str(path):
                self.slideshow_end_image.set("")
        else:
            self.slideshow_end_image.set(str(path))
            if self.slideshow_start_image.get() == str(path):
                self.slideshow_start_image.set("")
        ordered = apply_anchors(
            self._image_paths(),
            start_image=self._anchor_path(self.slideshow_start_image),
            end_image=self._anchor_path(self.slideshow_end_image),
        )
        self._replace_image_order(ordered)
        self.slideshow_order_status.set(text("ui.slideshow.status.anchor", name=path.name, role=text("ui.slideshow.role.start" if kind == "start" else "ui.slideshow.role.end")))

    def _clear_slideshow_anchors(self) -> None:
        self.slideshow_start_image.set("")
        self.slideshow_end_image.set("")
        self._refresh_slideshow_editors()
        self._autosave_project()
        self.slideshow_order_status.set(text("ui.slideshow.status.anchors_cleared"))

    def _set_scene_sync(self) -> None:
        enabled = bool(self.slideshow_scene_sync.get())
        self.config["slideshow_scene_sync"] = enabled
        if enabled:
            self._ensure_scene_analyses()
        self._rebuild_pairs()
        self._autosave_project()

    def _audio_display_map(self) -> dict[str, Path]:
        return {f"{index + 1:02d} · {path.name}": path for index, path in enumerate(self.audios)}

    def _waveform_audio_changed(self) -> None:
        path = self._audio_display_map().get(self.waveform_audio_display.get())
        self._selected_waveform_audio = path
        if path is None:
            self.waveform_view.set_analysis(None)
            return
        analysis = self.slideshow_analyses.get(path)
        self.waveform_view.set_analysis(analysis)
        if analysis is None:
            self._analyze_selected_audio()
        else:
            self._update_waveform_status(analysis)

    def _update_waveform_status(self, analysis: WaveformAnalysis) -> None:
        labels = " · ".join(marker.label for marker in analysis.markers)
        minutes, seconds = divmod(round(analysis.duration), 60)
        self.slideshow_analysis_status.set(
            text("ui.slideshow.status.waveform", minutes=minutes, seconds=seconds, points=len(analysis.peaks), scenes=labels or text("ui.slideshow.status.no_markers"))
        )

    def _analyze_selected_audio(self, *, refresh: bool = False) -> None:
        path = getattr(self, "_selected_waveform_audio", None)
        if path is None and self.audios:
            path = self.audios[0]
            self._selected_waveform_audio = path
        if path is None:
            self.slideshow_analysis_status.set(text("ui.slideshow.status.add_audio"))
            return
        if refresh:
            self.slideshow_analysis_failed.pop(path, None)
            self.slideshow_analyses.pop(path, None)
        self._queue_waveform_analysis(path, refresh=refresh)

    def _queue_waveform_analysis(self, path: Path, *, refresh: bool = False) -> None:
        if path in self.slideshow_analyses and not refresh:
            return
        if path in self.slideshow_analysis_pending:
            return
        self.slideshow_analysis_pending.add(path)
        self.slideshow_analysis_status.set(text("ui.slideshow.status.analyzing", name=path.name))

        def worker() -> None:
            try:
                analysis = analyze_audio(path, refresh=refresh)
                self.events.put(("waveform_ready", {"path": path, "analysis": analysis}))
            except Exception as exc:
                self.events.put(("waveform_failed", {"path": path, "message": str(exc)}))

        if not self.tasks.start(f"waveform-{hash(path)}", worker):
            self.slideshow_analysis_pending.discard(path)

    def _ensure_scene_analyses(self) -> None:
        if not self.slideshow_scene_sync.get():
            return
        for path in self.audios:
            if path not in self.slideshow_analyses and path not in self.slideshow_analysis_failed:
                self._queue_waveform_analysis(path)

    def _handle_waveform_ready(self, payload: dict) -> None:
        path = Path(payload["path"])
        analysis: WaveformAnalysis = payload["analysis"]
        self.slideshow_analysis_pending.discard(path)
        self.slideshow_analysis_failed.pop(path, None)
        self.slideshow_analyses[path] = analysis
        if path == getattr(self, "_selected_waveform_audio", None):
            self.waveform_view.set_analysis(analysis)
            self._update_waveform_status(analysis)
        self._rebuild_pairs()

    def _handle_waveform_failed(self, payload: dict) -> None:
        path = Path(payload["path"])
        message = str(payload.get("message", text("ui.slideshow.status.analysis_failed")))
        self.slideshow_analysis_pending.discard(path)
        self.slideshow_analysis_failed[path] = message
        if path == getattr(self, "_selected_waveform_audio", None):
            self.waveform_view.set_analysis(None)
            self.slideshow_analysis_status.set(text("ui.slideshow.status.waveform_unavailable", message=message))
        self._rebuild_pairs()

    def _refresh_slideshow_editors(self) -> None:
        images = self._image_paths()
        start = self._anchor_path(self.slideshow_start_image)
        end = self._anchor_path(self.slideshow_end_image)
        if hasattr(self, "slideshow_order_strip"):
            self.slideshow_order_strip.set_items(images, start=start, end=end)
        start_label = start.name if start else text("ui.slideshow.status.automatic")
        end_label = end.name if end else text("ui.slideshow.status.automatic")
        self.slideshow_order_status.set(text("ui.slideshow.status.order_summary", count=len(images), start=start_label, end=end_label))

        if hasattr(self, "waveform_audio_combo"):
            mapping = self._audio_display_map()
            values = list(mapping)
            self.waveform_audio_combo.configure(values=values)
            selected = getattr(self, "_selected_waveform_audio", None)
            if selected not in self.audios:
                selected = self.audios[0] if self.audios else None
                self._selected_waveform_audio = selected
            label = next((key for key, value in mapping.items() if value == selected), "")
            self.waveform_audio_display.set(label)
            analysis = self.slideshow_analyses.get(selected) if selected else None
            self.waveform_view.set_analysis(analysis)
            if analysis is not None:
                self._update_waveform_status(analysis)
            elif selected is None:
                self.slideshow_analysis_status.set(text("ui.slideshow.status.no_audio_selected"))
        self._ensure_scene_analyses()

    def _rebuild_pairs(self) -> None:
        options = self._options()
        self._ensure_scene_analyses()
        try:
            self.jobs = build_jobs(self.audios, self.media, options, scene_analyses=self.slideshow_analyses)
        except OSError:
            self.jobs = []
        self.pair_tree.delete(*self.pair_tree.get_children())
        slideshow = options.assignment_mode == SLIDESHOW_MODE_ALL_IMAGES
        image_count = sum(1 for path in self.media if path.suffix.lower() in IMAGE_EXTENSIONS) if slideshow else 0
        if slideshow:
            ignored = max(0, len(self.media) - image_count)
            marker_count = 0
            if self.jobs and self.jobs[0].scene_markers:
                marker_count = len(self.jobs[0].scene_markers)
            if self.jobs:
                first = self.jobs[0]
                self.slideshow_summary_text.set(
                    slideshow_summary(
                        first.audio_info.duration,
                        image_count,
                        options.slideshow_transition,
                        scene_sync=options.slideshow_scene_sync and bool(first.scene_markers),
                        marker_count=marker_count,
                    )
                )
                suffix = text("ui.slideshow.status.ignored_videos", count=ignored) if ignored else ""
                pending = len(self.slideshow_analysis_pending)
                failed = len(self.slideshow_analysis_failed)
                analysis_note = text("ui.slideshow.status.pending_analyses", count=pending) if pending else ""
                fallback_note = text("ui.slideshow.status.uniform_fallbacks", count=failed) if failed else ""
                self.pair_status.set(text("ui.slideshow.status.jobs_ready", jobs=len(self.jobs), images=image_count, suffix=suffix, pending=analysis_note, fallback=fallback_note))
            elif not self.audios or not image_count:
                self.slideshow_summary_text.set(text("ui.slideshow.status.files_missing", audios=len(self.audios), images=image_count))
                self.pair_status.set(text("ui.slideshow.status.not_ready"))
            else:
                self.slideshow_summary_text.set(text("ui.slideshow.status.duration_pending"))
                self.pair_status.set(text("ui.slideshow.status.preparing"))
        elif len(self.audios) != len(self.media):
            self.pair_status.set(text("ui.slideshow.status.pair_mismatch", audios=len(self.audios), media=len(self.media)))
            self.slideshow_summary_text.set(text("ui.slideshow.status.pairwise_lines"))
        elif not self.jobs:
            self.pair_status.set(text("ui.slideshow.status.no_pairs"))
            self.slideshow_summary_text.set(text("ui.slideshow.status.pairwise_active"))
        else:
            fast = sum(job.fast_path for job in self.jobs)
            self.pair_status.set(text("ui.slideshow.status.pairs_ready", pairs=len(self.jobs), copies=fast, renders=len(self.jobs)-fast))
            self.slideshow_summary_text.set(text("ui.slideshow.status.pairwise_one"))
        for job in self.jobs:
            media_label = text("ui.slideshow.status.media_slideshow", count=len(job.media_sequence)) if job.is_slideshow else job.media.name
            mode_label = text("ui.slideshow.mode.scene") if job.is_slideshow and job.scene_markers and options.slideshow_scene_sync else (text("ui.slideshow.mode.auto") if job.is_slideshow else (text("ui.slideshow.mode.copy") if job.fast_path else text("ui.slideshow.mode.one_pass")))
            self.pair_tree.insert("", END, values=(job.index, job.audio.name, media_label, mode_label, job.reason))
        if hasattr(self, "_update_header_statistics"):
            self._update_header_statistics()
        waiting_for_analysis = bool(options.slideshow_scene_sync and self.slideshow_analysis_pending)
        self.start_button.configure(state="normal" if self.jobs and not self.runner.running and not waiting_for_analysis else "disabled")
