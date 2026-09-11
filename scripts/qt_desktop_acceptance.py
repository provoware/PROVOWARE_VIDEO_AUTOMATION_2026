#!/usr/bin/env python3
from __future__ import annotations

import html
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SRC)) if str(SRC) not in sys.path else None
sys.path.insert(0, str(SCRIPTS)) if str(SCRIPTS) not in sys.path else None

from validate_acceptance_isolation import validate_environment
from videobatch_fast.platform_integration import (
    PlatformCompatibilityError,
    detect_desktop_platform,
    open_path,
    validate_gui_environment,
)

CATEGORIES = (
    ("platform", "Zielsystem"),
    ("runtime", "Qt-Laufzeit"),
    ("start", "STARTEN.sh"),
    ("layout", "Layout & Screenshots"),
    ("diagnostics", "Diagnose"),
)


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def run_dir() -> Path:
    base = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local/state")) / "VideoBatchFast" / "acceptance"
    base.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    target = base / stamp
    n = 1
    while target.exists():
        target = base / f"{stamp}_{n}"
        n += 1
    (target / "screenshots").mkdir(parents=True)
    return target


def run(command: list[str], *, env: dict[str, str] | None = None, timeout: int = 120) -> dict[str, object]:
    started = time.monotonic()
    try:
        cp = subprocess.run(
            command, cwd=ROOT, env=env, text=True, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, timeout=timeout, check=False, errors="replace",
        )
        return {"ok": cp.returncode == 0, "code": cp.returncode,
                "seconds": round(time.monotonic() - started, 2), "output": (cp.stdout or "")[-20000:]}
    except subprocess.TimeoutExpired as exc:
        value = exc.stdout or ""
        if isinstance(value, bytes):
            value = value.decode("utf-8", "replace")
        return {"ok": False, "code": 124, "seconds": round(time.monotonic() - started, 2),
                "output": "Zeitlimit überschritten.\n" + value[-18000:]}
    except OSError as exc:
        return {"ok": False, "code": 127, "seconds": round(time.monotonic() - started, 2), "output": str(exc)}


def version(name: str) -> dict[str, object]:
    path = shutil.which(name)
    if not path:
        return {"ok": False, "path": "", "value": "nicht gefunden"}
    result = run([path, "-version"], timeout=15)
    first = str(result["output"]).splitlines()
    return {"ok": bool(result["ok"]), "path": path, "value": first[0] if first else "keine Ausgabe"}


def add(report: dict, category: str, name: str, ok: bool, detail: str) -> None:
    report["checks"].append({"category": category, "name": name, "ok": bool(ok), "detail": detail})


def status(report: dict, category: str) -> str:
    values = [item["ok"] for item in report["checks"] if item["category"] == category]
    return "green" if values and all(values) else ("red" if values else "yellow")


def overall(report: dict) -> str:
    if "red" in report["automated"].values():
        return "red"
    return "green" if report["manual_approval"]["approved"] else "yellow"


def icon(value: str) -> str:
    return {"green": "🟢", "yellow": "🟡", "red": "🔴"}.get(value, "⚪")


