# Verbindlicher Agentenauftrag – VideoBatch (Issue #235)
Master: https://github.com/provoware/PROVOWARE_VIDEO_AUTOMATION_2026/issues/235

**Status: geplant; keine Implementierung oder Freigabe behauptet.**

## Zentrale Anforderungen
- Dashboard: Auflösung, Qualität, Effekt und Ausgabeort dauerhaft sichtbar, keine doppelten Eingabestellen.
- Vier Arbeitsbereiche: Dateien, Produktion, Erweiterte Einstellungen, Werkzeuge/Diagnose.
- Lesbare Schrift ab 12 pt, konsistente Vergrößerung und flexible dreigeteilte Ansichten.
- Gemeinsamer Medienbrowser mit echten Miniaturbildern, sofortiger Großvorschau, Video-Standbild und Mehrfachauswahl.
- Offline-SQLite-Index + persistenter Thumbnail-Cache ausschließlich für die XDG-Ordner Videos, Downloads und Bilder. Nur Bild-, Audio- und Videoformate; Entwicklungsverzeichnisse ausschließen.
- Sofortanzeige vorhandener Daten, Hintergrundabgleich und inotify; Originalmedien niemals verändern.

## Arbeitspakete mit Pflicht-Checkpoints
- [ ] 01 / CP-01 Ist-Zustand, Tests, Referenzbilder und Codeabhängigkeiten dokumentieren.
- [ ] 02 / CP-03 Einheitliches Konfigurationsmodell; Nutzerwahl > bewusst angewendete Vorlage > Automatik; End-to-End-Renderprüfung.
- [ ] 03 / CP-02 Permanente Dashboard-Steuerleiste implementieren; redundante Controls entfernen.
- [ ] 04 / CP-04 Reiter und Layout entschlacken; drei flexible Arbeitszonen.
- [ ] 05 / CP-05 Typografie, Kontrast und Tastaturbedienung bei 100/125/150/200 Prozent prüfen.
- [ ] 06 / CP-06 Medienbrowser mit echten Thumbnails, Klick-Vorschau und Video-Standbildern testen.
- [ ] 07 / CP-07 Drei XDG-Ordner, Medienfilter, Ausschlüsse, SQLite und Änderungsabgleich testen.
- [ ] 08 / CP-08 Persistenten Cache, Limits und Lasttests (1k/10k/100k) prüfen.
- [ ] 09 / CP-09 SQLite-Defekte, volle Datenträger, Rechtefehler, fehlende Medien und Abbruch prüfen.
- [ ] 10 / CP-10 Automatisierte Tests plus reale Kubuntu/KDE/Wayland-Sichtabnahme dokumentieren.
- [ ] 11 / CP-11 Handbuch, Testbelege, PRs, Rückfallpläne und Freigabeprüfung komplettieren.

## Bearbeitungsregeln
Kleine Pull Requests in der Reihenfolge CP-01 -> CP-03 -> CP-02 -> CP-04/05 -> CP-06 -> CP-07/08 -> CP-09 -> CP-10 -> CP-11. Für jeden Checkpoint konkrete Testergebnisse im Issue #235 verlinken. Keine direkte Stable-Freigabe und keine Änderungen an Originalmediendateien. Die ausführliche Planung liegt ergänzend als PDF und TXT in der zugehörigen Chat-Ausgabe.
