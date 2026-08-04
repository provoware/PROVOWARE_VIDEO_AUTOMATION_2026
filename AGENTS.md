# AGENTS.md

## Produktziel

`provoware – videoautomation – 2026` ist eine robuste, laienfreundliche Linux-Anwendung für FFmpeg-Automatisierung. Datenintegrität und nachvollziehbare Fehlerbehandlung haben Vorrang vor automatischem Fortschreiten.

## Verbindliche Architekturregeln

1. Offline- oder fehlende Projektpfade niemals automatisch löschen.
2. Ausgabeziele vor Prozessstart exklusiv reservieren.
3. Dateiablagen nur transaktional, journalisiert und nach Hashprüfung abschließen.
4. Jeder Hintergrundvorgang muss genau ein terminales Abschlussereignis liefern.
5. Prozessabbrüche benötigen feste Zeitgrenzen und Eskalation.
6. Plugins nur mit Signatur, sichtbarer Berechtigung, aktiver Freigabe und echter OS-Isolierung ausführen.
7. Nicht implementierte Capabilities müssen bereits bei Manifestprüfung blockiert werden.
8. Tests dürfen manifestierte Paketdateien nicht verändern.
9. Schreibende Build-Schritte und lesende Verifikation strikt trennen.
10. Produktname, Build, Version und Kanal ausschließlich aus `VERSION.json` lesen.
11. Abhängigkeiten in Release- und Qualitätsumgebung exakt sperren.
12. Fehler immer mit Ursache, Auswirkung, automatischer Schutzmaßnahme, Lösung und Alternative ausgeben.

## Qualitätsgrenzen

- Quelldatei: maximal 700 Zeilen
- Funktionskomplexität: maximal 45
- Kern-Coverage: mindestens 74 %
- `shell=True`, `os.system` und `tempfile.mktemp`: verboten
- private Schlüssel im Release: verboten

## Prüfstrecken

```bash
./build_artifacts.sh  # bewusst schreibend
./test.sh             # paketbezogen, schreibgeschützt
./quality.sh          # Ruff, MyPy, Bandit, pip-audit zwingend
```

## Release-Gates

- Registryprüfung
- interne AST- und Komplexitätsprüfung
- Ruff
- MyPy
- pytest-cov
- Bandit
- pip-audit
- Anwendungssimulation
- isolierte visuelle Regression
- Release-Manifest vor und nach allen Tests unverändert gültig
- Frischpaketprüfung
