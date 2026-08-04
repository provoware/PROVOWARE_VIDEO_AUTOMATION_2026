# VideoBatch Fast 2.8.3-rc20 – Abschlussanalyse

## Ergebnis

RC20 ist als vollständiger Releasekandidat konsistent, reproduzierbar paketierbar und funktional geprüft. Die neue Storyboard- und Wellenformfunktion verändert den sicheren Gleichlaufmodus nicht; bei Analysefehlern wird automatisch auf gleichmäßige Bildzeiten zurückgefallen.

## Gefundene und behobene Schwachstellen

1. **Ungültige Szenengrenzen bei extrem kurzen Audios:** Die bisherige Mindestlänge konnte bei vielen Bildern größer als die Gesamtdauer werden. Die Mindestgrenze wird jetzt dynamisch an Dauer und Bildzahl angepasst.
2. **Unbegrenzte beziehungsweise manipulierte Wellenform-Caches:** Cachegröße, Peakzahl, Zahlenwerte, Markerarten, Zeitgrenzen und Vertrauenswerte werden strikt validiert.
3. **Unnormalisierter Sortiermodus in Projektdateien:** Fremde Werte werden auf `manual` zurückgesetzt.
4. **EXIF-Sicherheitsfall:** Pillow-Decompression-Bomb-Fehler werden kontrolliert abgefangen.
5. **Textprüfung unvollständig:** Der neue Diashoweditor ist nun Bestandteil des statischen UI-Textvertrags.
6. **Komplexitätsüberschreitung in der Konfiguration:** `normalize_config` wurde modularisiert; maximale Projektkomplexität liegt wieder bei 28.
7. **Visueller Playlist-Test nach Tabumbau:** Der Test öffnet jetzt sowohl den Haupttab als auch den korrekten inneren Verarbeitungstab.

## Verbleibende Risiken

- Szenenerkennung ist eine robuste Heuristik, keine musikalische Wahrheit. Marker bleiben Vorschläge.
- Sehr große Bildsammlungen benötigen weiterhin reale Langzeit- und Speichertests.
- Plugin-Manager, Sandbox und Runner-Hauptcontroller besitzen im vollständigen Coveragebericht noch geringere Abdeckung als die kritischen Prozessunterfunktionen.
- Externe Qualitätswerkzeuge und physische KDE-X11-/Wayland-Abnahme sind weiterhin offene Stable-Gates.
- Das Update-System ist absichtlich kein primärer RC20-Ausgabeweg und wird erst nach der Stable-Freigabe produktiv aktiviert.
