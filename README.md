# VideoBatch Fast 2.8.3-rc24

RC21 verbessert den gesamten Nutzerfluss vor Produktionsbeginn. Fehler werden nicht mehr nur beschrieben: VideoBatch bietet direkt ausführbare, reversible Lösungswege an. Fehlende sichere Einstellungen werden automatisch ergänzt; nicht eindeutig lösbare Angaben werden gezielt abgefragt.

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

## Entwicklungsstand

- 253/253 automatisierte Tests bestanden
- 79 % Gesamt-Coverage mit Branch-Messung
- 12/12 Anwendungssimulationen bestanden
- 12/12 Fehlerlabor-Szenarien bestanden
- 17/17 visuelle Referenzszenarien bestanden
- 0 Registry-, Architektur- und interne Qualitätsbefunde
- maximale Funktionskomplexität 29

## Stable-Grenze

Für Stable bleiben reale Läufe der festgelegten Versionen von Ruff, MyPy, Bandit und pip-audit sowie die physische KDE-X11-/Wayland-Abnahme und ein großer Langzeit-Medientest erforderlich.
## RC22: responsiver Workflow und Großordnerimport

- Ausgabeordner und Live-Statistik direkt im Header
- sechs Haupt-Tabs mit dynamischem 2×2-Workflowraster
- vier moderne Themes und separater Bereichszoom
- blockweises Einlesen sehr großer Medienordner
- zusammengefasster Vorbereitungsassistent
- vollständiges Projekt-ZIP als einzige Vorrelease-Ausgabe

