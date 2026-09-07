# QUALITY GATE ATTEMPT · VideoBatch Fast 2.8.3-rc24

**Status:** OFFEN · keine Stable-Freigabe

**Kanonische Quelle:** `diagnostics/release_readiness/RELEASE_EVIDENCE.json`

Dieser Bericht dokumentiert ausschließlich die noch offenen externen Qualitäts-Gates. Er erklärt keinen Lauf als bestanden, der in der kanonischen Release-Evidence nicht als `passed` nachgewiesen ist.

## Offene externe Werkzeug-Gates

- **Ruff 0.16.1:** offen – exakt gepinnter vollständiger Offline-Lauf noch nicht abgeschlossen.
- **MyPy 2.3.0:** offen – exakt gepinnter Offline-Lauf noch nicht abgeschlossen.
- **Bandit 1.9.4:** offen – exakt gepinnter Offline-Lauf noch nicht abgeschlossen.
- **pip-audit 2.10.1:** offen – exakt gepinnter Offline-Lauf noch nicht abgeschlossen.

## Abgrenzung

Die in GitHub Actions verwendete gepinnte Ruff-Prüfung für Syntax- und Undefined-Name-Fehler ist Teil des PR-Preflights. Sie ersetzt nicht den in der Release-Evidence ausdrücklich offenen vollständigen externen Ruff-Stable-Gate-Lauf.

Auch die physische KDE-X11-/Wayland-Abnahme und der reale Langzeitrender mit großer Medienauswahl bleiben laut kanonischer Evidence offen.

## Freigaberegel

Diese Datei bleibt ohne `_save_`-Suffix, bis die zugehörigen externen Qualitäts-Gates mit nachvollziehbarer Evidence abgeschlossen und die kanonische Release-Evidence entsprechend aktualisiert wurden.
