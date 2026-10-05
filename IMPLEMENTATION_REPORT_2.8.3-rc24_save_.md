# Implementierungsbericht 2.8.3-rc24

## Ziel

Den weiterhin reproduzierbaren Absturz beim Anklicken eines bereits ausgewählten Bildes
strukturell beseitigen und sämtliche angrenzenden Vorschau-, Fehler- und Diagnosepfade härten.

## Ursache

RC23 trennte die Hintergrundarbeit im Medienimportdialog vom Tk-Hauptthread. Die bereits
ausgewählte Projekt-Medienliste besaß jedoch einen zweiten Vorschaupfad. Jedes
`<<TreeviewSelect>>`-Ereignis konnte dort einen neuen Thread und einen neuen FFmpeg-Prozess
starten. Schnelle Klickfolgen erzeugten parallele native Vorschauprozesse, verspätete Ergebnisse
und direkte Übergaben beliebiger PNG-Dateien an Tks nativen Decoder.

## Umsetzung

- genau ein dauerhafter serieller Vorschauarbeiter
- 180-ms-Debounce für Auswahlereignisse
- Generationstoken gegen verspätete Ergebnisse
- Fokuszeile bestimmt die Vorschau bei Mehrfachauswahl
- keine Tk-Aufrufe aus Hintergrundthreads
- Pillow-Prüfung vor `ImageTk.PhotoImage`
- Grenzen von 64 MiB und 24 Millionen Pixeln für Vorschaubilder
- sichere Behandlung gelöschter, beschädigter und nicht lesbarer Dateien
- sauberes Invalidieren und Beenden des Vorschaucontrollers
- funktionsfähige Aktion „Datei technisch prüfen“
- Diagnoseprotokoll mit temporärem Fallback
- reale statt angenommene Linux-Namespace-Prüfung
- Migration des veralteten Splitter-GUI-Tests auf Tabs, Scrollraster und Bereichszoom

## Module

- `selection_preview_controller.py`: serielle, zusammenführende Vorschauwarteschlange
- `ui_selection_preview_mixin.py`: Auswahl-, Debounce-, Anzeige- und Lösungslogik
- `preview_service.py`: defensive Bildprüfung und Größenbegrenzung
- `ui_event_handlers_mixin.py`: GUI-Hauptthread-Verarbeitung der Vorschauergebnisse
- `ui_services_mixin.py`: kontrollierter Lebenszyklus beim Schließen

## Ergebnis

Der reale GUI-Stresstest mit 120 schnellen Klicks besteht. Maximal ein Vorschauauftrag
arbeitet gleichzeitig. Die zuletzt aktive Auswahl bleibt maßgeblich. Architektur-,
Komplexitäts- und Coverage-Gates sind grün.


## Finalbereinigung

- 70 historische RC-Berichte und Nachweise verlustfrei unter `docs/archive/release-history/` gebündelt
- 16 veraltete doppelte visuelle Baselines entfernt
- zehn eigenständige Releaseunterlagen mit `_save_` gekennzeichnet
- fünf nicht releasefertige Status-/Gate-Dateien ausdrücklich als unfertig dokumentiert
- README und STATUS werden aus `RELEASE_FILE_STATUS.json` zweispaltig erzeugt
- Portable-, Manifest- und Stable-Kopien schließen das historische Archiv aus
- Hilfezentrum, Cache-Dialog und Medienauswahl mit präziseren Texten und Tooltips versehen
- Release-Dateivertrag blockiert nicht deklarierte `_save_`-Dateien im Projektstamm
- `manifest.json` wird gegen die kanonische Release-Evidenz auf Version, Kanal, Build-Datum und Einstieg geprüft
- Stable bleibt bis zur erneuten realen 100/150/200-%-Sichtabnahme des geänderten Qt-UI-Stands gesperrt
