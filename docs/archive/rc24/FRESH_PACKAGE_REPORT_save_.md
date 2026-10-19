# Saubere Paketprüfung · VideoBatch Fast 2.8.3-rc24

## Ergebnis

Der RC24-Paket- und Releasevertrag ist auf den heutigen Zielpfad **Kubuntu 26.04 LTS · KDE Plasma · natives Wayland · PySide6/Qt 6** ausgerichtet.

- Ziel-CI: Ubuntu 26.04 mit KDE-/Wayland-Laufzeitteilmenge und nativem Qt-Wayland-QPA
- X11, XWayland sowie Ubuntu 22.04/24.04 sind keine aktuellen Stable-Zielpfade
- FFmpeg und FFprobe werden über die vorhandenen Toolchain- und Laufzeitverträge geprüft
- Release-Manifest und Paketdateiliste werden deterministisch und fail-closed verifiziert
- historische interne Nachweise liegen im ausgeschlossenen Releasearchiv
- nicht deklarierte `_save_`-Dateien im Projektstamm werden durch den Release-Dateivertrag blockiert

## Freigabestatus

Die automatisierten Repository-, Qualitäts-, Qt-/Wayland-, Manifest- und Paketverträge sind die technische Grundlage des Kandidaten. Der Langzeitrender vom 29.09.2026 ist dokumentiert bestätigt.

**Stable ist noch nicht freigegeben:** Nach den UI-/Skalierungsänderungen aus PR #228 muss der unveränderte Kandidat erneut real auf Kubuntu 26.04 / KDE Plasma / Wayland bei **100 %, 150 % und 200 %** sichtbar geprüft werden.

Die aktuellen Statusangaben werden aus `diagnostics/release_readiness/RELEASE_EVIDENCE.json` abgeleitet.
