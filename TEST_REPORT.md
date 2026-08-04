# Testbericht – VideoBatch Fast 2.8.3-rc24

## Ergebnis

- 272/272 automatisierte Tests bestanden
- 2 Plugin-Sandboxtests korrekt übersprungen, weil die isolierte Laufzeit Linux-Namespaces real blockiert
- 82,89 % Zeilenabdeckung
- 66,80 % Branch-Abdeckung
- 79,70 % kombinierte Coverage
- 12/12 Anwendungssimulationen bestanden
- 12/12 Fehlerlabor-Szenarien bestanden
- 18/18 visuelle Szenarien bestanden
- isolierte visuelle Wiederholungsprüfung bestanden
- GUI-Tab-/Grid-/Zoom-Roundtrip bestanden
- 6/6 gezielte RC24-Absturzregressionen bestanden
- reale GUI-Stressprüfung mit 120 schnellen Medienklicks bestanden
- Versions-, Registry-, Text-, Manifest- und Architekturverträge bestanden

## Kritischer RC24-Test

Die bereits ausgewählte Bilderliste wurde mit 120 schnellen Fokus- und Auswahlwechseln belastet.
Dabei blieb exakt ein Vorschauarbeiter aktiv. Wartende Anfragen wurden zusammengeführt,
veraltete Ergebnisse verworfen und ausschließlich die zuletzt aktive Datei dargestellt.

## Bewusst nicht behauptet

Nicht real ausgeführt wurden Ruff 0.16.1, MyPy 2.3.0, Bandit 1.9.4,
pip-audit 2.10.1, die physische KDE-X11-/Wayland-Abnahme und ein
mehrstündiger Langzeitrender auf langsamem externem Speicher.

## Frischpaketprüfung

Ein neu entpacktes Vorab-ZIP bestand Manifest, Version, isolierte Kompilierung, Architektur, interne Qualität sowie 272/272 Tests. Der Diagnosepfad wurde dabei absichtlich unter einem noch nicht vorhandenen Elternordner angelegt.
