# VideoBatch Fast 2.8.3-rc23 – vollständige Abschlussanalyse

## Ausgangsproblem

Beim Anklicken eines Eintrags in der Medienliste konnte die Anwendung hart abstürzen. Die Ursache lag nicht in der ausgewählten Datei, sondern in der GUI-Architektur: Scan-, Vorschau- und Thumbnail-Arbeiter konnten Tkinter indirekt aus Hintergrundthreads anstoßen. Tkinter ist nicht threadsicher. Unter ungünstigem Timing führte das zu Tcl-Fehlern, Zugriffen auf bereits zerstörte Widgets oder einem vollständigen Prozessabbruch.

## Behobene Schwachstellen und Fehler

1. **Tk-Zugriff aus Hintergrundthreads**
   - Hintergrundarbeiter schreiben ausschließlich in eine begrenzte Python-Ereigniswarteschlange.
   - Nur der GUI-Hauptthread verarbeitet Ereignisse und verändert Widgets.

2. **Unbegrenzte Ereigniswarteschlange**
   - Die Queue besitzt eine feste Obergrenze von 256 Ereignissen.
   - Produzenten werden kontrolliert gebremst, statt den Speicher unbegrenzt zu füllen.

3. **Überholte Vorschauaufträge**
   - Bei einem neuen Auswahlfokus wird ein noch nicht gestarteter alter Auftrag abgebrochen.
   - Generationen verhindern, dass verspätete Ergebnisse die aktuelle Vorschau überschreiben.

4. **Hängender Aktivitätszähler nach Future-Abbruch**
   - Die Freigabe ist an den tatsächlichen Future-Abschluss gekoppelt.
   - Auch ein abgebrochener, nie gestarteter Auftrag setzt den Vorschauzustand korrekt zurück.

5. **Race beim Schließen des Dialogs**
   - Polling, Scan, Renderverzögerung und Auswahlereignisse werden kontrolliert beendet.
   - Späte Arbeitsergebnisse verändern keine zerstörten Widgets.

6. **Falsche Vorschau bei Mehrfachauswahl**
   - Maßgeblich ist immer der zuletzt aktiv angeklickte Eintrag.
   - Die übrige Mehrfachauswahl bleibt vollständig erhalten.

7. **Unsynchronisierte Listen- und Symbolansicht**
   - Auswahl, Fokus und gesammelte Dateien werden beim Ansichtswechsel übertragen.
   - Ein Wechsel der Darstellung verliert keine Auswahl.

8. **Fehlende Symbolansicht**
   - Eine virtualisierte Kachelansicht mit kleinen Bildvorschauen, Dateityp, Name und Größe wurde ergänzt.
   - Ordner, Audio und Video erhalten eindeutige Ersatzdarstellungen.

9. **Widgetexplosion bei großen Ordnern**
   - Es werden nur sichtbare Kacheln gezeichnet.
   - Ein Test mit 20.000 Einträgen erzeugte weniger als 100 Thumbnailanforderungen.

10. **Unbegrenzter Thumbnail-Speicher**
    - Der Bildcache ist auf 256 Einträge begrenzt.
    - Beim Ordnerwechsel werden nicht mehr relevante Einträge entfernt.

11. **Endlosschleife bei fehlerhaften Vorschaubildern**
    - Fehlgeschlagene Thumbnails werden pro Ordnerzustand zwischengespeichert.
    - Sie werden nicht bei jedem Neuzeichnen erneut angefordert.

12. **Vollständiger Neuaufbau nach jedem Scanblock**
    - Scanergebnisse werden zeitlich gebündelt gerendert.
    - Die Ansicht wird nicht mehr für jeden 128er-Block vollständig neu aufgebaut.

13. **Unzugängliche Sortierung in der Symbolansicht**
    - Name, Größe, Änderung und Art sind direkt auswählbar.
    - Die Sortierrichtung lässt sich sichtbar umkehren.

14. **Verdeckte Aktionsleiste bei 1220 × 760**
    - Der Dialog verwendet ein festes Vier-Zeilen-Raster.
    - Kopf, Navigation, flexibler Inhalt und Aktionen konkurrieren nicht mehr um denselben Platz.

15. **Abgeschnittene Hauptaktion**
    - Die Aktionszone wurde in zwei Ebenen gegliedert.
    - „Auswahl übernehmen + im Ordner bleiben“ nutzt die verfügbare Breite vollständig.

16. **Übergroße Vollvorschau**
    - Große Bilder werden auf den verfügbaren Vorschaubereich begrenzt.
    - Seitenverhältnis und Lesbarkeit der Metadaten bleiben erhalten.

17. **Helle Schrift auf hellen Eingabefeldern**
    - Vordergrundfarben werden per relativer Luminanz und Kontrastverhältnis bestimmt.
    - Readonly-Kombinationsfelder besitzen eine ausdrückliche Zustandsbelegung für Hintergrund und Text.

18. **Uneinheitliches Erscheinungsbild**
    - Kopfbereich, Navigation, Medienfläche, Live-Vorschau und Aktionen sind als klar getrennte Ebenen gestaltet.
    - Fokus, Auswahl, Erfolg, Hauptaktion und Abbruch sind visuell eindeutig.

## Ergebnis

Die Absturzursache wurde architektonisch entfernt und nicht nur mit einer Fehlermeldung verdeckt. Die Medienauswahl bleibt bei schnellem Klicken, Mehrfachauswahl, Ansichtswechsel, laufendem Scan und paralleler Thumbnailerzeugung stabil. Die Symbolansicht ist virtualisiert und für große Verzeichnisse vorbereitet. Kontraste werden programmatisch abgesichert. Das Release-Manifest bindet 385 geprüfte Dateien.

## Bewusst offene Stable-Gates

- Ruff 0.16.1 ist in der isolierten Umgebung nicht installiert.
- MyPy 2.3.0 ist nicht installiert.
- Bandit 1.9.4 ist nicht installiert.
- pip-audit 2.10.1 ist nicht installiert.
- Physische KDE-Abnahme unter X11 und Wayland fehlt.
- Reale Langzeitprüfung mit sehr großer Medienmenge und langsamem externem Ziel fehlt.
