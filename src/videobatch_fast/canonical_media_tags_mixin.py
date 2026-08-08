from __future__ import annotations

from tkinter import simpledialog

from .media_tags import add_tag, path_key, remove_tag, tags_for


class CanonicalMediaTagsMixin:
    """Persisted source tags and honest source-use filtering for the canonical dashboard."""

    def _selected_dashboard_source_paths(self) -> list:
        tree = getattr(self, "_dashboard_source_tree", None)
        mapping = getattr(self, "_dashboard_source_path_map", {})
        if tree is None:
            return []
        return [mapping[item] for item in tree.selection() if item in mapping]

    def _add_dashboard_tag(self) -> None:
        paths = self._selected_dashboard_source_paths()
        if not paths:
            self.guidance_text.set("Bitte zuerst mindestens eine Quelle auswählen.")
            return
        value = simpledialog.askstring(
            "Tag hinzufügen",
            "Tag für die ausgewählten Quellen:",
            parent=self.root,
        )
        if value is None:
            return
        if not add_tag(self.media_tags, paths, value):
            self.guidance_text.set("Tag war leer, bereits vorhanden oder das Tag-Limit ist erreicht.")
            return
        self._autosave_project(force=True, capture_layout=False)
        self._refresh_canonical_dashboard()

    def _remove_dashboard_tag(self) -> None:
        paths = self._selected_dashboard_source_paths()
        if not paths:
            self.guidance_text.set("Bitte zuerst mindestens eine Quelle auswählen.")
            return
        selected_filter = getattr(self, "_dashboard_tag_filter", None)
        default = selected_filter.get() if selected_filter and selected_filter.get() != "Alle Tags" else ""
        value = simpledialog.askstring(
            "Tag entfernen",
            "Zu entfernender Tag (leer = alle Tags der Auswahl):",
            initialvalue=default,
            parent=self.root,
        )
        if value is None:
            return
        if not remove_tag(self.media_tags, paths, value or None):
            self.guidance_text.set("Bei der Auswahl wurde kein passender Tag gefunden.")
            return
        self._autosave_project(force=True, capture_layout=False)
        self._refresh_canonical_dashboard()

    def _dashboard_used_source_keys(self) -> set[str]:
        used: set[str] = set()
        for job in getattr(self, "jobs", ()):
            audio = getattr(job, "audio", None)
            if audio:
                used.add(path_key(audio))
            for source in getattr(job, "source_media", ()):
                used.add(path_key(source))
        return used

    def _refresh_dashboard_sources(self, audios, media) -> None:
        tree = self._dashboard_source_tree
        for item in tree.get_children():
            tree.delete(item)
        self._dashboard_source_path_map = {}
        image_suffixes = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".tif", ".tiff"}
        video_suffixes = {".mp4", ".mkv", ".mov", ".avi", ".webm", ".m4v"}
        rows = [("Audio", path) for path in audios]
        for path in media:
            suffix = path.suffix.lower()
            kind = "Bild" if suffix in image_suffixes else "Video" if suffix in video_suffixes else "Medium"
            rows.append((kind, path))

        selected_filter = self._dashboard_source_filter.get() if hasattr(self, "_dashboard_source_filter") else "Alle"
        kind_filter = {"Bilder": "Bild", "Videos": "Video", "Audio": "Audio"}.get(selected_filter)
        if kind_filter:
            rows = [row for row in rows if row[0] == kind_filter]
        elif selected_filter == "Unbenutzt":
            used = self._dashboard_used_source_keys()
            rows = [row for row in rows if path_key(row[1]) not in used]

        all_tags = sorted(
            {tag for values in getattr(self, "media_tags", {}).values() for tag in values},
            key=str.casefold,
        )
        combo = getattr(self, "_dashboard_tag_filter_combo", None)
        if combo is not None:
            values = ("Alle Tags", *all_tags)
            combo.configure(values=values)
            if self._dashboard_tag_filter.get() not in values:
                self._dashboard_tag_filter.set("Alle Tags")
        tag_filter = self._dashboard_tag_filter.get() if hasattr(self, "_dashboard_tag_filter") else "Alle Tags"
        if tag_filter != "Alle Tags":
            rows = [
                row for row in rows
                if any(tag.casefold() == tag_filter.casefold() for tag in tags_for(self.media_tags, row[1]))
            ]

        for kind, path in rows[:100]:
            state = "Bereit" if path.is_file() else "Fehlt"
            tag_text = ", ".join(tags_for(self.media_tags, path)) or "–"
            item = tree.insert("", "end", values=(kind, path.name, tag_text, state))
            self._dashboard_source_path_map[item] = path
        if len(rows) > 100:
            tree.insert("", "end", values=("…", f"{len(rows) - 100} weitere", "", ""))
