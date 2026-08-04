# Implementierungsbericht 2.8.3-rc9

## Ziel

Wartbarkeit und reale Fehlertoleranz erhöhen, ohne den bestehenden Videoverarbeitungsweg unnötig umzubauen.

## Umsetzung

1. `safe_io.py` als zentrale dauerhafte Dateiablage eingeführt und sicherheitsrelevante Zustandsdateien darauf umgestellt.
2. Einzelinstanzsperre mit eindeutigem Blockiercode ergänzt.
3. persistentes Stapeljournal für pending, running, completed und failed ergänzt.
4. kontrollierte Wiederherstellung implementiert: nur offene Jobs, keine automatische Ausführung, alte Fehlerhistorie bleibt erhalten.
5. Recovery-Controller aus der Haupt-UI ausgelagert.
6. statische sichtbare UI-Texte in `resources/texts/de.json` überführt.
7. strengen Textvertrag für Schlüssel, Platzhalter und unerlaubte direkte UI-Literale ergänzt.
8. FFmpeg-Encoder- und Filterprüfung vor dem Rendern ergänzt.
9. Stillstands-Watchdog mit Aktivitäts-, CPU- und Ausgabewachstumskontrolle ergänzt.
10. vollständige Audio-/Videodekodierung in der tiefen Ausgabeprüfung ergänzt.
11. begrenzten Ereignispuffer und zentralen TaskManager für Hintergrundarbeiten ergänzt.
12. Branch-Coverage aktiviert und mit eigenem Mindestwert fail-closed eingebunden.

## Prüfung

- 166/166 Tests bestanden
- 11/11 gezielte RC7-Härtungstests bestanden
- 80,55 % Zeilenabdeckung
- 65,84 % Branch-Abdeckung
- 12/12 Anwendungssimulationen
- 16/16 visuelle Referenzszenarien
- GUI-Rasterprofil-Roundtrip bestanden
- Versions-, Text-, Registry-, Architektur- und interne Qualitätsprüfung bestanden
- maximale Komplexität 28/30
- größte Quelldatei 588/700 Zeilen

## Ehrliche Grenze

Der Buildhost besitzt keinen DNS-Zugriff zu PyPI. Die realen Läufe von Ruff, MyPy, Bandit und pip-audit bleiben daher offen und werden nicht als bestanden behauptet. Die reale Desktopabnahme ist ebenfalls noch offen.
