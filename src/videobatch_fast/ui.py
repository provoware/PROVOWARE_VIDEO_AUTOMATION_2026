from __future__ import annotations

from datetime import datetime
import os
import queue
import subprocess
import time
from pathlib import Path
from tkinter import END, BooleanVar, DoubleVar, IntVar, StringVar, Tk, Toplevel, filedialog, messagebox, ttk

from .config import DEFAULT_CONFIG, load_config
from .effects import speed_summary
from .error_handling import error_definition
from .event_buffer import EventBuffer
from .event_logging import EventLogger
from .media_library import SORT_KEYS, sort_paths
from .permission_service import downloads_dir, ensure_writable_directory
from .models import BatchOptions, PairJob, ProgressSnapshot
from .paths import default_output_dir, ensure_app_dirs
from .playlist import AudioPlayer, Playlist
from .project_state import default_project_file, load_project_state, normalize_project_state, projects_dir
from .probe import AUDIO_EXTENSIONS, IMAGE_EXTENSIONS, VIDEO_EXTENSIONS, probe_media
from .quick_modes import mode_spec, quick_mode_summary
from .slideshow import (
    SLIDESHOW_MODE_ALL_IMAGES,
    SLIDESHOW_MODE_PAIRWISE,
    TRANSITION_LABELS,
)
from .runner import BatchRunner
from .task_manager import TaskManager
from .selection_preview_controller import SelectionPreviewController
from .instance_lock import focus_request_token
from .startup_handshake import signal_ui_ready
from .text_resources import text
from .theme import COLORS, apply_theme, available_themes
from .ui_components import HelpCenterDialog, SolutionDialog
from .validation import ValidationIssue, validate_pairs
from .versioning import build_label
from .ui_dashboard_project_mixin import UiDashboardProjectMixin
from .ui_layout_profiles_mixin import UiLayoutProfilesMixin
from .ui_media_panels_mixin import UiMediaPanelsMixin
from .ui_services_mixin import UiServicesMixin
from .ui_debug_footer_mixin import UiDebugFooterMixin
from .ui_event_handlers_mixin import UiEventHandlersMixin
from .ui_workspace_grid_mixin import UiWorkspaceGridMixin
from .ui_recovery_mixin import UiRecoveryMixin
from .ui_area_zoom_mixin import UiAreaZoomMixin
from .ui_access_media_mixin import UiAccessMediaMixin
from .ui_resolution_mixin import UiResolutionMixin
from .ui_slideshow_mixin import UiSlideshowMixin
from .ui_selection_preview_mixin import UiSelectionPreviewMixin

START_ACTION_LABEL = "Automatisch prüfen und Videos erstellen"
UI_CONTRACT_LABELS = ("Schnellmodi", "QuickMode.TButton", START_ACTION_LABEL)