def write_reports(report: dict, folder: Path) -> None:
    report["overall"] = overall(report)
    report["generated_at"] = now()
    tmp = folder / "acceptance.json.tmp"
    tmp.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(folder / "acceptance.json")

    lines = [
        "PROVOWARE VIDEOBATCH 2026 · KUBUNTU 26.04 QT-ABNAHME",
        "=" * 64,
        f"Gesamtstatus: {icon(report['overall'])} {report['overall'].upper()}",
        "",
    ]
    for key, label in CATEGORIES:
        value = report["automated"].get(key, "yellow")
        lines.append(f"{icon(value)} {label}: {value.upper()}")
    manual = report["manual_approval"]
    lines += [
        f"{'🟢' if manual['approved'] else '🟡'} Manuelle Sichtprüfung: {'BESTANDEN' if manual['approved'] else 'OFFEN'}",
        "", "PRÜFPUNKTE",
        *[f"{'✓' if item['ok'] else '✕'} {item['name']}: {item['detail']}" for item in report["checks"]],
        "", f"Prüfer: {manual.get('reviewer') or '—'}",
        f"Freigabezeit: {manual.get('approved_at') or '—'}",
        "",
        ("FREIGEGEBEN: Die separate, reversible Qt-Startpfad-Umschaltung darf vorbereitet werden."
         if report["overall"] == "green" else "NICHT FREIGEGEBEN: Der kanonische Startpfad bleibt unverändert."),
    ]
    (folder / "ABNAHME.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")

    rows = "".join(
        f"<tr><td>{icon(report['automated'].get(k,'yellow'))}</td><td>{html.escape(label)}</td>"
        f"<td>{html.escape(report['automated'].get(k,'yellow').upper())}</td></tr>"
        for k, label in CATEGORIES
    )
    rows += (
        f"<tr><td>{'🟢' if manual['approved'] else '🟡'}</td><td>Manuelle Sichtprüfung</td>"
        f"<td>{'BESTANDEN' if manual['approved'] else 'OFFEN'}</td></tr>"
    )
    checks = "".join(
        f"<tr><td>{'✓' if c['ok'] else '✕'}</td><td>{html.escape(c['name'])}</td>"
        f"<td>{html.escape(c['detail'])}</td></tr>" for c in report["checks"]
    )
    shots = "".join(
        f'<li><a href="screenshots/{html.escape(Path(x).name)}">{html.escape(Path(x).name)}</a></li>'
        for x in report["screenshots"]
    )
    page = f"""<!doctype html><html lang="de"><meta charset="utf-8">
<title>VideoBatch Qt-Abnahme</title><style>
body{{font:16px system-ui;background:#eef1f4;color:#17202a;margin:0;padding:24px}}
main{{max-width:1050px;margin:auto;background:#fff;padding:24px;border-radius:14px}}
table{{width:100%;border-collapse:collapse}}td{{padding:9px;border-bottom:1px solid #ddd;vertical-align:top}}
.box{{padding:14px;border:1px solid #ccd3da;border-radius:10px;font-size:1.2rem;font-weight:700}}
</style><main><h1>VideoBatch 2026 · echte Kubuntu-26.04-Qt-Abnahme</h1>
<p class="box">{icon(report['overall'])} Gesamtstatus: {report['overall'].upper()}</p>
<h2>Ampel</h2><table>{rows}</table><h2>Prüfpunkte</h2><table>{checks}</table>
<h2>Screenshots</h2><ul>{shots or '<li>keine</li>'}</ul>
<p>Prüfer: <b>{html.escape(manual.get('reviewer') or '—')}</b></p>
<p><a href="acceptance.json">acceptance.json</a> · <a href="ABNAHME.txt">ABNAHME.txt</a></p>
</main></html>"""
    (folder / "AMPEL.html").write_text(page, encoding="utf-8")


def acceptance_environment_status(
    environ: dict[str, str] | None = None,
) -> tuple[bool, str]:
    env = os.environ if environ is None else environ
    raw = str(env.get("VIDEOBATCH_ACCEPTANCE_TEST_HOME", "")).strip()
    if not raw:
        return False, (
            "VIDEOBATCH_ACCEPTANCE_TEST_HOME fehlt. "
            "Die interne Qt-Abnahme darf nur über KUBUNTU_26_04_QT_ABNAHME.sh gestartet werden."
        )
    test_home = Path(raw).expanduser().resolve(strict=False)
    errors = validate_environment(test_home, env)
    if errors:
        return False, "Abnahme-Isolation ungültig: " + " | ".join(errors)
    return True, f"isolierte Test-Heimat bestätigt: {test_home}"


def real_start(folder: Path) -> dict[str, object]:
    state = folder / "startpfad-state"
    config = folder / "startpfad-config"
    state.mkdir()
    config.mkdir()
    env = {**os.environ, "XDG_STATE_HOME": str(state), "XDG_CONFIG_HOME": str(config),
           "VIDEOBATCH_TEST_AUTO_CLOSE_MS": "1200", "VIDEOBATCH_DEBUG": "1", "PYTHONPATH": str(SRC)}
    result = run([str(ROOT / "STARTEN.sh"), "--check-only"], env=env, timeout=90)
    out = str(result["output"])
    result.update(ui_ready="BOOTSTRAP_READY pid=" in out, normal="mode=normal" in out,
                  clean="Die Anwendung wurde regulär beendet." in out)
    result["ok"] = bool(result["ok"] and result["ui_ready"] and result["normal"] and result["clean"])
    (folder / "startpfad.log").write_text(out + "\n", encoding="utf-8")
    return result


def geometry(widget, window) -> tuple[bool, str]:
    from PySide6.QtCore import QPoint
    if not widget.isVisible():
        return False, "nicht sichtbar"
    p = widget.mapTo(window, QPoint(0, 0))
    r = widget.rect()
    right, bottom = p.x() + r.width(), p.y() + r.height()
    ok = r.width() >= 8 and r.height() >= 8 and p.x() >= -4 and p.y() >= -4 \
        and right <= window.width() + 4 and bottom <= window.height() + 4
    return ok, f"{r.width()}x{r.height()} · Position {p.x()},{p.y()}"


