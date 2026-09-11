# Kubuntu 26.04 LTS / Plasma Wayland

## Ziel

VideoBatch wird ab dieser Qt-Ausbaustufe gezielt für **Kubuntu 26.04 LTS mit KDE Plasma und Wayland** entwickelt und geprüft. X11, Ubuntu 22.04/24.04 sowie die Tk/Tkinter-Oberfläche gehören nicht mehr zum vorgesehenen Zielpfad.

## Technisches Modell

Die neue Oberfläche basiert auf **PySide6 / Qt 6** und soll unter Plasma direkt über den Qt-Wayland-Backendpfad laufen. XWayland ist für die VideoBatch-Oberfläche nicht vorgesehen und wird von der Kubuntu-26.04-Vorbereitung nicht installiert.

Desktopfunktionen werden über Wayland- und Freedesktop-Schnittstellen angebunden:

- `wl-clipboard` für die native Zwischenablage,
- `xdg-open` für Dateien und Ordner,
- `xdg-desktop-portal` und `xdg-desktop-portal-kde` für Desktop-Integration,
- Qt 6 / PySide6 für die grafische Oberfläche.

## Einmalige Systemvorbereitung

```bash
bash scripts/install_kubuntu_26_04_wayland.sh
```

Der Helfer ergänzt nur benötigte Systempakete. Er löscht keine Nutzerdaten und installiert absichtlich weder `python3-tk` noch `xwayland` als Voraussetzung für die neue Oberfläche.

## Plattformprüfung

```bash
python3 scripts/kubuntu_26_04_wayland_check.py
python3 scripts/kubuntu_26_04_wayland_check.py --json
```

Freigegeben wird nur folgende Kombination:

- Kubuntu 26.04 LTS,
- KDE Plasma,
- `XDG_SESSION_TYPE=wayland`,
- gesetztes `WAYLAND_DISPLAY`.

Ein vorhandenes `DISPLAY` ist für den nativen Qt-Wayland-Pfad nicht erforderlich.

## Qt-Teststart während der Migration

Solange der produktive Startpfad noch nicht endgültig auf Qt umgeschaltet wurde, kann die aktuelle Qt-Phase gezielt gestartet werden:

```bash
python3 -m venv .venv-qt
source .venv-qt/bin/activate
python3 -m pip install -r requirements-qt.txt
PYTHONPATH=src QT_QPA_PLATFORM=wayland python3 -m videobatch_fast.qt_phase3
```

## Plattformbericht

Die Plattformprüfung kann weiterhin einen maschinenlesbaren Bericht unter dem bestehenden Statuspfad erzeugen:

`~/.local/state/VideoBatchFast/startup/platform.json`

Der relevante Transportwert lautet nun `ui_transport: wayland-native`.

## CI-Prüfung

Die CI verwendet einen GitHub-Runner auf Ubuntu 26.04 als technische Basis, installiert die benötigten KDE-/Wayland-Komponenten und startet einen headless Weston-Compositor. Darin wird Qt ausdrücklich mit `QT_QPA_PLATFORM=wayland` ausgeführt.

Das prüft Betriebssystembasis, Abhängigkeiten und den nativen Wayland-Transport reproduzierbar. Es ersetzt **nicht** die abschließende Sichtprüfung auf einem echten Kubuntu-26.04-Plasma-Desktop.

## Freigabegrenze

Eine stabile Freigabe benötigt weiterhin einen echten Programmstart auf dem Zielrechner mit Kubuntu 26.04 Plasma Wayland sowie eine visuelle Prüfung der Oberfläche. Bis dahin bleibt der Qt-PR absichtlich im Draft-Status.