class VideoBatchFastUI(UiResolutionMixin, UiAccessMediaMixin, UiSelectionPreviewMixin, UiSlideshowMixin, UiRecoveryMixin, UiEventHandlersMixin, UiDashboardProjectMixin, UiMediaPanelsMixin, UiWorkspaceGridMixin, UiAreaZoomMixin, UiLayoutProfilesMixin, UiDebugFooterMixin, UiServicesMixin):
    def __init__(self, root: Tk) -> None:
        ensure_app_dirs()
        self.root = root
        self.safe_mode = os.environ.get("VIDEOBATCH_SAFE_MODE", "0") == "1"
        if self.safe_mode:
            self.config = dict(DEFAULT_CONFIG)
            self.project_file = projects_dir() / "sicherer_start.vbfast.json"
            self.project_state = normalize_project_state({"project_name": "Sicherer Start"})
            project_healed = False
        else:
            self.config = load_config()
            self.project_file, self.project_state, project_healed = load_project_state(
                self.config.get("current_project_file", str(default_project_file()))
            )
        self.project_name_value = str(self.project_state.get("project_name", "Neues Projekt") or "Neues Projekt")
        self.calendar_marks = dict(self.project_state.get("calendar_marks", {}))
        self.calendar_notes = dict(self.project_state.get("calendar_notes", {}))
        self.calendar_year = int(self.project_state.get("calendar_year", datetime.now().year))
        self.calendar_month = int(self.project_state.get("calendar_month", datetime.now().month))
        self.project_dirty = False
        self._initialize_workspace_layout_store(self.project_state.get("workspace_layout_profiles", {}))
        self.events = EventBuffer(maxsize=2000)
        self.tasks = TaskManager()
        self.selection_previews = SelectionPreviewController(self.events.put_legacy)
        self.audios: list[Path] = []
        self.media: list[Path] = []
        self.audio_view: list[Path] = []
        self.media_view: list[Path] = []
        self.jobs: list[PairJob] = []
        self.tree_path_map: dict[str, Path] = {}
        self.runner = BatchRunner(self.events.put)
        self.logger = EventLogger()
        self.playlist = Playlist(repeat=str(self.config.get("playlist_repeat", "off")), shuffle=bool(self.config.get("playlist_shuffle", False)))
        self.audio_player = AudioPlayer()
        self.started_at = 0.0
        self._applying_quick_mode = False
        self.mode_buttons: dict[str, ttk.Button] = {}
        self.preview_source: Path | None = None
        self.preview_photo = None
        self.preview_request = 0
        self._preview_debounce_job: str | None = None
        self.last_results = []
        self.current_operation_id = "general"
        self.slideshow_analyses = {}
        self.slideshow_analysis_pending: set[Path] = set()
        self.slideshow_analysis_failed: dict[Path, str] = {}
        self._selected_waveform_audio: Path | None = None
        self._selected_slideshow_image: Path | None = None

        root.title(f"provoware - videoautomation - 2026 · {build_label()}")
        root.minsize(1024, 680)
        root.geometry(str(self.config.get("window_geometry", "1500x920")))
        apply_theme(root, int(self.config.get("font_scale", 105)), str(self.config.get("theme", "neon_gravity")))
        self._build_variables()
        self._initialize_area_zoom()
        self._build_ui()
        self._bind_header_statistics()
        self._apply_project_state(self.project_state)
        self._apply_quick_mode(self.quick_mode.get(), rebuild=False)
        self._update_header_statistics()
        self._refresh_runtime_status()
        self._apply_bootstrap_status()
        self.root.after(100, self._flush_events)
        self.root.after(500, self._poll_audio_player)
        self.root.after(200, self._update_clock)
        self.root.protocol("WM_DELETE_WINDOW", self._close)
        self._focus_request_token = focus_request_token()
        self.root.after(500, self._poll_focus_requests)
        self.logger.write("APP_READY", "Oberfläche aufgebaut", "provoware - videoautomation - 2026 ist bereit.", level="success", solution="Dateien hinzufügen oder ein bestehendes Projekt fortsetzen.")
        if project_healed:
            self._event("PROJECT_HEALED", "Projektdatei repariert", "Die letzte Projektdatei war beschädigt und wurde sicher durch eine Standarddatei ersetzt.", level="warning", solution="Projektinhalte kurz prüfen und weiterarbeiten.")
        self._initialize_recovery()
        if self._startup_permission_message:
            self.root.after_idle(lambda: self._event(
                "OUTPUT_PERMISSION_REPAIRED",
                text("ui.permissions.title"),
                self._startup_permission_message,
                level="warning",
                solution=text("ui.permissions.repaired"),
            ))


    def _apply_bootstrap_status(self) -> None:
        startup_status = os.environ.get("VIDEOBATCH_STARTUP_STATUS", "ready").strip().lower()
        if self.safe_mode:
            self.status_text.set(text("startup.safe_badge", "Aktiv · sicherer Startmodus"))
            self.guidance_text.set(text("startup.safe_mode", "VideoBatch wurde mit einer neutralen Projektumgebung geöffnet."))
            self._event(
                "STARTUP_SAFE_MODE",
                text("startup.safe_title", "Sicherer Startmodus aktiv"),
                text("startup.safe_mode", "VideoBatch wurde mit einer neutralen Projektumgebung geöffnet."),
                level="warning",
                solution=text("startup.safe_solution", "Die Kernfunktionen sind verfügbar. Frühere Einstellungen und Projekte bleiben unverändert erhalten."),
                detail=os.environ.get("VIDEOBATCH_BOOTSTRAP_LOG", ""),
            )
        elif startup_status in {"warning", "degraded", "blocked"}:
            self.status_text.set(text("startup.degraded_badge", "Aktiv · Start mit Einschränkung"))
            self.guidance_text.set(text("startup.degraded"))
            self._event(
                "STARTUP_DEGRADED",
                "VideoBatch wurde sicher geöffnet",
                text("startup.degraded"),
                level="warning",
                solution="Betroffene Funktionen werden erst beim konkreten Auftrag geprüft; alle übrigen Bereiche bleiben nutzbar.",
                detail=os.environ.get("VIDEOBATCH_BOOTSTRAP_LOG", ""),
            )
        else:
            self.status_text.set(text("startup.ready_badge", "Aktiv · startbereit"))
            self.guidance_text.set(text("startup.ready"))

    def _poll_focus_requests(self) -> None:
        token = focus_request_token()
        if token > self._focus_request_token:
            self._focus_request_token = token
            try:
                self.root.deiconify()
                self.root.lift()
                self.root.attributes("-topmost", True)
                self.root.after(300, lambda: self.root.attributes("-topmost", False))
                self.root.focus_force()
            except Exception:
                pass
            self._event(
                "INSTANCE_FOCUSED",
                text("startup.focus_title", "Vorhandenes Fenster aktiviert"),
                text("startup.focus_body", "VideoBatch lief bereits und wurde in den Vordergrund geholt."),
                level="success",
                solution=text("startup.focus_solution", "Im vorhandenen Fenster weiterarbeiten."),
            )
        self.root.after(500, self._poll_focus_requests)

    def _build_variables(self) -> None:
        configured_output = Path(str(self.config.get("output_dir", default_output_dir()))).expanduser()
        output_access = ensure_writable_directory(configured_output, default_output_dir())
        self.output_dir = StringVar(value=str(output_access.path))
        self._startup_permission_message = output_access.message
        self.output_mode = StringVar(value=str(self.config.get("output_mode", "Gemeinsamer Ordner")))
        self.theme_name = StringVar(value=str(self.config.get("theme", "neon_gravity")))
        self.auto_open_output = BooleanVar(value=bool(self.config.get("auto_open_output", True)))
        self.resolution = StringVar(value=str(self.config.get("resolution", "Original")))
        self.codec = StringVar(value=str(self.config.get("codec", "libx264")))
        self.profile = StringVar(value=str(self.config.get("profile", "fast")))
        self.verification = StringVar(value=str(self.config.get("verification", "Schnell")))
        self.keep_lists = BooleanVar(value=bool(self.config.get("keep_lists", True)))
        self.visual_effect = StringVar(value=str(self.config.get("visual_effect", "none")))
        self.transition = StringVar(value=str(self.config.get("transition", "none")))
        self.quick_mode = StringVar(value=str(self.config.get("quick_mode", "smart_auto")))
        self.assignment_mode = StringVar(value=str(self.config.get("assignment_mode", SLIDESHOW_MODE_PAIRWISE)))
        self.slideshow_transition = StringVar(value=str(self.config.get("slideshow_transition", "auto")))
        self.slideshow_scene_sync = BooleanVar(value=bool(self.config.get("slideshow_scene_sync", False)))
        self.slideshow_order_mode = StringVar(value=str(self.config.get("slideshow_order_mode", "manual")))
        self.slideshow_random_seed = IntVar(value=int(self.config.get("slideshow_random_seed", 0) or 0))
        self.slideshow_start_image = StringVar(value=str(self.config.get("slideshow_start_image", "") or ""))
        self.slideshow_end_image = StringVar(value=str(self.config.get("slideshow_end_image", "") or ""))
        self.slideshow_order_status = StringVar(value=text("ui.slideshow.order.empty"))
        self.waveform_audio_display = StringVar(value="")
        self.slideshow_analysis_status = StringVar(value=text("ui.slideshow.analysis.empty"))
        self.slideshow_summary_text = StringVar(value=text("ui.slideshow.summary_ready"))
        self.effect_speed_note = StringVar(value=speed_summary(self.visual_effect.get(), self.transition.get()))
        self.quick_mode_note = StringVar(value=quick_mode_summary(self.quick_mode.get()))
        self.quick_mode_detail = StringVar(value=mode_spec(self.quick_mode.get()).description)
        self.status_text = StringVar(value=text('ui.ui.startprufung_lauft'))
        self.header_selection_stats = StringVar(value=text("ui.header.selection_empty"))
        self.guidance_text = StringVar(value=text("status.ready"))
        self.pair_status = StringVar(value=text('ui.ui.fuge_gleich_viele_audios_und_bilder_oder_videos'))
        self.current_job = StringVar(value=text('ui.ui.noch_kein_auftrag_gestartet'))
        self.phase = StringVar(value=text('ui.ui.wartet'))
        self.elapsed = StringVar(value=text('ui.ui.00_00'))
        self.eta = StringVar(value=text('ui.ui.symbol'))
        self.speed = StringVar(value=text('ui.ui.symbol'))
        self.output_size = StringVar(value=text('ui.ui.0_mb'))
        self.activity = StringVar(value=text('ui.ui.symbol'))
        self.job_progress = DoubleVar(value=0.0)
        self.total_progress = DoubleVar(value=0.0)
        self.audio_sort = StringVar(value=str(self.config.get("audio_sort", "import")))
        self.media_sort = StringVar(value=str(self.config.get("media_sort", "import")))
        self.global_font_scale = IntVar(value=int(self.config.get("font_scale", 105)))
        self.last_audio_dir = StringVar(value=str(self.config.get("last_audio_dir", downloads_dir())))
        self.last_media_dir = StringVar(value=str(self.config.get("last_media_dir", downloads_dir())))
        self.preview_zoom = IntVar(value=int(self.config.get("preview_zoom", 100)))
        self.preview_status = StringVar(value=text('ui.ui.datei_anklicken_vorschau_erscheint_hier'))
        self.preview_meta = StringVar(value=text('ui.ui.noch_keine_datei_ausgewahlt'))
        self.playlist_status = StringVar(value=text("empty.playlist.body"))
        self.playlist_repeat = StringVar(value=self.playlist.repeat)
        self.playlist_shuffle = BooleanVar(value=self.playlist.shuffle)
        self.archive_used = BooleanVar(value=bool(self.config.get("archive_used", False)))
        self.archive_project_dir = StringVar(value=str(self.config.get("archive_project_dir", "")))
        self.archive_suffix = StringVar(value=str(self.config.get("archive_suffix", "__verwendet")))
        self.project_name = StringVar(value=self.project_name_value)
        self.quick_note = StringVar(value=str(self.project_state.get("quick_note", "")))
        self.datetime_text = StringVar(value="")
        self.calendar_title = StringVar(value="")

    def _global_zoom_changed(self, value: str) -> None:
        try:
            zoom = min(160, max(80, int(float(value))))
        except ValueError:
            return
        self.global_font_scale.set(zoom)
        self.config["font_scale"] = zoom
        apply_theme(self.root, zoom, self.theme_name.get())
        if hasattr(self, "_refresh_theme_widgets"):
            self._refresh_theme_widgets()
        for area in tuple(self.area_zoom):
            self._apply_area_zoom(area)

    def _set_global_zoom(self, value: int) -> None:
        self.global_font_scale.set(min(160, max(80, int(value))))
        self._global_zoom_changed(str(self.global_font_scale.get()))
        self._save_settings()

    def _set_sort(self, audio: bool, key: str) -> None:
        (self.audio_sort if audio else self.media_sort).set(key)
        self._refresh_file_trees()
        self.guidance_text.set(f"Ansicht sortiert nach {SORT_KEYS[key]}. Die Produktionsreihenfolge bleibt unverändert.")
        self._event("VIEW_SORTED", "Ansicht sortiert", f"{SORT_KEYS[key]} wurde angewendet.", solution="Bei Bedarf ausdrücklich als Produktionsreihenfolge übernehmen.")
        self._autosave_project()

    def _apply_view_order(self, audio: bool) -> None:
        view = self.audio_view if audio else self.media_view
        if not view:
            return
        changed = view != (self.audios if audio else self.media)
        if not changed:
            self.guidance_text.set("Die Ansicht entspricht bereits der Produktionsreihenfolge.")
            return
        if not messagebox.askyesno(text('ui.ui.produktionsreihenfolge_andern'), text('ui.ui.diese_aktion_verandert_die_tatsachliche_zuordnung_der_dateien')):
            return
        if audio:
            self.audios = list(view)
            self.audio_sort.set("import")
        else:
            self.media = list(view)
            self.media_sort.set("import")
        self._refresh_file_trees()
        self._refresh_slideshow_editors()
        self._rebuild_pairs()
        self._autosave_project()
        self._event("PRODUCTION_ORDER_CHANGED", "Produktionsreihenfolge übernommen", "Die sichtbare Reihenfolge wurde ausdrücklich übernommen.", level="success", solution="Zuordnungstabelle prüfen und danach Videos erstellen.")
        self._autosave_project()







    def _preview_zoom_changed(self, value: str) -> None:
        try:
            zoom = int(float(value))
        except ValueError:
            return
        self.preview_zoom.set(max(25, min(800, zoom)))
        self.preview_zoom_label.configure(text=f"{self.preview_zoom.get()} %")
        if self.preview_source:
            self.root.after(250, lambda path=self.preview_source: self._request_preview(path) if path == self.preview_source else None)

    def _set_preview_zoom(self, value: int) -> None:
        self.preview_zoom.set(value)
        self.preview_zoom_label.configure(text=f"{value} %")
        if self.preview_source:
            self._request_preview(self.preview_source)


    def _open_preview_fullscreen(self) -> None:
        if not self.preview_photo:
            self.guidance_text.set("Wähle zuerst ein Bild oder Video für die Vorschau aus.")
            return
        window = Toplevel(self.root)
        window.title(text('ui.ui.groe_vorschau_esc_schliet'))
        window.configure(bg=COLORS["preview"])
        label = ttk.Label(window, image=self.preview_photo, anchor="center")
        label.pack(fill="both", expand=True)
        window.bind("<Escape>", lambda _e: window.destroy())
        window.attributes("-fullscreen", True)






    def _append_paths(self, names, audio: bool) -> None:
        target = self.audios if audio else self.media
        allowed = AUDIO_EXTENSIONS if audio else IMAGE_EXTENSIONS | VIDEO_EXTENSIONS
        added = 0
        for name in names:
            path = Path(name)
            if path.suffix.lower() in allowed and path.is_file() and path not in target:
                target.append(path)
                added += 1
        self._refresh_file_trees()
        self._rebuild_pairs()
        self._autosave_project()
        self.guidance_text.set(f"{added} Datei(en) hinzugefügt. Klicke eine Datei für Vorschau oder Vorhören an.")
        self._event("FILES_ADDED", "Dateien hinzugefügt", f"{added} gültige Datei(en) wurden übernommen.", level="success", solution="Vorschau prüfen oder weitere Dateien hinzufügen.")
        self._autosave_project()

    def _refresh_file_trees(self) -> None:
        self.tree_path_map.clear()
        self.audio_view = sort_paths(self.audios, self.audio_sort.get()) if self.audios else []
        self.media_view = sort_paths(self.media, self.media_sort.get()) if self.media else []
        for kind, tree, paths in (("audio", self.audio_tree, self.audio_view), ("media", self.media_tree, self.media_view)):
            tree.delete(*tree.get_children())
            for index, path in enumerate(paths):
                info = probe_media(path)
                iid = f"{kind}:{index}"
                self.tree_path_map[iid] = path
                try:
                    stat = path.stat()
                    changed = time.strftime("%d.%m.%Y %H:%M", time.localtime(stat.st_mtime))
                    size = self._size(stat.st_size)
                except OSError:
                    changed, size = "nicht erreichbar", "–"
                if not path.exists():
                    status = "○ offline"
                elif not path.is_file() or info.kind == "unknown":
                    status = "✕ prüfen"
                else:
                    status = "✓ bereit"
                tree.insert("", END, iid=iid, values=(status, path.name, info.kind, size, self._duration(info.duration), changed))
        if hasattr(self, "_refresh_slideshow_editors"):
            self._refresh_slideshow_editors()
        if hasattr(self, "_update_header_statistics"):
            self._update_header_statistics()

    def _selected_paths(self, audio: bool) -> list[Path]:
        tree = self.audio_tree if audio else self.media_tree
        return [self.tree_path_map[iid] for iid in tree.selection() if iid in self.tree_path_map]

    def _remove_selected(self, audio: bool) -> None:
        selected = set(self._selected_paths(audio))
        if not selected:
            return
        if audio:
            self.audios = [path for path in self.audios if path not in selected]
        else:
            self.media = [path for path in self.media if path not in selected]
        self._refresh_file_trees()
        self._rebuild_pairs()
        self._autosave_project()

    def _add_selected_to_playlist(self) -> None:
        paths = self._selected_paths(True)
        self.playlist.add(paths)
        self._refresh_playlist()
        self.playlist_status.set(f"{len(paths)} Titel hinzugefügt · Playlist enthält {len(self.playlist.items)} Titel")
        self._autosave_project()

    def _refresh_playlist(self) -> None:
        self.playlist_box.delete(0, END)
        for index, path in enumerate(self.playlist.items):
            marker = "▶ " if index == self.playlist.current and self.audio_player.process else ""
            offline = "○ offline · " if not path.is_file() else ""
            self.playlist_box.insert(END, marker + offline + path.name)
        if 0 <= self.playlist.current < len(self.playlist.items):
            self.playlist_box.selection_set(self.playlist.current)
            self.playlist_box.see(self.playlist.current)

    def _play_selected_audio(self) -> None:
        paths = self._selected_paths(True)
        if not paths:
            self.guidance_text.set("Markiere zuerst eine Audiodatei.")
            return
        self.playlist.add(paths)
        self.playlist.current = self.playlist.items.index(paths[0])
        self._play_playlist()

    def _play_playlist(self) -> None:
        selection = self.playlist_box.curselection()
        if selection:
            self.playlist.current = int(selection[0])
        if not (0 <= self.playlist.current < len(self.playlist.items)):
            self.playlist_status.set("Die Playlist ist leer.")
            return
        path = self.playlist.items[self.playlist.current]
        if not path.is_file():
            self.playlist_status.set(f"Offline: {path.name} · Projektverweis bleibt erhalten")
            self._event("PLAYLIST_SOURCE_OFFLINE", "Audiodatei derzeit offline", str(path), level="warning", solution="Datenträger verbinden oder Datei bewusst entfernen.")
            return
        try:
            self.audio_player.play(path)
            self.playlist_status.set(f"Wiedergabe: {path.name}")
            self._refresh_playlist()
            self._event("AUDIO_PLAYBACK_STARTED", "Audio wird vorgehört", path.name, solution="Pause, Stopp oder nächsten Titel wählen.")
        except Exception as exc:
            self._show_error("PREVIEW_FAILED", str(exc))

    def _pause_audio(self) -> None:
        try:
            paused = self.audio_player.toggle_pause()
            self.playlist_status.set("Wiedergabe pausiert" if paused else "Wiedergabe fortgesetzt")
        except OSError as exc:
            self._show_error("PREVIEW_FAILED", str(exc))

    def _stop_audio(self) -> None:
        self.audio_player.stop()
        self.playlist_status.set("Wiedergabe gestoppt")
        self._refresh_playlist()

    def _playlist_previous(self) -> None:
        if not self.playlist.items:
            return
        self.playlist.current = max(0, self.playlist.current - 1)
        self._play_playlist()

    def _playlist_next(self) -> None:
        index = self.playlist.next_index()
        if index is None:
            self._stop_audio()
            return
        self.playlist.current = index
        self._play_playlist()

    def _remove_playlist_selected(self) -> None:
        self.playlist.remove([int(index) for index in self.playlist_box.curselection()])
        self._refresh_playlist()
        self._autosave_project()

    def _set_playlist_repeat(self, value: str) -> None:
        self.playlist.repeat = value
        self.playlist_repeat.set(value)
        self._sync_playlist_options()

    def _sync_playlist_options(self) -> None:
        self.playlist.shuffle = self.playlist_shuffle.get()
        self._autosave_project()

    def _poll_audio_player(self) -> None:
        process = self.audio_player.process
        if process and process.poll() is not None:
            self.audio_player.process = None
            index = self.playlist.next_index()
            if index is not None:
                self.playlist.current = index
                self._play_playlist()
            else:
                self.playlist_status.set("Playlist abgeschlossen")
                self._refresh_playlist()
        self.root.after(500, self._poll_audio_player)

    def _open_selected_external(self) -> None:
        paths = self._selected_paths(False)
        if not paths:
            return
        try:
            subprocess.Popen(["xdg-open", str(paths[0])], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except OSError as exc:
            self._show_error("PREVIEW_FAILED", str(exc))



    def _apply_quick_mode(self, key: str, *, rebuild: bool = True) -> None:
        spec = mode_spec(key)
        self._applying_quick_mode = True
        try:
            self.quick_mode.set(spec.key)
            if spec.key != "custom":
                self.visual_effect.set(spec.visual_effect)
                self.transition.set(spec.transition)
                self.profile.set(spec.profile)
                self.codec.set(spec.codec)
                self.resolution.set(spec.resolution)
                self.verification.set(spec.verification)
            self.quick_mode_note.set(quick_mode_summary(spec.key))
            self.quick_mode_detail.set(spec.description)
            self.effect_speed_note.set(speed_summary(self.visual_effect.get(), self.transition.get()))
            for mode_key, button in self.mode_buttons.items():
                button.configure(style="QuickModeSelected.TButton" if mode_key == spec.key else "QuickMode.TButton")
        finally:
            self._applying_quick_mode = False
        self.guidance_text.set(f"{spec.label} ist aktiv. {spec.description}")
        if rebuild:
            self._rebuild_pairs()
        self._autosave_project()

    def _label_entry(self, parent, title: str, variable: StringVar, browse: bool = False, project: bool = False) -> None:
        ttk.Label(parent, text=title).pack(anchor="w", pady=(7, 2))
        row = ttk.Frame(parent, style="Card.TFrame")
        row.pack(fill="x")
        ttk.Entry(row, textvariable=variable).pack(side="left", fill="x", expand=True)
        if browse:
            ttk.Button(row, text=text('ui.ui.ordner_auswahlen'), command=lambda: self._choose_directory(variable, project)).pack(side="left", padx=(6, 0))





    def _combo(self, parent, title: str, variable: StringVar, values, formatter=None) -> None:
        ttk.Label(parent, text=title).pack(anchor="w", pady=(7, 2))
        display_values = [formatter(value) for value in values] if formatter else list(values)
        combo = ttk.Combobox(parent, values=display_values, state="readonly")
        current = variable.get()
        if formatter:
            mapping = dict(zip(display_values, values))
            reverse = {value: label for label, value in mapping.items()}
            combo.set(reverse.get(current, display_values[0]))
            combo.bind("<<ComboboxSelected>>", lambda _event: variable.set(mapping[combo.get()]))
        else:
            combo.configure(textvariable=variable)
        combo.pack(fill="x")

    def _options(self) -> BatchOptions:
        return BatchOptions(
            output_dir=Path(self.output_dir.get()).expanduser(), output_mode=self.output_mode.get(), resolution=self.resolution.get(), codec=self.codec.get(), profile=self.profile.get(), verification=self.verification.get(), keep_lists=self.keep_lists.get(), visual_effect=self.visual_effect.get(), transition=self.transition.get(), quick_mode=self.quick_mode.get(), assignment_mode=self.assignment_mode.get(), slideshow_transition=self.slideshow_transition.get(), slideshow_scene_sync=self.slideshow_scene_sync.get()
        )

    def _start(self) -> None:
        if not self._prepare_start_intelligently():
            return
        self._rebuild_pairs()
        options = self._options()
        if options.slideshow_scene_sync and self.slideshow_analysis_pending:
            self.guidance_text.set("Die lokale Wellenformanalyse läuft noch. VideoBatch startet automatisch, sobald alle Audios vorbereitet sind.")
            return
        issues = validate_pairs(self.jobs, options)
        blockers = [issue for issue in issues if issue.blocking]
        if blockers:
            self._refresh_preparation_assistant()
            self._focus_preparation_assistant()
            summary = " · ".join(f"{issue.title}: {issue.message}" for issue in blockers[:5])
            self.guidance_text.set(
                f"Vorbereitung unvollständig: {len(blockers)} Punkt(e). "
                "Alle offenen Angaben stehen gesammelt im Vorbereitungsassistenten."
            )
            self._event(
                "VALIDATION_BLOCKED",
                "Vorbereitung noch nicht vollständig",
                summary,
                level="error",
                solution="Offene Punkte im Vorbereitungsassistenten nacheinander lösen.",
                detail="\n".join(f"{item.code}: {item.solution}" for item in blockers),
            )
            return
        self.started_at = time.monotonic()
        self.start_button.configure(state="disabled")
        self.cancel_button.configure(state="normal")
        self.status_text.set(text("status.running"))
        self.guidance_text.set("VideoBatch verarbeitet jetzt die Paare. Fortschritt und Aktivität werden fortlaufend angezeigt.")
        self.total_progress.set(0)
        self.job_progress.set(0)
        self._save_settings()
        try:
            self.runner.start(self.jobs, options)
        except RuntimeError as exc:
            self.start_button.configure(state="normal")
            self.cancel_button.configure(state="disabled")
            self.status_text.set("Start blockiert · Ausgabeziel nicht reservierbar")
            self._event(
                "OUTPUT_RESERVATION_FAILED",
                "Ausgabeziel konnte nicht reserviert werden",
                str(exc),
                level="error",
                solution="Ausgabeordner prüfen oder den Auftrag erneut starten.",
            )
            return
        self._event("BATCH_STARTED", "Videoerstellung gestartet", f"{len(self.jobs)} Auftrag/Aufträge werden verarbeitet.", solution="Fortschritt beobachten; nur bei Bedarf sicher abbrechen.")

    def _cancel(self) -> None:
        if self.runner.running and messagebox.askyesno(text('ui.ui.vorgang_sicher_abbrechen'), text('ui.ui.der_laufende_ffmpeg_prozess_wird_kontrolliert_beendet_originaldateien')):
            self.runner.cancel()
            self.status_text.set("Abbruch wird ausgeführt …")
            self._event("BATCH_CANCEL_REQUESTED", "Sicherer Abbruch angefordert", "Der laufende Prozess wird kontrolliert beendet.", level="warning", solution="Abschlussmeldung abwarten.")

    def _flush_events(self) -> None:
        while True:
            try:
                name, payload = self.events.get_nowait()
            except queue.Empty:
                break
            self._handle_event(name, payload)
        self.root.after(100, self._flush_events)

    def _update_progress(self, snapshot: ProgressSnapshot) -> None:
        self.job_progress.set(snapshot.job_percent)
        self.total_progress.set(snapshot.total_percent)
        self.phase.set(snapshot.phase)
        self.elapsed.set(self._clock(snapshot.elapsed_seconds))
        self.eta.set(self._clock(snapshot.eta_seconds) if snapshot.eta_seconds is not None else "–")
        self.speed.set(snapshot.speed or (f"{snapshot.fps:.1f} fps" if snapshot.fps else "aktiv"))
        self.output_size.set(self._size(snapshot.output_size))
        self.activity.set(f"vor {snapshot.last_activity_seconds:.0f}s" if snapshot.last_activity_seconds else "jetzt")



def run_app() -> None:
    root = Tk()
    try:
        root.tk.call("tk", "scaling", max(1.0, root.winfo_fpixels("1i") / 72.0))
    except Exception:
        pass
    app = VideoBatchFastUI(root)
    root.report_callback_exception = lambda exc_type, exc, tb: SolutionDialog(root, error_definition("UNKNOWN"), f"{exc_type.__name__}: {exc}")
    root.update_idletasks()
    signal_ui_ready()
    root.mainloop()
