# Best Practices – gehärteter Entwicklungsvertrag

- Offline-Pfade als Zustand behandeln, nicht als Löschsignal.
- Vor jedem externen Prozess sämtliche Ziele reservieren.
- Quelldaten erst nach bestätigtem Zielhash entfernen.
- Wiederaufnahme über Journale statt Annahmen steuern.
- Hintergrundthreads immer über `finally` abschließen.
- Prozesse als Gruppe starten und begrenzt beenden.
- Pluginfähigkeiten erst nach vollständiger Implementierung freischalten.
- Sicherheitsversprechen technisch durchsetzen oder Funktion blockieren.
- Build und Verifikation nie im selben schreibenden Ablauf vermischen.
- Releaseprüfungen müssen vor und nach Ausführung denselben Dateivertrag bestätigen.
- Qualitätswerkzeuge exakt sperren und in einem separaten Entwickler-Venv installieren.

## Responsive Design und barrierearme Ansicht

### Ist-Analyse

- **Breite:** Das Dashboard besitzt drei Modi für eine, zwei oder drei Spalten. Die Umschaltung richtet
  sich sinnvoll nach der tatsächlich verfügbaren Inhaltsbreite neben der Seitenleiste. Vollständige
  Bedienelemente werden bevorzugt; bei Platzmangel sinkt die Spaltenzahl bis auf eins.
- **Höhe:** Die Layoutprofile unterscheiden derzeit nur kompakt, standard und groß. Breite und Höhe
  fließen zwar in die Auswahl ein, es fehlen aber eigene Regeln für niedrige, normale und hohe Fenster.
  Das bestätigt den offenen Befund `UI-012` der Bildvergleichs-Checkliste.
- **Darstellungsverhältnisse:** Geteilte Arbeitsbereiche speichern Verhältnisse statt Pixelwerten.
  Mindestgrößen begrenzen unbrauchbare Aufteilungen; ungültige oder veraltete Profile fallen auf
  geprüfte Standardwerte zurück. Das ist für Auflösungs- und Zoomwechsel robust. Die Profile beziehen
  jedoch nur Bildschirmgröße und Zoom ein, nicht die tatsächlich nutzbare Fensterfläche oder sehr
  breite beziehungsweise hochformatige Fensterformen.
- **Fenstergrenzen:** Gespeicherte Fenstermaße werden auf den sichtbaren Bildschirm begrenzt. Damit
  bleibt das Hauptfenster erreichbar. Mehrmonitor-Arbeitsflächen und nachträglich geänderte
  Arbeitsleisten sind durch die statische Randannahme noch nicht real bestätigt.
- **Skalierung:** Tk übernimmt die erkannte DPI-Skalierung. Zusätzlich gibt es globalen Zoom und
  Bereichszoom. Die gespeicherten Grenzen verhindern extreme Werte. Größere Schrift vergrößert jedoch
  nicht nachweislich jedes Höhenbudget; dadurch können lesbare Texte zugleich Inhalte verdrängen.
- **Kontrast und Fokus:** Kontrast-Hilfen und Prüfungen sichern wichtige Farbkombinationen ab.
  Tooltips reagieren auch auf Tastaturfokus, die Medienkacheln unterstützen Leertaste und Eingabetaste,
  und zentrale Menüaktionen besitzen Tastenkürzel. Eine vollständige, sichtbare Fokusreihenfolge für
  alle Dashboard-, Dialog- und Canvas-Aktionen ist noch nicht belegt.
- **Scrollen:** Einzelne Listen und Detailflächen dürfen intern scrollen. Ein globaler Scrollbereich als
  Ausgleich für eine zu hohe Kopfzone widerspricht dagegen der Bildvergleichs-Checkliste und erschwert
  Tastatur- sowie Zoomnutzung.

### Verbindliche Best Practices

1. **Nutzfläche statt Bildschirmgröße messen.** Breakpoints aus der Breite und Höhe des aktuellen
   Inhaltsbereichs ableiten; Seitenleiste, Fensterrahmen und Systemleisten nicht doppelt einrechnen.
2. **Breite und Höhe getrennt klassifizieren.** Spaltenmodus und Höhendichte sind unabhängige
   Entscheidungen. Ein breites, niedriges Fenster darf nicht dieselbe Kopf- und Kartenhöhe erhalten wie
   ein gleich breites, hohes Fenster.
3. **Seitenverhältnis nur als Zusatzsignal verwenden.** Hochformat, 4:3, 16:9 und Ultrawide dürfen
   niemals allein einen Modus bestimmen. Maßgeblich bleibt, ob die erforderlichen Mindestflächen nach
   Schrift- und DPI-Skalierung tatsächlich verfügbar sind.
4. **Inhalt vor Dekoration schützen.** Header, Kennzahlen und Aktionsleiste erhalten ein begrenztes
   Höhenbudget; Quellen, Queue und Details teilen sich die verbleibende flexible Fläche. Keine wichtige
   Aktion darf abgeschnitten, überlagert oder nur durch globales Scrollen erreichbar sein.
5. **Umbruch statt Verkleinerung.** Bei zu wenig Breite Aktionen geordnet umbrechen, gruppieren oder mit
   verständlichem Kurztext anzeigen. Schrift und Trefferflächen nicht verkleinern, um ein starres Raster
   zu erhalten.
6. **Zoom als Layoutzustand prüfen.** Jede unterstützte Fensterklasse mindestens mit kleinstem,
   normalem und größtem globalen Zoom prüfen. Bereichszoom darf weder Fokus noch primäre Aktionen aus
   dem sichtbaren Bereich verdrängen.
7. **Tastaturweg vollständig halten.** Alle Mausaktionen benötigen eine Tastaturalternative. Fokus muss
   sichtbar sein, einer verständlichen Reihenfolge folgen und darf nach Layoutwechsel, Dialogschluss oder
   dynamischem Neuaufbau nicht verloren gehen.
8. **Information nie nur über Farbe vermitteln.** Status zusätzlich mit Text oder Symbol benennen.
   Textkontrast, Fokusmarkierung, deaktivierte Zustände und Auswahlzustände getrennt prüfen.
9. **Scrollbereiche begrenzen und benennen.** Nur lange Datenlisten oder Details intern scrollen.
   Tastaturfokus muss den richtigen Bereich aktivieren; verschachtelte Scrollflächen sind zu vermeiden.
10. **Reale Abnahme bleibt Pflicht.** Statische Verträge belegen nur Regeln. Freigabefähig ist eine
    sichtbare Änderung erst nach Zielsystem-Screenshots und Bedienprüfung mit Tastatur, hoher
    Schriftvergrößerung und den relevanten Fensterformen.

### Kleinster empfohlener Folgeblock

1. Für denselben Programmzustand reale Screenshots in niedriger, normaler und hoher Fensterhöhe sowie
   bei großer Schrift erfassen.
2. Sichtbare Nutzfläche, angeforderte Widgetgrößen, Clipping, Fokusweg und Scrollbereiche messen.
3. Erst danach einen reinen Höhenmodus-Vertrag ergänzen und mit fokussierten Grenzwerttests absichern.
4. Anschließend genau eine betroffene Dashboardzone anpassen und auf dem Zielsystem erneut abnehmen.

**Offen:** Eine Screenreader-Abnahme, vollständige Tastaturinventur, Mehrmonitorprüfung und reale
Sichtprüfung bei maximalem Zoom liegen in dieser Analyse nicht vor.

**Bewusst nicht geändert:** Keine Breakpoints, Layoutverhältnisse, Mindestgrößen, Farben, Texte oder
Widgets wurden auf Basis unbestätigter Annahmen angepasst.
