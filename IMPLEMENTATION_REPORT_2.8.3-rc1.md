# Implementierungsbericht – 2.8.3-rc1

## Ziel

Dieser Releasekandidat senkt die verbindliche maximale Funktionskomplexität auf 30, zerlegt die besonders sicherheits- und prozesskritischen Bereiche weiter, erweitert die Fehlerpfadtests und stellt eine fail-closed arbeitende Offline-Qualitätsumgebung bereit.

## Architekturänderungen

### Runner

Die FFmpeg-Prozessausführung liegt in `runner_process.py`. Start, Streamleser, Fortschrittsparser, Stall-Erkennung, Prozesszustand, Ergebnisbildung und Aufräumen sind getrennte Schritte. `runner.py` koordiniert Stapel und Jobs, besitzt aber nicht mehr die komplette Prozessüberwachung.

### Updateprüfung

`update_validation.py` trennt Paket-Hülle, ZIP-Richtlinie, Manifeststruktur, Nutzlast-Hashprüfung, Löschoperationen und Stable-Freigabebindung. Ungültige Einträge werden fail-closed abgewiesen.

### Plugin-Isolation

`sandbox_seccomp.py` kapselt Bibliothekssuche, Seccomp-Kontext, Systemaufrufauflösung, Regelinstallation und Filteraktivierung. Fehler beim Aufbau der Isolation führen nicht zu einem unisolierten Fallback.

### UI-Ereignisrouting

Das Ereignisrouting wurde aus `ui.py` in `ui_event_handlers_mixin.py` ausgelagert. Die größte Quelldatei liegt dadurch bei 584 Zeilen.

## Qualitätsgrenzen

- maximale Funktionskomplexität: 30
- gemessener Höchstwert: 28
- Mindestabdeckung: 74 Prozent
- gemessene Abdeckung: 74,43 Prozent
- maximale Quelldatei: 700 Zeilen
- gemessene größte Quelldatei: 584 Zeilen

## Offline-Qualitätsumgebung

Enthalten sind:

- exakt gesperrte Qualitätsabhängigkeiten
- Wheelhouse-Builder ausschließlich für Binär-Wheels
- SHA-256- und METADATA-Manifest
- fail-closed Verifikation
- Installation mit `--no-index`
- getrennte `.quality-venv`
- exakte Werkzeugversionsprüfung
- verpflichtendes `quality.sh`

Der Wheelhouse-Builder arbeitet über ein Staging-Verzeichnis. Ein fehlgeschlagener Download beschädigt kein bereits vorhandenes geprüftes Wheelhouse.

## Umgebungsgrenze

Das konfigurierte Paketgateway der Buildumgebung stellt Ruff, MyPy, Bandit und pip-audit nicht bereit. Daher konnten die Wheels hier nicht erzeugt und der strenge externe Lauf nicht grün abgeschlossen werden. `quality.sh` blockiert korrekt, anstatt fehlende Werkzeuge zu überspringen.

## Ergebnis

Die Komplexitäts-, Refactoring-, Fehlerpfad-, Funktions-, GUI- und visuellen Ziele sind erfüllt. Der Stand bleibt Releasekandidat, bis das Wheelhouse auf einem vernetzten passenden Linux-Buildsystem erzeugt und `./quality.sh` vollständig bestanden wurde.
