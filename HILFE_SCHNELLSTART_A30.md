# PROVOWARE VideoBatch Fast – Schnellstart und Hilfe (A30)

## In 30 Sekunden starten

1. Projekt vollständig entpacken.
2. Im Projektordner `./start.sh --doctor` ausführen, wenn der Rechner oder die Installation noch nicht geprüft wurde.
3. Mit `./start.sh` starten.

Der normale Start verändert keine Originalmedien. Der sichere Bootstrap prüft zuerst die Startvoraussetzungen und protokolliert Startfehler.

## Wenn VideoBatch nicht startet

1. `./start.sh --doctor` – System- und Startdiagnose.
2. `./start.sh --status` – letzten Startstatus ansehen.
3. Erst danach `./start.sh --repair`, wenn die Diagnose eine Reparatur nahelegt.

Nicht auf Verdacht Projektdateien, Logs oder Originalmedien löschen.

## Befehle

- `./start.sh` – normal starten.
- `./start.sh --help` oder `--hilfe` – kompakte Hilfe anzeigen.
- `./start.sh --doctor` oder `--diagnose` – Diagnose starten.
- `./start.sh --status` – Startstatus anzeigen.
- `./start.sh --prepare` – sichere Vorbereitung ausführen.
- `./start.sh --repair` – Reparaturfunktion starten.
- `./start.sh --test` – Tests starten.
- `./start.sh --quality` – Qualitätsprüfungen starten.
- `./start.sh --assurance` – erweiterte Prüfungen starten.

## Typische Fehlermeldung: Python 3 fehlt

`STARTEN.sh` prüft ab A30 vor dem eigentlichen Bootstrap, ob der konfigurierte Python-3-Befehl erreichbar ist. Fehlt er, beendet sich der Starter mit Rückgabecode 127 und erklärt die nächsten Schritte. Dabei wird VideoBatch nicht gestartet und es werden keine Mediendateien verändert.

## Sicherer Grundsatz

Erst prüfen, dann reparieren, dann starten: **Diagnose → Status → gezielte Reparatur → normaler Start**.
