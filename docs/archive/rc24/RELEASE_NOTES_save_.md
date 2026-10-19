# Release Notes 2.8.3-rc24

## Kritische Stabilitätskorrektur

Der verbleibende Absturz beim Anklicken eines Bildes in der bereits ausgewählten Medienliste wurde behoben.
Der frühere Pfad startete pro Auswahlereignis einen eigenen Hintergrundthread und einen eigenen
FFmpeg-Vorschauprozess. Schnelle Klickfolgen konnten dadurch parallele native Prozesse, veraltete
Ergebnisse und unsichere Bildübergaben an Tk erzeugen.

RC24 verwendet stattdessen genau einen seriellen Vorschauarbeiter. Neue Klicks ersetzen wartende
Anfragen; alte Ergebnisse werden anhand eines Generationstokens verworfen.

## Sichere Vorschau

- 180-ms-Debounce für schnelle Auswahlwechsel
- genau ein laufender Vorschauauftrag
- Fokuszeile statt erster Mehrfachauswahleintrag
- sichere Größen- und Pixelgrenzen
- Pillow-Validierung vor ImageTk
- kontrollierte Behandlung gelöschter oder beschädigter Dateien
- kein Tk-Zugriff aus Hintergrundthreads
- sauberes Beenden beim Programmschluss

## Interaktive Fehlerlösung

Bei einem Vorschaufehler stehen jetzt funktionsfähige Aktionen bereit:

- Datei technisch erneut prüfen
- Datei extern öffnen
- Protokoll öffnen

## Finale UI-, Bedien- und Barrierefreiheitskorrekturen

Ein realer Sichttest bei **125 %** zeigte anschließend, dass die gleichzeitige Drei-Spalten-Darstellung trotz korrekter Schrift-Skalierung zu eng blieb. Deshalb wurde der Hauptablauf strukturell getrennt:

- **1 · Dateien**, **2 · Ausgabe** und **3 · Produktion** besitzen eigene Arbeitsseiten
- der Hauptarbeitsbereich benötigt keine übergeordnete Scrollfläche mehr
- Audio und Bilder/Videos stehen auf der Dateiseite in zwei ausreichend hohen Listen nebeneinander
- Projekt, Hilfe, Diagnose und Vorschau dürfen die aktive Hauptseite nicht dauerhaft zusammendrücken
- Alt+1, Alt+2 und Alt+3 öffnen zuerst die passende Arbeitsseite und setzen dann den Fokus
- Sortieren bleibt eine reine Ansichtsfunktion; die Produktionsreihenfolge wird nur ausdrücklich übernommen
- die reale Abschlussabnahme umfasst nun 100 %, 125 %, 150 % und 200 %

Vor der Stable-Promotion wurden weitere reproduzierbare Restbefunde im Qt-Hauptpfad korrigiert:

- dynamische Status- und Schritttexte bleiben für Vorlesesoftware als aktueller sichtbarer Text erhalten
- der Zustand „ANALYSE“ wird nicht mehr fälschlich als Bereitschaft dargestellt
- Tabellenzeilen skalieren mit der 100–200-%-Ansicht
- globaler Ansichts-Zoom und Listen-Zoom besitzen getrennte Tastenkürzel
- Farbschema und globale Ansichtsvergrößerung überschreiben sich nicht mehr gegenseitig
- Sortieren ändert zunächst nur die Ansicht; die Produktionsreihenfolge wird erst nach ausdrücklicher Übernahme verändert

Wegen dieser UI-/Skalierungsänderungen ist die physische Sichtabnahme des aktuellen Kandidaten erneut erforderlich.

## Ausgabeform

RC24 wird als vollständiges Projekt-ZIP bereitgestellt. Teil- und Onlineupdates bleiben bis nach
der Stable-Veröffentlichung ein Nachrelease-System.

Ein als verifiziert gekennzeichnetes Projektartefakt wird ausschließlich nach erfolgreichem
Read-only-Preflight, dem aktuellen Ubuntu-26.04/KDE-/Wayland-Zielvertrag und erneut bestandenen
Abschlussverträgen erzeugt. Es wird nicht automatisch als Release veröffentlicht.

## Verifizierbares Gesamtprojekt-Artefakt

Das Prüfartefakt enthält:

- das vollständige Projekt-ZIP aus dem exakt geprüften Git-Commit
- eine SHA-256-Datei für das gesamte ZIP
- `ARTIFACT_CONTENTS.json` mit Pfad, unkomprimierter Größe und SHA-256 jeder Datei
- `VERIFIED_SOURCE_ARTIFACT.json` mit Commit, ZIP-Größe, ZIP-SHA-256 und Vertragsstatus
- `release-manifest-check.json` mit dem maschinenlesbaren Manifestprüfergebnis

Der neue Prüfmodus von `scripts/build_artifact_contents.py` vergleicht ein heruntergeladenes ZIP
vollständig gegen die zugehörige Inhaltsliste. Er bricht fail-closed ab bei:

- fehlenden Dateien
- zusätzlichen Dateien
- abweichenden Dateigrößen
- abweichenden SHA-256-Werten
- abweichendem Archivnamen oder Commit
- widersprüchlicher Dateizahl oder Gesamtgröße
- doppelten ZIP-Pfaden
- beschädigten ZIP-Einträgen
- ungültiger oder unsortierter JSON-Struktur

Prüfaufruf:

```bash
python3 scripts/build_artifact_contents.py \
  PROVOWARE_VIDEO_AUTOMATION_2026_*_verified.zip \
  --check ARTIFACT_CONTENTS.json
```

Exitcodes: `0 = vollständig bestätigt`, `1 = reproduzierbare Drift`,
`2 = beschädigtes oder ungültiges Artefakt beziehungsweise Prüfmanifest`.

## Finalisierte Projektstruktur und Hilfe

- releasefertige eigenständige Unterlagen tragen `_save_`
- README zeigt fertige und unfertige Dateien direkt nebeneinander
- historische RC-Berichte sind archiviert und aus Auslieferungen ausgeschlossen; nicht deklarierte `_save_`-Dateien im Stamm werden blockiert
- Changelog-Dubletten und alte visuelle Baseline-Dubletten sind entfernt
- Tooltips erscheinen verzögert, funktionieren per Tastatur und bleiben im sichtbaren Bildschirm
- Cache- und Hilfeaktionen erklären vorab Wirkung, Schutz und nächsten Schritt
- FFmpeg 7+ wird bei atomaren Vorschau-Teildateien explizit auf PNG festgelegt
