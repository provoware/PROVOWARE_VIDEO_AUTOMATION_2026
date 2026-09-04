from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OLD_BUILD = "2.8.3-rc24"
NEW_BUILD = "2.8.3-rc25"
OLD_PEP = "2.8.3rc24"
NEW_PEP = "2.8.3rc25"


def replace_once(path: str, old: str, new: str) -> None:
    target = ROOT / path
    text = target.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{path}: erwartete genau 1 Fundstelle, gefunden {count}")
    target.write_text(text.replace(old, new, 1), encoding="utf-8")


def replace_json_build(path: str) -> None:
    target = ROOT / path
    data = json.loads(target.read_text(encoding="utf-8"))

    def walk(value):
        if isinstance(value, dict):
            return {key: walk(item) for key, item in value.items()}
        if isinstance(value, list):
            return [walk(item) for item in value]
        if isinstance(value, str):
            return value.replace(OLD_BUILD, NEW_BUILD)
        return value

    target.write_text(json.dumps(walk(data), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def update_workflow_geometry() -> None:
    replace_once(
        "src/videobatch_fast/workflow_grid.py",
        """    def refresh(self) -> None:\n        try:\n            self.body.update_idletasks()\n            self._sync_width_and_rows()\n            self._sync_scroll_region()\n        except TclError:\n            pass\n\n    def scroll_to_widget(self, widget) -> None:\n""",
        """    def refresh(self) -> None:\n        \"\"\"Refresh geometry without recursively draining Tk's global idle queue.\"\"\"\n        try:\n            self._sync_width_and_rows()\n            self._sync_scroll_region()\n        except TclError:\n            pass\n\n    def scroll_to_top(self) -> None:\n        \"\"\"Return a workflow page to its deterministic first-content anchor.\"\"\"\n        try:\n            self.canvas.yview_moveto(0.0)\n        except TclError:\n            pass\n\n    def scroll_to_widget(self, widget) -> None:\n""",
    )

    replace_once(
        "src/videobatch_fast/canonical_shell_workspace.py",
        """    def _select_shell_page(self, page_index: int | None) -> None:\n        if page_index is not None:\n            self.main_notebook.select(page_index)\n            self.main_notebook.focus_set()\n\n""",
        """    def _select_shell_page(self, page_index: int | None) -> None:\n        if page_index is None:\n            return\n        self.main_notebook.select(page_index)\n        self.main_notebook.focus_set()\n        area = {1: \"media\", 2: \"preview\", 3: \"modes\", 4: \"production\"}.get(page_index)\n        grid = getattr(self, \"workflow_grids\", {}).get(area) if area else None\n        if grid is not None:\n            self.root.after_idle(grid.scroll_to_top)\n\n""",
    )


def update_kpi_geometry_feedback() -> None:
    replace_once(
        "src/videobatch_fast/canonical_shell_chrome.py",
        """            card.bind(\"<Configure>\", self._update_shell_kpi_wraplengths, add=\"+\")\n\n        row.bind(\"<Configure>\", self._layout_shell_kpis, add=\"+\")\n""",
        """\n        row.bind(\"<Configure>\", self._layout_shell_kpis, add=\"+\")\n""",
    )
    replace_once(
        "src/videobatch_fast/canonical_shell_chrome.py",
        """        self._update_shell_kpi_wraplengths()\n\n    def _update_shell_kpi_wraplengths(self, _event=None) -> None:\n        for label in getattr(self, \"_shell_kpi_detail_labels\", ()): \n            try:\n                label.configure(wraplength=max(130, label.master.winfo_width() - 26))\n            except TclError:\n                return\n""",
        """        self._update_shell_kpi_wraplengths(available_width=available, columns=columns)\n\n    def _update_shell_kpi_wraplengths(\n        self,\n        _event=None,\n        *,\n        available_width: int | None = None,\n        columns: int | None = None,\n    ) -> None:\n        row = getattr(self, \"_shell_kpi_row\", None)\n        width = int(available_width or (row.winfo_width() if row is not None else 0) or 1)\n        if columns is None:\n            columns = 4 if width >= 1040 else 2 if width >= 600 else 1\n        target = max(130, min(560, width // max(1, columns) - 52))\n        for label in getattr(self, \"_shell_kpi_detail_labels\", ()):\n            try:\n                current = int(float(label.cget(\"wraplength\") or 0))\n                if current != target:\n                    label.configure(wraplength=target)\n            except (TclError, TypeError, ValueError):\n                return\n""",
    )
    replace_once(
        "src/videobatch_fast/canonical_kpi_compact_mixin.py",
        """            card.bind(\"<Configure>\", self._compact_kpi_labels, add=\"+\")\n        self._shell_kpi_detail_labels = tracked\n        self._compact_kpi_labels()\n\n    def _compact_kpi_labels(self, _event=None) -> None:\n        for card in getattr(self, \"_shell_kpi_cards\", ()):\n            width = max(130, card.winfo_width() - 26)\n            for child in card.winfo_children():\n                if isinstance(child, ttk.Label):\n                    try:\n                        child.configure(wraplength=width)\n                    except TclError:\n                        return\n""",
        """        self._shell_kpi_detail_labels = tracked\n        self._compact_kpi_labels()\n\n    def _compact_kpi_labels(self, _event=None) -> None:\n        self._update_shell_kpi_wraplengths()\n""",
    )


def update_version_contract() -> None:
    version = ROOT / "VERSION.json"
    data = json.loads(version.read_text(encoding="utf-8"))
    if data.get("build") != OLD_BUILD or data.get("version") != OLD_BUILD:
        raise SystemExit("VERSION.json: unerwartete Ausgangsversion")
    data["build"] = NEW_BUILD
    data["version"] = NEW_BUILD
    data["purpose"] = "Deterministische Workspace-Geometrie: kein Tk-Idle-Reentry, stabile KPI-Wraps und reproduzierbarer Top-Anker für Queue/Produktion."
    version.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    replace_once("pyproject.toml", f'version = "{OLD_PEP}"', f'version = "{NEW_PEP}"')
    for relative in (
        "TOOLCHAIN_CONTRACT.json",
        "VISUAL_INSPECTION_MANIFEST.json",
        "QUALITY_ENVIRONMENT_STATUS.json",
        "DEVELOPMENT_STATUS.json",
        "STARTUP_CONTRACT.json",
        "INSTALLER_SYSTEM_CONTRACT.json",
        "registries/UI_BLUEPRINT.json",
        "registries/UI_COMPONENT_REGISTRY.json",
        "registries/VISUAL_INSPECTION_REGISTRY.json",
        "registries/PLUGIN_APPROVAL_REGISTRY.json",
        "registries/VISUAL_REGRESSION_REGISTRY.json",
        "registries/VISUAL_APPROVAL_REGISTRY.json",
    ):
        replace_json_build(relative)

    manifest = ROOT / "manifest.json"
    manifest_data = json.loads(manifest.read_text(encoding="utf-8"))
    manifest_data["version"] = NEW_BUILD
    manifest_data["build_date"] = "2026-09-04"
    manifest.write_text(json.dumps(manifest_data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def update_docs() -> None:
    changelog = ROOT / "CHANGELOG.md"
    text = changelog.read_text(encoding="utf-8")
    marker = "Alle wichtigen Änderungen dieses Projekts werden hier in zusammengefasster, chronologischer Form dokumentiert. Die vollständige frühere Detailhistorie liegt unter `docs/archive/release-history/CHANGELOG_FULL_PRE_FINALIZATION.md`.\n"
    if "## Iteration 40C · Workspace Geometry Stability" in text:
        raise SystemExit("CHANGELOG: 40C-Eintrag existiert bereits")
    entry = """
## Iteration 40C · Workspace Geometry Stability · 2026-09-04

- realen Queue-/Produktions-Screenshot mit abgeschnittenen Kartenköpfen, dominanten Scrollleisten und scheinbar leeren Tabellen als Geometrie-/Scrollproblem isoliert;
- rekursives `update_idletasks()` aus dem Workflow-Grid-Refresh entfernt, damit der Aufbau nicht die globale Tk-Idle-Queue innerhalb eines Geometriecallbacks erneut leert;
- KPI-Wraplength-Berechnung von Karten-`<Configure>`-Rückkopplungen auf eine idempotente, zeilenbreitenbasierte Berechnung umgestellt;
- normale Navigation zu Medien, Vorschau, Effekten und Queue setzt den jeweiligen Workflow reproduzierbar auf den oberen Inhaltsanker zurück; gezielte Sprünge zu Unterkarten bleiben danach weiterhin möglich;
- Regressionstest und 1858×1080-Xvfb-Smoke ergänzen Scroll-Reproduktion, Top-Anker und wiederholtes `root.update_idletasks()`;
- keine Render-, Queue-Auftrags-, Medien-, FFmpeg- oder Fehlerbehandlungslogik verändert.
"""
    if marker not in text:
        raise SystemExit("CHANGELOG-Marker fehlt")
    changelog.write_text(text.replace(marker, marker + entry, 1), encoding="utf-8")

    status_path = ROOT / "PROJEKTSTATUS.json"
    status = json.loads(status_path.read_text(encoding="utf-8"))
    status["programmversion"] = NEW_BUILD
    status["entwicklungsiteration"] = "40C"
    status["status"] = "40C Workspace Geometry Stability implementiert; Stable bleibt durch unveränderte Release-Gates blockiert"
    status.setdefault("erscheinungsbild", {})["workspace_geometry"] = "deterministic top anchor; non-reentrant idle refresh; row-driven KPI wrapping"
    status["naechster_schritt"] = "40C Vollregression und Exact-Head-Paket abschließen; danach separaten Screenshot-Harness auf CanonicalVideoBatchFastUI umstellen"
    status_path.write_text(json.dumps(status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    iteration = ROOT / "ITERATION_40C_WORKSPACE_GEOMETRY_STABILITY_2026-09-04.md"
    iteration.write_text(
        "# Iteration 40C · Workspace Geometry Stability\n\n"
        "## Ausgangsbefund\n"
        "Im realen Queue-/Produktions-Screenshot waren die oberen Workflowkarten scheinbar leer bzw. angeschnitten. "
        "Tabellenkörper und Scrollleisten dominierten, während Kartenkopf und erste Zeilen außerhalb des sichtbaren Ankers lagen.\n\n"
        "## Ursache\n"
        "`ScrollableWorkflowGrid.refresh()` rief während des Widget-Aufbaus synchron `update_idletasks()` auf. "
        "Zusammen mit dynamischen KPI-`wraplength`-Änderungen auf Karten-`<Configure>` konnte dadurch eine Geometrie-Rückkopplung entstehen. "
        "Zusätzlich blieb die vertikale Scrollposition eines Workflowtabs bei normaler Navigation erhalten.\n\n"
        "## Korrektur\n"
        "- Workflow-Refresh ohne rekursives Leeren der globalen Tk-Idle-Queue.\n"
        "- KPI-Wraps idempotent aus der stabilen Zeilenbreite statt aus rückgekoppelten Kartenbreiten.\n"
        "- Deterministischer Top-Anker bei normaler Shell-Navigation.\n"
        "- Gezielte Unterkarten-Sprünge bleiben unverändert möglich.\n\n"
        "## Nicht verändert\n"
        "Renderlogik, Queue-Aufträge, Medienverarbeitung, FFmpeg-Kommandos und Recovery-Fachlogik.\n\n"
        "## Stable-Status\n"
        "Keine Stable-Freigabe: Coverage 80/65, physische KDE-X11/Wayland-Abnahme und realer Large-Media-/Slow-Target-Soak bleiben eigenständige Gates.\n",
        encoding="utf-8",
    )


def main() -> int:
    update_workflow_geometry()
    update_kpi_geometry_feedback()
    update_version_contract()
    update_docs()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
