# QUALITY GATE ATTEMPT · VideoBatch Fast 2.8.3-rc24

**Status:** PYTHON-QUALITÄTSGATES VOLLSTÄNDIG BESTANDEN · Stable weiterhin gesperrt

**Kanonische Quelle:** `diagnostics/release_readiness/RELEASE_EVIDENCE.json`

Diese technische Provenienzdatei dokumentiert die externen Python-Qualitätsgates des aktuellen RC24-Kandidaten. Sie bleibt bewusst ohne `_save_`-Suffix, weil sie den Arbeits- und Reparaturpfad festhält; der releasefertige Ergebnisbericht ist `QUALITY_GATE_REPORT_2.8.3-rc24_save_.md`.

## Aktueller provenienzgebundener Lauf

- GitHub-Actions-Lauf: `34421827176`
- geprüfter Commit: `5d7c1949e7995126b7b58ca444ae6e112ecefcea`
- Qualitätsumgebung: exakt gepinnte Wheel-Versionen, SHA-256-manifestiertes Wheelhouse, Installation mit `--no-index`, `--find-links` und `--require-hashes`
- eigentlicher Werkzeuglauf: Netzwerkzugriff durch den Offline-Guard blockiert
- Wheelhouse-Manifest SHA-256: `e1d99b53efc8b65527a7d5b292258439c2562b5d80354d8ae342e1cae7b59844`
- aufgelöste Hash-Lockdatei SHA-256: `3fe96551379db60b501b749e66b9a807d7c6a6ba0e7000770a97e8003cb40ca1`
- pip-audit-Cache-Inventar SHA-256: `bbd31f0bae51c2dda936042d3815bed51d178339c214551332e2fc67eb5ff4d8`

| Werkzeug | Version | Ergebnis | Rückgabecode |
|---|---:|---|---:|
| Ruff | 0.16.1 | BESTANDEN | 0 |
| MyPy | 2.3.0 | BESTANDEN | 0 |
| Bandit | 1.9.4 | BESTANDEN | 0 |
| pip-audit | 2.10.1 | BESTANDEN | 0 |

## Reparierter Bandit-Befund

Der erste aktuelle Voll-Lauf auf Commit `caeb6c48a7492937340ece58fc90461939dc6fe9` bestand Ruff, MyPy und pip-audit, meldete aber genau einen Bandit-Befund `B112` mit niedriger Schwere in `src/videobatch_fast/canonical_ui.py`. Dort wurde ein allgemeines `except Exception: continue` beim Lesen eines Tk-Widget-Textes still verworfen.

Die Korrektur verengt die erwartete Ausnahme auf `tkinter.TclError` und setzt bei einer nicht vorhandenen `text`-Option einen definierten Leerwert. Es wurde **kein** `#nosec`, keine Bandit-Ausnahme und keine Lockerung der Sicherheitskonfiguration verwendet. Der vollständige Wiederholungslauf `34421827176` bestand anschließend mit Bandit-Rückgabecode `0`.

## Historische Evidence

Der ältere Vier-Werkzeug-Lauf `30972392104` vom 5. August 2026 auf Commit `2e33a2c00a0b2e7aa44f3db38a0a60a2d6998710` bleibt als historische Evidence erhalten. Er wird nicht mehr benötigt, um den aktuellen Kandidaten freizugeben, weil nun ein direkt an den aktuellen RC24-Prüfstand gebundener Nachweis vorliegt.

## Verbleibende Stable-Gates

Nur zwei Stable-Gates bleiben offen:

1. physische KDE-X11-/Wayland-Abnahme auf realen Zielsystemen,
2. realer Langzeitrender mit großer Medienauswahl auf langsamem externem Ziel.

Stable wird bis zum erfolgreichen Abschluss **beider** realen Nachweise nicht erklärt.
