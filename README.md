<!-- release-status:start -->
# provoware - videoautomation - 2026 · 2.8.3-rc24

**Kanal:** rc
**Freigegebener Qualitätsbericht:** `VideoBatch_Fast_2.8.3-rc24_BUILD_REPORT.json`

- 272/272 automatisierte Tests bestanden
- 82,89 % Zeilenabdeckung
- 66,80 % Zweigabdeckung
- 18/18 visuelle Szenarien bestanden

### Offene Stable-Gates

- Ruff 0.16.1
- MyPy 2.3.0
- Bandit 1.9.4
- pip-audit 2.10.1
- physische KDE-X11-/Wayland-Abnahme
- Langzeitrender mit großer Medienauswahl und langsamem externem Ziel
<!-- release-status:end -->

**Ausgabe vor Stable:** immer als vollständiges Projekt-ZIP. Teil- und Onlineupdates bleiben bis nach der Stable-Freigabe ein deaktivierter Nachrelease-Mechanismus.

## Zentrale Verbesserungen

- interaktive Fehlerlösung mit konkreten Aktionsschaltern
- sicherer Ausgabe- und Projektordner kann direkt aus dem Lösungsfenster erstellt werden
- automatische Reparatur vergessener oder ungültiger Schnellmodus- und Pfadeinstellungen
- intelligenter Wechsel zum Diashowmodus bei ungleichen Audio-/Bildmengen
- korrigierte Vorschau bei Mehrfachauswahl: maßgeblich ist der zuletzt aktiv angeklickte Eintrag
- mehrere Auswahlrunden im selben Ordner über „Auswahl übernehmen + im Ordner bleiben“
- bereits übernommene Dateien werden in der Liste sichtbar markiert
- globale Headerstatistik mit Audio-, Bild-, Video- und Auftragszahl sowie Modus, Übergang, Szenenkopplung und Schnellprofil
- Lösungsdialoge mit dauerhaft erreichbaren Aktionen; lange Erklärungen und technische Details sind scrollbar
- dauerhafter Thumbnail-Datenträgercache mit 256-MiB-/2.000-Dateien-Grenze, LRU-Bereinigung und atomarer Speicherung

## Dauerhafter Thumbnail-Datenträgercache

Vorschaubilder werden unter dem XDG-Benutzercache gespeichert und bei erneutem Öffnen wiederverwendet. Der Cache wächst nicht unbegrenzt: Standardmäßig gelten maximal 256 MiB und 2.000 PNG-Dateien. Bei Überschreitung werden zuerst die am längsten nicht verwendeten Einträge entfernt. Originalmedien und andere Dateitypen werden niemals gelöscht.

Der Cache-Schlüssel berücksichtigt Quellpfad, Änderungszeit, Dateigröße und gewünschte Breite. Eine geänderte Quelldatei erhält deshalb automatisch eine neue Vorschau. Neue Vorschaubilder werden zunächst als Teil-Datei erzeugt und erst nach erfolgreicher Prüfung atomar unter dem endgültigen Namen veröffentlicht.

## Fortschritt der aktuellen Folge-Iteration

**Fortschritt:** 100 % für den abgegrenzten Punkt „dauerhafter Thumbnail-Datenträgercache“.

**Erledigt:** persistente Wiederverwendung, Größen- und Dateigrenze, LRU-Bereinigung, Quelländerungs-Erkennung, atomare Speicherung, Fehlerbereinigung, Schutz des aktiven Eintrags, fokussierte Regressionstests und `FAIL_MEMORY_PASS.md`.

**Offen:** Stable-Gates bleiben unverändert offen; keine physische KDE-Abnahme und kein Langzeitrender wurden in dieser Iteration durchgeführt.

## Sicheres Berechtigungskonzept

VideoBatch arbeitet ohne pauschale Rootrechte, `chmod 777` oder rekursive Besitzänderungen. Schreibziele werden durch reale Schreibproben geprüft. Bei Problemen kann der Nutzer:

1. einen neuen Benutzerordner anlegen,
2. einen anderen Ordner auswählen,
3. einen geprüften Standardordner verwenden,
4. den betroffenen optionalen Schritt für diesen Lauf deaktivieren.

Originaldateien und bestätigte Projektzustände bleiben bei Fehlern unverändert.

## Bedienablauf

1. Audios und Medien auswählen.
2. Auswahlstatistik im Header kontrollieren.
3. Modus und Einstellungen wählen oder die Automatik verwenden.
4. Produktion starten.
5. Fehlende Angaben werden automatisch ergänzt oder mit direkten Lösungsaktionen abgefragt.
6. Bei Unsicherheit zuerst `PROJEKTORDNERSTRUKTUR.md` öffnen und die Schritt-für-Schritt-Anleitung nutzen.

## Laienfreundliche Projektübersicht

Die Datei `PROJEKTORDNERSTRUKTUR.md` erklärt Ordner, wichtige Dateien, sichere Startbefehle, Funktionsbereiche, Barrierefreiheitsprinzipien und sinnvoll mitlieferbare Basisabhängigkeiten in einfacher Sprache.
