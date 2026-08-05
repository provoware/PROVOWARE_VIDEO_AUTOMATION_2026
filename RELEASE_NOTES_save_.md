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

## Ausgabeform

RC24 wird als vollständiges Projekt-ZIP bereitgestellt. Teil- und Onlineupdates bleiben bis nach
der Stable-Veröffentlichung ein Nachrelease-System.

Ein als verifiziert gekennzeichnetes Projektartefakt wird ausschließlich nach erfolgreichem
Read-only-Preflight, vollständig grüner Kubuntu-Vierfachmatrix und erneut bestandenen
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
- historische RC-Berichte sind archiviert und aus Auslieferungen ausgeschlossen
- Changelog-Dubletten und alte visuelle Baseline-Dubletten sind entfernt
- Tooltips erscheinen verzögert, funktionieren per Tastatur und bleiben im sichtbaren Bildschirm
- Cache- und Hilfeaktionen erklären vorab Wirkung, Schutz und nächsten Schritt
- FFmpeg 7+ wird bei atomaren Vorschau-Teildateien explizit auf PNG festgelegt
