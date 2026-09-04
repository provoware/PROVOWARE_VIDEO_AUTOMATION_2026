from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace_once(path: str, old: str, new: str) -> None:
    target = ROOT / path
    text = target.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{path}: erwartete genau 1 Fundstelle, gefunden {count}")
    target.write_text(text.replace(old, new, 1), encoding="utf-8")


def update_violet_pulse() -> None:
    path = ROOT / "resources/themes/toxic_candy.json"
    theme = json.loads(path.read_text(encoding="utf-8"))
    theme["name"] = "Violet Pulse"
    theme["label"] = "Violet Pulse"
    theme["colors"] = {
        "background_main": "#061426",
        "background_surface": "#0A1830",
        "background_elevated": "#171B3E",
        "background_preview": "#030A12",
        "background_toolbar": "#07172A",
        "text_primary": "#EEF0FF",
        "text_secondary": "#C5C9E8",
        "text_muted": "#979DBF",
        "border_default": "#3E4775",
        "border_subtle": "#202A4A",
        "border_focus": "#9B8CFF",
        "action_primary": "#6C52D8",
        "action_primary_text": "#FFFFFF",
        "action_secondary": "#111F3A",
        "status_success": "#72E39B",
        "status_information": "#65A4FF",
        "status_active": "#9B8CFF",
        "status_warning": "#E9AE42",
        "status_attention": "#D89345",
        "status_error": "#FF6B86",
        "state_selected": "#2C3268",
        "state_hover": "#252B5A",
        "state_disabled": "#536079",
        "tile_gold": "#C79B43",
        "tile_magenta": "#A34782",
        "tile_green": "#3F7A50",
        "tile_blue": "#2B6F99",
    }
    path.write_text(json.dumps(theme, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def update_theme_engine() -> None:
    path = "src/videobatch_fast/theme.py"
    replace_once(
        path,
        '        bordercolor=COLORS["border"],\n        lightcolor=COLORS["border_subtle"],\n        darkcolor=COLORS["border"],',
        '        bordercolor=COLORS["border_subtle"],\n        lightcolor=COLORS["border_subtle"],\n        darkcolor=COLORS["border_subtle"],',
    )
    replace_once(
        path,
        '    style.configure("QuickModeSelected.TButton", background=COLORS["accent2"], foreground=best_text_color(COLORS["accent2"]), padding=(9, 10), anchor="center", font=("DejaVu Sans", base, "bold"), borderwidth=0)\n\n    style.configure("TEntry", fieldbackground=COLORS["panel2"], foreground=field_text, insertcolor=field_text, bordercolor=COLORS["border"], padding=(8, 7))',
        '    style.configure("QuickModeSelected.TButton", background=COLORS["selection"], foreground=selected_text, padding=(9, 10), anchor="center", font=("DejaVu Sans", base, "bold"), borderwidth=1, bordercolor=COLORS["accent2"])\n    style.map("QuickModeSelected.TButton", background=[("active", COLORS["hover"]), ("focus", COLORS["selection"])], bordercolor=[("focus", COLORS["accent2"])])\n\n    style.configure("TEntry", fieldbackground=COLORS["panel2"], foreground=field_text, insertcolor=field_text, bordercolor=COLORS["border_subtle"], padding=(8, 7))',
    )
    replace_once(
        path,
        '    style.configure("TCombobox", fieldbackground=COLORS["panel2"], foreground=field_text, arrowcolor=COLORS["accent2"], bordercolor=COLORS["border"], padding=(7, 6))',
        '    style.configure("TCombobox", fieldbackground=COLORS["panel2"], foreground=field_text, arrowcolor=COLORS["accent2"], bordercolor=COLORS["border_subtle"], padding=(7, 6))',
    )
    replace_once(
        path,
        '    style.configure("TCheckbutton", background=COLORS["panel"], foreground=panel_text)\n\n    style.configure("Treeview"',
        '    style.configure("TCheckbutton", background=COLORS["panel"], foreground=panel_text)\n\n    style.configure("TSeparator", background=COLORS["border_subtle"])\n    style.configure("Treeview"',
    )
    replace_once(
        path,
        '    style.map("TNotebook.Tab", background=[("selected", COLORS["accent2"]), ("active", COLORS["hover"])], foreground=[("selected", best_text_color(COLORS["accent2"])), ("active", best_text_color(COLORS["hover"]))], bordercolor=[("selected", COLORS["accent2"]), ("active", COLORS["border"])])',
        '    style.map("TNotebook.Tab", background=[("selected", COLORS["selection"]), ("active", COLORS["hover"])], foreground=[("selected", selected_text), ("active", best_text_color(COLORS["hover"]))], bordercolor=[("selected", COLORS["accent2"]), ("active", COLORS["border_subtle"])])',
    )


def update_shell_chrome() -> None:
    path = "src/videobatch_fast/canonical_shell_chrome.py"
    replace_once(
        path,
        '        style.configure(\n            "ShellSidebar.TFrame",\n            background=COLORS["toolbar"],\n            relief="solid",\n            borderwidth=1,\n        )',
        '        style.configure(\n            "ShellSidebar.TFrame",\n            background=COLORS["toolbar"],\n            relief="solid",\n            borderwidth=1,\n            bordercolor=COLORS["border_subtle"],\n        )',
    )
    replace_once(
        path,
        '        style.configure(\n            "ShellHeader.TFrame",\n            background=COLORS["toolbar"],\n            relief="solid",\n            borderwidth=1,\n        )',
        '        style.configure(\n            "ShellHeader.TFrame",\n            background=COLORS["toolbar"],\n            relief="solid",\n            borderwidth=1,\n            bordercolor=COLORS["border_subtle"],\n        )\n        style.configure(\n            "ShellActionBar.TFrame",\n            background=COLORS["panel"],\n            relief="solid",\n            borderwidth=1,\n            bordercolor=COLORS["border_subtle"],\n        )',
    )
    replace_once(
        path,
        '        style.configure(\n            "ShellCard.TFrame",\n            background=COLORS["panel"],\n            relief="solid",\n            borderwidth=1,\n        )',
        '        style.configure(\n            "ShellCard.TFrame",\n            background=COLORS["panel"],\n            relief="solid",\n            borderwidth=1,\n            bordercolor=COLORS["border_subtle"],\n        )',
    )
    replace_once(
        path,
        '        style.configure(\n            "ShellKpiHint.TLabel",\n            background=COLORS["panel"],\n            foreground=panel_muted,\n            font=("DejaVu Sans", max(9, round(10 * factor))),\n        )',
        '        style.configure(\n            "ShellKpiHint.TLabel",\n            background=COLORS["panel"],\n            foreground=panel_muted,\n            font=("DejaVu Sans", max(9, round(10 * factor))),\n        )\n        style.configure(\n            "ShellKpiMeta.TLabel",\n            background=COLORS["panel"],\n            foreground=safe_text_color(COLORS["panel"], COLORS["text_muted"]),\n            font=("DejaVu Sans", max(8, round(9 * factor))),\n        )',
    )
    replace_once(
        path,
        '        style.configure(\n            "ShellNav.TButton",\n            background=COLORS["toolbar"],\n            foreground=toolbar_text,\n            padding=(12, nav_padding_y),\n            anchor="w",\n            relief="flat",\n            borderwidth=0,\n        )',
        '        style.configure(\n            "ShellNav.TButton",\n            background=COLORS["toolbar"],\n            foreground=toolbar_text,\n            padding=(12, nav_padding_y),\n            anchor="w",\n            relief="flat",\n            borderwidth=0,\n        )\n        style.map(\n            "ShellNav.TButton",\n            background=[("active", COLORS["hover"]), ("focus", COLORS["toolbar"])],\n            foreground=[("focus", safe_text_color(COLORS["toolbar"], COLORS["accent2"]))],\n        )',
    )
    replace_once(
        path,
        '        style.configure(\n            "ShellNavActive.TButton",\n            background=COLORS["selection"],\n            foreground=best_text_color(COLORS["selection"]),\n            padding=(12, nav_padding_y),\n            anchor="w",\n            relief="flat",\n            borderwidth=0,\n        )',
        '        style.configure(\n            "ShellNavActive.TButton",\n            background=COLORS["selection"],\n            foreground=best_text_color(COLORS["selection"]),\n            padding=(12, nav_padding_y),\n            anchor="w",\n            relief="flat",\n            borderwidth=0,\n        )\n        style.map(\n            "ShellNavActive.TButton",\n            background=[("active", COLORS["selection"]), ("focus", COLORS["selection"])],\n            foreground=[("active", best_text_color(COLORS["selection"])), ("focus", best_text_color(COLORS["selection"]))],\n        )',
    )
    replace_once(path, '        bar = ttk.Frame(parent, style="ShellHeader.TFrame", padding=(7, 5))', '        bar = ttk.Frame(parent, style="ShellActionBar.TFrame", padding=(9, 6))')
    replace_once(path, '            ("◷ Startzeituhr · Checkpoint 5", lambda: None, "Ghost.TButton", "disabled"),\n', '')
    replace_once(
        path,
        '        columns = max(1, min(len(buttons), available // max(145, requested))) if available else 1',
        '        if available >= 1380 and len(buttons) <= 6:\n            columns = len(buttons)\n        else:\n            columns = max(1, min(len(buttons), available // max(145, requested))) if available else 1',
    )
    replace_once(path, '                padx=3,\n                pady=3,', '                padx=4,\n                pady=4,')


def update_kpi_compaction() -> None:
    path = "src/videobatch_fast/canonical_kpi_detail_mixin.py"
    replace_once(
        path,
        '        self._shell_kpi_updated_vars = {key: StringVar(value="Aktualisiert: –") for key in keys}\n        for key in keys:',
        '        self._shell_kpi_updated_vars = {key: StringVar(value="Aktualisiert: –") for key in keys}\n        self._shell_kpi_meta_vars = {key: StringVar(value="Stand wird ermittelt") for key in keys}\n        for key in keys:',
    )
    replace_once(
        path,
        '            ttk.Label(\n                card,\n                textvariable=self._shell_kpi_cause_vars[key],\n                style="ShellKpiHint.TLabel",\n                wraplength=220,\n                justify="left",\n            ).pack(anchor="w", pady=(0, 4))\n            ttk.Label(\n                card,\n                textvariable=self._shell_kpi_updated_vars[key],\n                style="ShellKpiHint.TLabel",\n                wraplength=220,\n                justify="left",\n            ).pack(anchor="w", pady=(0, 5))',
        '            ttk.Label(\n                card,\n                textvariable=self._shell_kpi_meta_vars[key],\n                style="ShellKpiMeta.TLabel",\n                wraplength=240,\n                justify="left",\n            ).pack(anchor="w", pady=(0, 6))',
    )
    replace_once(
        path,
        '                self._shell_kpi_updated_vars[key].set(f"Aktualisiert: {updated}")',
        '                self._shell_kpi_updated_vars[key].set(f"Aktualisiert: {updated}")\n                if hasattr(self, "_shell_kpi_meta_vars"):\n                    if snapshot.state in {"warning", "error"}:\n                        self._shell_kpi_meta_vars[key].set(f"{cause} · {updated}")\n                    else:\n                        self._shell_kpi_meta_vars[key].set(f"Stand {updated}")',
    )


def update_contracts_and_docs() -> None:
    replace_once(
        "src/videobatch_fast/canonical_shell_workspace.py",
        '            active = item.page_index == selected_index and item.action != "disabled"',
        '            active = item.page_index == selected_index and item.action not in {"disabled", "settings"}',
    )
    replace_once(
        "scripts/checkpoint2_shell_smoke.py",
        "    assert len(app._shell_action_buttons) == 7",
        "    assert len(app._shell_action_buttons) == 6",
    )

    manifest_path = ROOT / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["build_date"] = "2026-09-04"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    changelog = ROOT / "CHANGELOG.md"
    text = changelog.read_text(encoding="utf-8")
    marker = "Alle wichtigen Änderungen dieses Projekts werden hier in zusammengefasster, chronologischer Form dokumentiert. Die vollständige frühere Detailhistorie liegt unter `docs/archive/release-history/CHANGELOG_FULL_PRE_FINALIZATION.md`.\n"
    if "## Iteration 40B · Real-Screenshot Visual Hierarchy" in text:
        raise SystemExit("CHANGELOG: 40B-Eintrag existiert unerwartet bereits")
    entry = """
## Iteration 40B · Real-Screenshot Visual Hierarchy · 2026-09-04

- realen 1858×1080-Programmzustand gegen `VIDEOBATCH_CANONICAL_UI_REFERENCE.svg` und Design-Tokens geprüft;
- erkannt, dass der Screenshot das gespeicherte Theme `toxic_candy` verwendet, obwohl es öffentlich bereits `Violet Pulse` heißt;
- Legacy-Grün/Türkis-Palette auf echte Navy/Violet-Palette mit kanonischem Grundhintergrund und klaren Kontraststufen umgestellt;
- helle Konturen aus normalen Containern, Eingabefeldern und Tabs zurückgenommen und für Fokus, Auswahl und Status reserviert;
- KPI-Metadaten visuell verdichtet, Doppelmarkierung der Navigation beseitigt und die sechs realen Hauptaktionen auf breiten Fenstern bevorzugt einzeilig angeordnet;
- keine Render-, Queue-, Medien-, FFmpeg- oder Fehlerbehandlungslogik verändert.
"""
    if marker not in text:
        raise SystemExit("CHANGELOG-Marker fehlt")
    changelog.write_text(text.replace(marker, marker + entry, 1), encoding="utf-8")

    status_path = ROOT / "PROJEKTSTATUS.json"
    status = json.loads(status_path.read_text(encoding="utf-8"))
    status["entwicklungsiteration"] = "40B"
    status["status"] = "40B Real-Screenshot Visual Hierarchy implementiert; Validierung läuft; Stable weiterhin blockiert"
    status["lineage_base_sha"] = "3f88a4411c34b6c1c6ba11576cfa669d1a2dcd02"
    appearance = status.setdefault("erscheinungsbild", {})
    appearance.update({
        "current_screenshot_theme_id": "toxic_candy",
        "current_screenshot_theme_label": "Violet Pulse",
        "violet_pulse_reference_alignment": "implementation_pending_validation",
        "visual_hierarchy": "subtle container borders; focus/status colors reserved for state; compact KPI meta line",
    })
    status["naechster_schritt"] = "40B vollständig validieren und erst danach den nächsten visuellen Evidence-Schritt bestimmen"
    status_path.write_text(json.dumps(status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    update_violet_pulse()
    update_theme_engine()
    update_shell_chrome()
    update_kpi_compaction()
    update_contracts_and_docs()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
