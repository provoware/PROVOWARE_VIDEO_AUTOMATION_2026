# Abschlussaudit – VideoBatch Fast 2.8.3-rc24

## Kritischer Befund

Der in RC23 verbleibende Absturz lag nicht im Medienimportdialog, sondern in der
bereits ausgewählten Projekt-Medienliste. Dort erzeugte jeder Auswahlklick einen
eigenen Vorschau-Thread samt FFmpeg-Prozess. Unter schneller Bedienung konnten
native Prozesse, Ergebnisreihenfolge und Bilddecoder miteinander kollidieren.

## Nachhaltige Korrektur

RC24 besitzt für diesen Pfad exakt einen seriellen Vorschaucontroller. Neue Anfragen
ersetzen wartende Anfragen. Generationstoken verhindern die Anzeige verspäteter
Ergebnisse. Tkinter wird ausschließlich im GUI-Hauptthread verändert. Bilder werden
mit Pillow validiert, begrenzt und erst danach an `ImageTk` übergeben.

## Zusätzlich behobene Schwachstellen

1. aktive Fokuszeile bei Mehrfachauswahl wurde nicht zuverlässig bevorzugt
2. technische Dateiprüfung war im Fehlerkatalog vorhanden, aber nicht angebunden
3. Diagnoseprotokoll konnte bei unbeschreibbarem Statusordner selbst den Build abbrechen
4. Sandboxfähigkeit wurde aus einer vorhandenen `unshare`-Datei abgeleitet
5. veralteter GUI-Test erwartete die entfernte Splitterarchitektur
6. Vorschaucontroller war zunächst zu stark in der zentralen UI-Datei gebündelt

Alle Punkte wurden korrigiert und mit Regressionen abgesichert.

## Audit-Ergebnis

- 325/325 Tests im kanonischen Vollregressionsnachweis bestanden
- 0 übersprungene Tests im belegten Vollregressionslauf
- 82,43 % Statement-/Zeilenabdeckung
- 67,21 % Branch-Abdeckung
- 18/18 visuelle Szenarien
- 12/12 Anwendungssimulationen
- 12/12 Fehlerlabor-Szenarien
- 0 Architekturprobleme
- 0 interne Qualitätsbefunde
- maximale Komplexität 29
- reale Klick-Stressprüfung mit 120 Auswahlwechseln bestanden
- exakter Offline-Qualitätslauf `33801346178` auf `048aa5733d9d0ce5fef872d25e0437fae08eab94`: Ruff, MyPy, Bandit und pip-audit jeweils bestanden
- P0-Kubuntu-Matrix, kanonischer Evidence-Lauf `33791408050` auf `9823e790f8e67a6e0f406b132c37569e3b95d977`: 4/4 bestanden

## Freigabegrenze

RC24 ist ein Releasekandidat. Stable bleibt blockiert, bis die physische
KDE-X11-/Wayland-Abnahme und der Langzeitrender vollständig grün sind.

## Frischpaketprüfung

Ein neu entpacktes Vorab-ZIP bestand Manifest, Version, isolierte Kompilierung, Architektur, interne Qualität sowie den belegten Vollregressionslauf. Der Diagnosepfad wurde dabei absichtlich unter einem noch nicht vorhandenen Elternordner angelegt.

## Repository-Abschluss

Der aktive Projektstamm enthält nur die aktuellen RC24-Nachweise. Frühere Berichte bleiben im historischen Archiv nachvollziehbar, werden jedoch nicht ausgeliefert. Der Release-Dateivertrag, die zweispaltige README-Tabelle und die `_save_`-Kennzeichnung sind maschinell geprüft. Stable bleibt wegen der zwei ausdrücklich genannten physischen beziehungsweise Langzeit-Gates gesperrt.
