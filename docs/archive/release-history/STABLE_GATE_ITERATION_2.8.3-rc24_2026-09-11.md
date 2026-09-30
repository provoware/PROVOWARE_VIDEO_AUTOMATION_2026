# Stable-Gate-Iteration 2.8.3-rc24 – 11. September 2026

## Ziel

Den aktuellen Qt-/Wayland-Kandidaten ausschließlich für **Kubuntu 26.04 LTS · KDE Plasma · natives Wayland** bis zur realen Stable-Abnahme führen.

## Aktueller Stand

- Entwicklungszweig: `feature/qt6-ui-phase3`
- Zieloberfläche: PySide6 / Qt 6
- GUI-Transport: natives Wayland
- X11/XWayland und Ubuntu 22.04/24.04 sind keine unterstützten Zielpfade mehr.
- Automatisierte Ubuntu-26.04-/Wayland-CI ersetzt die reale Sicht- und Startabnahme nicht.

## Offene Stable-Gates

1. **Physische Kubuntu-26.04-Plasma-Wayland-Abnahme** auf dem unveränderten finalen Kandidaten.
2. **Realer Langzeitrender** mit großer Medienauswahl auf langsamem externem Ziel.

## Abschlussregel

Stable bleibt gesperrt, bis beide Nachweise gemäß `docs/STABLE_ACCEPTANCE_EVIDENCE.md` zum exakt gleichen Kandidaten und Manifest-Hash bestanden vorliegen. Es wird kein Nachweis simuliert oder automatisch erzeugt.
