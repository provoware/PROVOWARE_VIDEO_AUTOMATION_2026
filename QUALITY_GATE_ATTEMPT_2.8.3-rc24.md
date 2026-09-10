# QUALITY GATE ATTEMPT · VideoBatch Fast 2.8.3-rc24

**Status:** TEILWEISE BESTANDEN · keine Stable-Freigabe

**Kanonische Quelle:** `diagnostics/release_readiness/RELEASE_EVIDENCE.json`

Dieser Bericht dokumentiert die externen Qualitäts-Gates des aktuellen RC24-Kandidaten. Ein Werkzeug gilt nur dann für den aktuellen Kandidaten als bestanden, wenn seine Evidence mit dem aktuellen Prüfstand nachvollziehbar verknüpft ist.

## Aktuell bestandener Werkzeug-Gate

- **Ruff 0.16.1: BESTANDEN.** Exakt gepinnter Offline-Lauf mit deaktiviertem Paketindex (`pip --no-index`) aus einem SHA-256-geprüften Wheelhouse.
- GitHub-Actions-Lauf: `34418854572`
- geprüfter Commit: `eda699f3d1159cf0a1104ec7a8c880faf6bb93bd`
- Findings: `0`
- Rückgabecode: `0`
- Wheel-SHA-256: `39897739f112253ee4fdd2e8aa9a4f9ded99fb2be367d5f31dfa4ded6025584c`

## Noch offene Werkzeug-Gates

- **MyPy 2.3.0:** offen – exakt gepinnter Offline-Nachweis für den aktuellen Kandidaten noch nicht bestätigt.
- **Bandit 1.9.4:** offen – exakt gepinnter Offline-Nachweis für den aktuellen Kandidaten noch nicht bestätigt.
- **pip-audit 2.10.1:** offen – exakt gepinnter Offline-Nachweis für den aktuellen Kandidaten noch nicht bestätigt.

## Historische Evidence

Am 5. August 2026 bestand ein älterer, exakt gepinnter Vier-Werkzeug-Lauf (`30972392104`) auf Commit `2e33a2c00a0b2e7aa44f3db38a0a60a2d6998710`. Dieser Nachweis bleibt erhalten, wird aber nicht automatisch auf den heutigen RC24-Kandidaten übertragen. Für Ruff existiert inzwischen ein neuer, direkt zum aktuellen Prüfpfad gehörender Nachweis; für MyPy, Bandit und pip-audit wird die Provenienz noch separat erneuert.

## Weitere offene Stable-Gates

Die physische KDE-X11-/Wayland-Abnahme und der reale Langzeitrender mit großer Medienauswahl auf langsamem externem Ziel bleiben offen.

## Freigaberegel

Diese Datei bleibt ohne `_save_`-Suffix, bis alle zugehörigen externen Qualitäts-Gates mit nachvollziehbarer aktueller Evidence abgeschlossen sind. Stable wird erst erklärt, wenn zusätzlich die physischen Desktop- und Langzeit-Gates bestanden sind.
