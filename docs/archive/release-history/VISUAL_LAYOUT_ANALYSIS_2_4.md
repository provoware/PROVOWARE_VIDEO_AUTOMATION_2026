# Bildanalyse und Übertragung in VideoBatch Fast 2.4.0-rc1

## Visuelle Kerneigenschaften der Vorlage

1. **Dunkle, ruhige Hauptfläche** mit leicht olivem Unterton.
2. **Warme goldene Kontur** als ordnendes Rahmenmotiv.
3. **Vier große Primärkacheln** mit klar unterscheidbaren Akzentfarben.
4. **Zwei mittlere Inhaltskarten** für Assistent und Tipps.
5. **Eine zusätzliche Schnellaktionsleiste** im unteren Bereich.
6. **Große Typografie** mit klarer Hierarchie: Titel → Frage → Aktion → Details.
7. **Laienlogik**: zuerst Handlung, dann Hilfe, erst danach Technik.

## Übertragene Anforderungen

- Header mit Titel, Untertitel, Entwicklerinformation-Schnellspeicher, Uhrzeit und Monatskalender.
- Vier große Kacheln mit eindeutigen Aufgaben.
- Leere, aber klar benannte Prototyp-Bereiche für künftige Erweiterungen.
- Getrennte Architektur: UI, Projektzustand, Plugin-Sandbox, Registries, Texte, Theme.
- JSON-versionierte Layoutbeschreibung in `registries/UI_BLUEPRINT.json`.
- Vollautomatische Selbstheilung für Projektdatei und Konfiguration.
- Plugin-Ausführung nur isoliert in einer Subprozess-Sandbox.

## Technische Ableitung

- Der Header ist für kleine und große Anzeigen horizontal/vertikal flexibel angelegt.
- Der Monatskalender besitzt klickbare Tagesmarkierungen und speichert deren Zustand im Projekt.
- Die Projektdatei dient als zentraler, robuster Wiedereinstiegspunkt.
- Farbige Primärkacheln bleiben bedienbar, auch wenn noch nicht alle Zielmodule fertig implementiert sind.