def acceptance_dialog(report: dict, folder: Path, window, automated_green: bool) -> None:
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout

    dialog = QDialog(window)
    dialog.setWindowTitle("VideoBatch · Qt-Abnahme")
    dialog.setModal(False)
    dialog.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
    layout = QVBoxLayout(dialog)
    title = QLabel("Echte Kubuntu-26.04-Sichtprüfung")
    title.setStyleSheet("font-size:18px;font-weight:700")
    layout.addWidget(title)
    layout.addWidget(QLabel("\n".join(
        f"{icon(report['automated'].get(k,'yellow'))} {label}: {report['automated'].get(k,'yellow').upper()}"
        for k, label in CATEGORIES
    )))
    note = QLabel("Prüfe die weiterhin bedienbare VideoBatch-Oberfläche auf Lesbarkeit, abgeschnittene Elemente, "
                  "stabile Anordnung, Navigation und sinnvolle Größen. Grün wird nie automatisch gesetzt.")
    note.setWordWrap(True)
    layout.addWidget(note)
    reviewer = QLineEdit(os.environ.get("USER", ""))
    reviewer.setPlaceholderText("Prüfername")
    layout.addWidget(reviewer)

    open_row = QHBoxLayout()
    report_button = QPushButton("Ampelbericht öffnen")
    folder_button = QPushButton("Prüfordner öffnen")
    report_button.clicked.connect(lambda: open_path(folder / "AMPEL.html", detect_desktop_platform()))
    folder_button.clicked.connect(lambda: open_path(folder, detect_desktop_platform()))
    open_row.addWidget(report_button); open_row.addWidget(folder_button); layout.addLayout(open_row)

    row = QHBoxLayout()
    later = QPushButton("Noch nicht freigeben")
    approve = QPushButton("✓ Sichtprüfung bestanden")
    approve.setEnabled(automated_green)
    row.addWidget(later); row.addStretch(); row.addWidget(approve); layout.addLayout(row)

    decided = {"value": False}

    def decide(ok: bool) -> None:
        name = reviewer.text().strip()
        if ok and not name:
            reviewer.setStyleSheet("border:2px solid #c0392b"); reviewer.setFocus(); return
        decided["value"] = True
        report["manual_approval"] = {"approved": ok, "reviewer": name if ok else "", "approved_at": now() if ok else ""}
        write_reports(report, folder)
        dialog.accept()

    later.clicked.connect(lambda: decide(False))
    approve.clicked.connect(lambda: decide(True))

    def closed(_result: int) -> None:
        if not decided["value"]:
            report["manual_approval"] = {"approved": False, "reviewer": "", "approved_at": ""}
            write_reports(report, folder)
        open_path(folder / "AMPEL.html", detect_desktop_platform())
        window.close()

    dialog.finished.connect(closed)
    dialog.resize(640, 360)
    dialog.show(); dialog.raise_(); dialog.activateWindow()
    window._acceptance_dialog = dialog


