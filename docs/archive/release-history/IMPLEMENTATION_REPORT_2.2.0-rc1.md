# Implementierungsbericht – VideoBatch Fast 2.2.0-rc1

## Auftrag

Mindestens zehn laienoptimierte Schnellfunktionen für Techno und HardTechno bereitstellen. Jeder Modus soll alle technischen Parameter automatisch setzen, schnell bleiben und bei Fehlern kontrolliert auf eine sichere Alternative zurückfallen.

## Ergebnis

Umgesetzt wurden 13 Automatikmodi und ein getrenntes Expertenprofil. Die Modusauswahl ist als große Kachelmatrix in der Oberfläche sichtbar. Ein Klick setzt Effekt, Übergang, Encoderprofil, Codec, Auflösung und Ergebnisprüfung.

## Verarbeitungsprinzip

- kompatible Videos: Direktkopie, wenn der gewählte Modus keine Pixeländerung verlangt
- Bilder und Effektmodi: genau ein schneller FFmpeg-Renderdurchgang
- keine Zwischenvideos
- keine versteckten Zusatzrenderings
- maximal ein automatischer Fallback
- FFprobe-Prüfung vor Erfolgsmeldung

## Automatikmodi

1. Automatisch schnell
2. Maximale Geschwindigkeit
3. Techno Clean
4. HardTechno Impact
5. Industrial Dark
6. Acid Neon
7. Bass Pulse
8. Strobe Safe
9. Glitch Light
10. Monochrome Rave
11. Cold Warehouse
12. Red Alert
13. Sharp Stage

## Sicherheitsmaßnahmen

- zentrales Schnellmodusregister
- maschinenlesbares `QUICK_MODES_MANIFEST.json`
- Startprüfung vergleicht Manifest und aktiven Code
- unbekannte Konfigurationswerte werden auf einen sicheren Standard normalisiert
- jeder Modus verweist auf bekannte Effekte, Übergänge und Encoderprofile
- Originaldateien werden nicht verändert
- Ausgaben werden nicht still überschrieben
- Automatikfallback ist auf einen Versuch begrenzt
- starke Stroboskopeffekte sind ausgeschlossen

## Geänderte Kernmodule

- `src/videobatch_fast/quick_modes.py`
- `src/videobatch_fast/effects.py`
- `src/videobatch_fast/command_builder.py`
- `src/videobatch_fast/runner.py`
- `src/videobatch_fast/ui.py`
- `src/videobatch_fast/config.py`
- `src/videobatch_fast/validation.py`
- `src/videobatch_fast/verification.py`

## Prüfung

- Schnellmodusvertrag: bestanden
- 13 reale FFmpeg-Modi: bestanden
- Direktkopie: bestanden
- Einpass-Filterketten: bestanden
- automatischer Fallback: bestanden
- GUI-Kacheltest unter Xvfb: bestanden
- vollständige Testsuite: 25 bestanden

## Verbleibende Grenzen

- echte Übergänge zwischen mehreren Bildern innerhalb eines einzelnen Videos gehören nicht zum schnellen Paarmodus
- Effekte auf ein Video benötigen grundsätzlich Neucodierung
- reale Laufzeit hängt von Auflösung, Dauer, Codec und Hardware ab
