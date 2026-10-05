# Exakter Offline-Qualitätsbericht · VideoBatch Fast 2.8.3-rc24

## Ergebnis

Der aktuelle RC24-Kandidat hat die vier verpflichtenden Python-Qualitätswerkzeuge vollständig bestanden. Maßgeblicher Nachweis ist GitHub-Actions-Lauf `34421827176` auf Commit `5d7c1949e7995126b7b58ca444ae6e112ecefcea`.

| Werkzeug | Exakte Version | Ergebnis | Rückgabecode |
|---|---:|---|---:|
| Ruff | 0.16.1 | bestanden | 0 |
| MyPy | 2.3.0 | bestanden | 0 |
| Bandit | 1.9.4 | bestanden | 0 |
| pip-audit | 2.10.1 | bestanden | 0 |

## Reproduzierbarer Sicherheitsvertrag

1. Die Werkzeugversionen sind exakt gepinnt.
2. Das Wheelhouse wird vollständig erzeugt, inventarisiert und per SHA-256 manifestiert.
3. Die Qualitätsumgebung wird anschließend ausschließlich mit `--no-index`, `--find-links` und `--require-hashes` installiert.
4. Die tatsächlich installierten Versionen werden gegen die Pflichtversionen geprüft.
5. pip-audit erhält vor dem Netzwerksperrlauf einen reproduzierbaren Cachebestand.
6. Der eigentliche Werkzeuglauf verwendet `run_external_quality.py --mode required --offline`; der Netzwerkzugriff ist dabei blockiert.
7. Die Repository-Arbeitskopie wird nach dem Lauf auf unveränderten Zustand geprüft.

## Provenienz

- GitHub-Actions-Lauf: `34421827176`
- geprüfter Commit: `5d7c1949e7995126b7b58ca444ae6e112ecefcea`
- Evidence-Artefakt-ID: `10131186987`
- Evidence-Artefakt-Digest: `sha256:c11ed40a13264a7912154c6fee3e7f70108b20218a06442254ceb4fb7158e371`
- Wheelhouse-Manifest SHA-256: `e1d99b53efc8b65527a7d5b292258439c2562b5d80354d8ae342e1cae7b59844`
- aufgelöste Hash-Lockdatei SHA-256: `3fe96551379db60b501b749e66b9a807d7c6a6ba0e7000770a97e8003cb40ca1`
- pip-audit-Cache-Inventar SHA-256: `bbd31f0bae51c2dda936042d3815bed51d178339c214551332e2fc67eb5ff4d8`
- Netzwerkblocker im Werkzeuglauf: aktiv

## Bandit-Reparatur und Regression

Der erste vollständige aktuelle Lauf auf Commit `caeb6c48a7492937340ece58fc90461939dc6fe9` lieferte genau einen Bandit-Befund `B112` niedriger Schwere. Ursache war ein pauschales `except Exception: continue` beim Lesen der `text`-Option eines Tk-Widgets.

Die Korrektur verengt den erwarteten Fehlerfall auf `tkinter.TclError` und setzt bei fehlender `text`-Option einen definierten Leerwert. Es wurde weder `#nosec` verwendet noch die Bandit-Konfiguration gelockert. Der vollständige Wiederholungslauf bestand anschließend mit Rückgabecode 0.

## Historischer Nachweis

Der ältere Vier-Werkzeug-Lauf `30972392104` vom 5. August 2026 auf Commit `2e33a2c00a0b2e7aa44f3db38a0a60a2d6998710` bleibt im Repository als historische Provenienz erhalten. Für den aktuellen Kandidaten ist er nicht mehr erforderlich, weil nun ein direkt gebundener aktueller Nachweis vorliegt.

## Freigabegrenze

Die Python-Qualitätsgates sind vollständig grün. **Stable ist trotzdem noch nicht freigegeben.** Es fehlen weiterhin zwei reale Nachweise auf demselben finalen Kandidaten: die physische KDE-X11-/Wayland-Abnahme und der dokumentierte Langzeitrender mit großer Medienauswahl auf langsamem externem Ziel.
