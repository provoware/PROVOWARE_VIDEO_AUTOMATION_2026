# Kubuntu 26.04 LTS / Plasma Wayland

## Ziel

Die aktuelle VideoBatch-Fast-Version aus `VERSION.json` bleibt mit X11 kompatibel und kann auf Kubuntu 26.04 in einer Plasma-Wayland-Sitzung betrieben werden.

## Technisches Modell

Die bestehende Oberfläche verwendet Python/Tkinter. Das in Kubuntu 26.04 verfügbare Tk 8.6 arbeitet unter Linux über X11. In einer Plasma-Wayland-Sitzung wird das Fenster deshalb über **XWayland** dargestellt. Das ist bewusst dokumentiert: Diese Erweiterung behauptet keine native Wayland-Tk-Oberfläche.

Wayland-spezifische Desktopfunktionen werden getrennt behandelt. `wl-clipboard` kann für native Zwischenablageoperationen genutzt werden; `xdg-open` und die KDE-Desktop-Portale bleiben die vorgesehenen Desktop-Schnittstellen. Es werden keine X11-Automationswerkzeuge wie `xdotool` oder `wmctrl` vorausgesetzt.

## Einmalige Vorbereitung

```bash
bash scripts/install_kubuntu_26_04_wayland.sh
```

Der Helfer installiert nur fehlende Laufzeitpakete und löscht keine Nutzerdaten.

## Prüfung

```bash
python3 scripts/kubuntu_26_04_wayland_check.py
python3 scripts/kubuntu_26_04_wayland_check.py --json
```

Für eine funktionierende Wayland-Sitzung müssen mindestens `XDG_SESSION_TYPE=wayland`, `WAYLAND_DISPLAY` und für die Tk-Oberfläche ein von XWayland bereitgestelltes `DISPLAY` vorhanden sein.

## Start

```bash
./STARTEN.sh
```

Beim Start schreibt VideoBatch zusätzlich einen maschinenlesbaren Plattformbericht nach:

`~/.local/state/VideoBatchFast/startup/platform.json`

## Fehlerbild: Wayland aktiv, aber DISPLAY fehlt

Das Programm bricht vor der Tk-Fenstererzeugung mit einer verständlichen Diagnose ab. Prüfen:

```bash
printf 'XDG_SESSION_TYPE=%s\nWAYLAND_DISPLAY=%s\nDISPLAY=%s\n' \
  "$XDG_SESSION_TYPE" "$WAYLAND_DISPLAY" "$DISPLAY"
command -v Xwayland || command -v xwayland
```

Danach `xwayland` installieren bzw. die Plasma-Sitzung neu anmelden.

## Freigabegrenze

CI kann Paketbestand, Python-Logik, simulierte Wayland-Umgebungen und reproduzierbare Builds prüfen. Die endgültige Freigabe als „Kubuntu 26.04 Wayland vollständig abgenommen“ erfordert zusätzlich einen echten Start auf einem Kubuntu-26.04-Plasma-Wayland-System mit sichtbarer UI-Ready-Meldung.