def main() -> int:
    isolated, isolation_detail = acceptance_environment_status()
    if not isolated:
        print(f"🔴 Qt-Abnahme blockiert: {isolation_detail}")
        return 4

    folder = run_dir()
    report = {
        "schema_version": 1,
        "target": "Kubuntu 26.04 LTS · KDE Plasma · natives Wayland · PySide6/Qt 6",
        "generated_at": now(), "run_directory": str(folder), "checks": [], "screenshots": [],
        "manual_approval": {"approved": False, "reviewer": "", "approved_at": ""}, "automated": {},
    }

    platform = detect_desktop_platform()
    try:
        validate_gui_environment(platform)
        platform_ok, detail = True, f"{platform.distro_name} · {platform.current_desktop or platform.desktop_session} · {platform.session_type}"
    except PlatformCompatibilityError as exc:
        platform_ok, detail = False, str(exc)
    report["platform"] = platform.to_dict()
    add(report, "platform", "Isolierte Test-Heimat", True, isolation_detail)
    add(report, "platform", "Kubuntu 26.04 + KDE Plasma + Wayland", platform_ok, detail)
    if not platform_ok:
        report["automated"] = {"platform": "red", "runtime": "yellow", "start": "yellow", "layout": "yellow", "diagnostics": "yellow"}
        write_reports(report, folder)
        print(f"🔴 Abnahme blockiert: {detail}\nBericht: {folder / 'AMPEL.html'}")
        return 2

    ffmpeg, ffprobe = version("ffmpeg"), version("ffprobe")
    report["diagnostics"] = {"python": sys.version, "executable": sys.executable, "ffmpeg": ffmpeg, "ffprobe": ffprobe}
    add(report, "diagnostics", "FFmpeg verfügbar", bool(ffmpeg["ok"]), str(ffmpeg["value"]))
    add(report, "diagnostics", "FFprobe verfügbar", bool(ffprobe["ok"]), str(ffprobe["value"]))

    gate = run([sys.executable, str(ROOT / "scripts/toolchain.py"), "gate", "--scope", "runtime", "--quiet"])
    add(report, "runtime", "Verifizierte Runtime", bool(gate["ok"]),
        "TOOLCHAIN_GATE_PASSED=runtime" if gate["ok"] else str(gate["output"])[-800:])

    start = real_start(folder)
    report["start_chain"] = start
    add(report, "start", "Echter STARTEN.sh-Pfad bis UI_READY", bool(start["ok"]),
        f"UI_READY={start['ui_ready']} · normal={start['normal']} · Clean={start['clean']} · {start['seconds']} s")

    from PySide6 import QtCore
    from PySide6.QtWidgets import QApplication
    from videobatch_fast.qt_phase3 import VideoBatchQtPhase3Window
    from videobatch_fast.qt_theme import APP_STYLE

    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("PROVOWARE VideoBatch 2026 · Abnahme")
    app.setStyle("Fusion"); app.setStyleSheet(APP_STYLE)
    backend = app.platformName().lower()
    report["qt"] = {"version": QtCore.qVersion(), "backend": backend}
    add(report, "runtime", "Qt verwendet natives Wayland", backend.startswith("wayland"), backend)
    add(report, "runtime", "Tkinter nicht geladen", "tkinter" not in sys.modules,
        "nicht geladen" if "tkinter" not in sys.modules else "unerwartet geladen")

    screen = app.primaryScreen()
    available = screen.availableGeometry() if screen else None
    screen_ok = bool(available and available.width() >= 1024 and available.height() >= 700)
    add(report, "layout", "Nutzbare Bildschirmfläche", screen_ok,
        f"{available.width()}x{available.height()} · DPR {screen.devicePixelRatio():.2f}" if available and screen else "kein Bildschirm")

    window = VideoBatchQtPhase3Window(autoload_project=False)
    if available:
        window.resize(max(1024, min(1440, available.width())), max(700, min(900, available.height())))
    window.show(); app.processEvents(); time.sleep(.15); app.processEvents()
    add(report, "layout", "Qt-Hauptfenster sichtbar", window.isVisible(), f"{window.width()}x{window.height()}")
    add(report, "layout", "Fenstertitel Qt + Wayland",
        "Qt 6" in window.windowTitle() and "Wayland" in window.windowTitle(), window.windowTitle())

    for label, widget in (("Statusanzeige", window.status), ("Start-Schaltfläche", window.start),
                          ("Auftragstabelle", window.table), ("Workspace-Navigation", window.workspace_navigation)):
        ok, detail = geometry(widget, window); add(report, "layout", label, ok, detail)

    for route in ("dashboard", "media", "preview", "project", "diagnostics"):
        window._route_workspace(route); app.processEvents(); time.sleep(.12); app.processEvents()
        target = folder / "screenshots" / f"{route}.png"
        saved = window.grab().save(str(target), "PNG")
        ok = bool(saved and target.is_file() and target.stat().st_size > 8000)
        add(report, "layout", f"Screenshot {route}", ok, f"{target.name} · {target.stat().st_size if target.exists() else 0} Bytes")
        if ok: report["screenshots"].append(str(target))

    window._route_workspace("project"); app.processEvents()
    ok, detail = geometry(window.project_panel, window); add(report, "layout", "Projektbereich sichtbar", ok, detail)
    window._route_workspace("diagnostics"); app.processEvents()
    ok, detail = geometry(window.diagnostics_panel, window); add(report, "layout", "Diagnosebereich sichtbar", ok, detail)

    report["automated"] = {key: status(report, key) for key, _label in CATEGORIES}
    write_reports(report, folder)
    automated_green = all(v == "green" for v in report["automated"].values())
    acceptance_dialog(report, folder, window, automated_green)

    print(f"{'🟢' if automated_green else '🔴'} Automatische Qt-Abnahme {'bestanden' if automated_green else 'blockiert'}.")
    print(f"Prüfordner: {folder}")
    app.exec()

    final = json.loads((folder / "acceptance.json").read_text(encoding="utf-8"))
    if final["overall"] == "green":
        print("🟢 KUBUNTU-26.04-QT-ABNAHME VOLLSTÄNDIG BESTANDEN"); return 0
    if "red" in final["automated"].values():
        print("🔴 KUBUNTU-26.04-QT-ABNAHME BLOCKIERT"); return 1
    print("🟡 TECHNISCH BESTANDEN · SICHTFREIGABE OFFEN"); return 3


if __name__ == "__main__":
    raise SystemExit(main())
