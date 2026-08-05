# Implementierungsbericht 2.8.1-rc1

## Auftrag

Rasterzustände getrennt nach Auflösung und UI-Zoom projektbezogen speichern. Ungültige oder veraltete Zustände automatisch auf geprüfte Standardverhältnisse zurücksetzen.

## Umsetzung

- neues Modul `layout_profiles.py`
- neues UI-Modul `ui_layout_profiles_mixin.py`
- neue Registry `WORKSPACE_LAYOUT_REGISTRY.json`
- Projektschema auf Version 3 erweitert
- vier Splitter als normalisierte Verhältnisse gespeichert
- Profile nach Anwendungsauflösung und UI-Zoom getrennt
- maximal 16 aktuelle Profile pro Projekt
- veraltete Vertragsversionen automatisch ersetzt
- kollabierte oder nicht endliche Werte abgefangen
- Speichern nach Splitterbewegung entprellt
- Wiederherstellung erst nach sichtbarer Arbeitsbereich-Geometrie
- reales GUI-Neustart- und Roundtrip-Szenario ergänzt

## Fehler, die während der Umsetzung gefunden wurden

1. Unsichtbare Notebook-Seiten meldeten vor dem ersten Anzeigen teilweise Breite `1`. Die Wiederherstellung erfolgt deshalb erst beim sichtbaren Arbeitsbereich und setzt vertikale Splitter vor horizontalen Splittern.
2. Die erste Mindesthöhenregel war für kompakte 1280×720-Fenster zu streng. Die Grenzen wurden gegen die vorhandenen visuellen Referenzen korrigiert.
3. Erstmalige Standardprofile erzeugten unnötige sichtbare Ereignisse. Normale Standard- und Wiederherstellungsfälle werden jetzt nur im Hintergrund protokolliert; sichtbare Warnungen erscheinen ausschließlich bei echter Selbstheilung.

## Validierung

- 97 Python-Tests bestanden
- 7 neue Profiltests bestanden
- GUI-Rasterprofil-Roundtrip unter Xvfb bestanden
- 12/12 Anwendungssimulationen bestanden
- 16/16 visuelle Szenarien bestanden
- Registryprüfung bestanden
- Architekturprüfung ohne Befund

## Releasezustand

Der Stand ist ein Releasekandidat. Die automatischen visuellen Referenzen sind grün; eine neue reale KDE-/XFCE-Sichtprüfung ist noch nicht signiert.
