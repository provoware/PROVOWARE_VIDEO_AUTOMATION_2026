from __future__ import annotations

from tkinter import Listbox, ttk

from .media_library import SORT_KEYS
from .text_resources import text
from .theme import COLORS
from .ui_components import Tooltip


class UiMediaPanelsMixin:
    def _build_workflow_strip(self, parent) -> None:
        strip = ttk.Frame(parent, style="Card.TFrame", padding=6)
        strip.pack(fill="x", pady=(8, 0))
        labels = ("workflow.files", "workflow.preview", "workflow.mode", "workflow.output", "workflow.finish")
        for index, key in enumerate(labels):
            ttk.Label(strip, text=text(key), style="Hint.TLabel").grid(row=0, column=index, sticky="ew", padx=6)
            strip.columnconfigure(index, weight=1)

    def _library_card(self, parent):
        card = ttk.Frame(parent, style="Card.TFrame", padding=10)
        header = ttk.Frame(card, style="Card.TFrame")
        header.pack(fill="x", pady=(0, 5))
        ttk.Label(header, text=text('ui.media_panels.dateien'), style="Section.TLabel").pack(side="left")
        ttk.Button(header, text=text('ui.media_panels.audio_hinzufugen'), style="Accent.TButton", command=self._add_audio).pack(side="right", padx=(6, 0))
        ttk.Button(header, text=text('ui.media_panels.medien_hinzufugen'), style="Accent.TButton", command=self._add_media).pack(side="right", padx=(6, 0))
        ttk.Button(header, text=text('ui.media_panels.add_folder'), command=self._add_media_folder).pack(side="right", padx=(6, 0))
        order_button = ttk.Button(header, text=text('ui.media_panels.reihenfolge_ubernehmen'), command=self._apply_active_view_order)
        order_button.pack(side="right", padx=(4, 0))
        Tooltip(order_button, text("help.sorting"))
        notebook = ttk.Notebook(card)
        self.library_notebook = notebook
        notebook.pack(fill="both", expand=True)
        self.audio_tab = self._file_tab(notebook, True)
        self.media_tab = self._file_tab(notebook, False)
        notebook.add(self.audio_tab, text=text('ui.media_panels.audio'))
        notebook.add(self.media_tab, text=text('ui.media_panels.bilder_und_videos'))
        return card

    def _apply_active_view_order(self) -> None:
        self._apply_view_order(self.library_notebook.index(self.library_notebook.select()) == 0)

    def _file_tab(self, parent, audio: bool):
        frame = ttk.Frame(parent, style="Card.TFrame", padding=6)
        sort_row = ttk.Frame(frame, style="Card.TFrame")
        sort_row.pack(fill="x", pady=(0, 4))
        ttk.Label(sort_row, text=text('ui.media_panels.ansicht')).pack(side="left")
        variable = self.audio_sort if audio else self.media_sort
        values = list(SORT_KEYS)
        display = [SORT_KEYS[key] for key in values]
        combo = ttk.Combobox(sort_row, values=display, state="readonly", width=19)
        combo.set(SORT_KEYS.get(variable.get(), SORT_KEYS["import"]))
        mapping = dict(zip(display, values))
        combo.bind("<<ComboboxSelected>>", lambda _e, a=audio, c=combo, m=mapping: self._set_sort(a, m[c.get()]))
        combo.pack(side="left", padx=5, fill="x", expand=True)
        ttk.Button(sort_row, text=text('ui.media_panels.entfernen'), command=lambda a=audio: self._remove_selected(a)).pack(side="right")
        if audio:
            ttk.Button(sort_row, text=text('ui.media_panels.vorhoren'), command=self._play_selected_audio).pack(side="right", padx=4)
            ttk.Button(sort_row, text=text('ui.media_panels.playlist'), command=self._add_selected_to_playlist).pack(side="right")
        else:
            ttk.Button(sort_row, text=text('ui.tabs.preview'), command=self._open_preview_tab).pack(side="right", padx=4)
        ttk.Label(frame, text=text('ui.media_panels.sort_hint'), style="Hint.TLabel").pack(fill="x", pady=(0, 4))
        table = ttk.Frame(frame, style="Card.TFrame")
        table.pack(fill="both", expand=True)
        tree = ttk.Treeview(table, columns=("status", "name", "type", "size", "duration", "date"), show="headings", selectmode="extended", height=8)
        columns = (("status", "Status", 80), ("name", "Datei", 210), ("type", "Typ", 70), ("size", "Größe", 80), ("duration", "Dauer", 75), ("date", "Geändert", 115))
        for key, label, width in columns:
            tree.heading(key, text=label, command=lambda column=key, a=audio: self._sort_from_heading(a, column))
            tree.column(key, width=width, minwidth=70, stretch=key == "name")
        yscroll = ttk.Scrollbar(table, orient="vertical", command=tree.yview)
        xscroll = ttk.Scrollbar(table, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
        tree.grid(row=0, column=0, sticky="nsew")
        yscroll.grid(row=0, column=1, sticky="ns")
        xscroll.grid(row=1, column=0, sticky="ew")
        table.rowconfigure(0, weight=1)
        table.columnconfigure(0, weight=1)
        tree.bind("<<TreeviewSelect>>", lambda _e, a=audio: self._selection_changed(a))
        tree.bind("<Double-1>", lambda _e, a=audio: self._play_selected_audio() if a else self._open_preview_tab())
        if audio:
            self.audio_tree = tree
        else:
            self.media_tree = tree
        return frame

    def _preview_card(self, parent):
        card = ttk.Frame(parent, style="Card.TFrame", padding=10)
        ttk.Label(card, text=text('ui.media_panels.groe_vorschau'), style="Section.TLabel").pack(anchor="w")
        ttk.Label(card, text=text("help.preview"), style="Hint.TLabel", wraplength=620).pack(anchor="w", pady=(0, 5))
        action_row = ttk.Frame(card, style="Card.TFrame")
        action_row.pack(fill="x", pady=(0, 5))
        ttk.Button(action_row, text=text('ui.media_panels.einpassen'), command=lambda: self._set_preview_zoom(100)).pack(side="left")
        ttk.Button(action_row, text=text('ui.media_panels.vollbild'), command=self._open_preview_fullscreen).pack(side="left", padx=5)
        ttk.Label(action_row, textvariable=self.preview_meta, style="Hint.TLabel", wraplength=380).pack(side="right")
        preview = ttk.Frame(card, style="Preview.TFrame", padding=8)
        preview.pack(fill="both", expand=True)
        self.preview_label = ttk.Label(preview, textvariable=self.preview_status, anchor="center", justify="center", style="Subtitle.TLabel")
        self.preview_label.pack(fill="both", expand=True)
        controls = ttk.Frame(card, style="Card.TFrame")
        controls.pack(fill="x", pady=(5, 0))
        ttk.Label(controls, text=text('ui.media_panels.zoom')).pack(side="left")
        scale = ttk.Scale(controls, from_=25, to=800, variable=self.preview_zoom, command=self._preview_zoom_changed)
        scale.pack(side="left", fill="x", expand=True, padx=6)
        self.preview_zoom_label = ttk.Label(controls, text=f"{self.preview_zoom.get()} %")
        self.preview_zoom_label.pack(side="right")
        return card

    def _playlist_tab(self, parent):
        tab = ttk.Frame(parent, style="Card.TFrame", padding=7)
        ttk.Label(tab, text=text('ui.media_panels.vorhor_playlist'), style="Section.TLabel").pack(anchor="w")
        options = ttk.Frame(tab, style="Card.TFrame")
        options.pack(fill="x", pady=(3, 4))
        ttk.Label(options, text=text('ui.media_panels.wiederholung')).pack(side="left")
        repeat = ttk.Combobox(options, values=("Aus", "Titel", "Liste"), state="readonly", width=8)
        reverse = {"off": "Aus", "one": "Titel", "all": "Liste"}
        mapping = {value: key for key, value in reverse.items()}
        repeat.set(reverse.get(self.playlist_repeat.get(), "Aus"))
        repeat.bind("<<ComboboxSelected>>", lambda _event: self._set_playlist_repeat(mapping[repeat.get()]))
        repeat.pack(side="left", padx=4)
        ttk.Checkbutton(options, text=text('ui.media_panels.zufall'), variable=self.playlist_shuffle, command=self._sync_playlist_options).pack(side="left")
        ttk.Label(options, textvariable=self.playlist_status, style="Status.TLabel", wraplength=220).pack(side="right")
        self.playlist_box = Listbox(tab, bg=COLORS["panel"], fg=COLORS["text"], selectbackground=COLORS["selection"], relief="flat", height=5)
        self.playlist_box.pack(fill="both", expand=True)
        row = ttk.Frame(tab, style="Card.TFrame")
        row.pack(fill="x", pady=(5, 0))
        ttk.Button(row, text=text('ui.media_panels.symbol'), width=4, command=self._playlist_previous).pack(side="left")
        ttk.Button(row, text=text('ui.media_panels.symbol_2'), width=4, command=self._play_playlist).pack(side="left", padx=3)
        ttk.Button(row, text=text('ui.media_panels.pause'), command=self._pause_audio).pack(side="left")
        ttk.Button(row, text=text('ui.media_panels.symbol_3'), width=4, command=self._stop_audio).pack(side="left", padx=3)
        ttk.Button(row, text=text('ui.media_panels.symbol_4'), width=4, command=self._playlist_next).pack(side="left")
        ttk.Button(row, text=text('ui.media_panels.entfernen'), command=self._remove_playlist_selected).pack(side="right")
        return tab
