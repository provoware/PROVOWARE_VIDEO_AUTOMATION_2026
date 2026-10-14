# CP-UX – Implementierungs- und Prüfstand (15.10.2026)

Masterauftrag: #234 · CP-A: #238 · Entwicklungs-PR: #239
Status: **Implementiert im PR-Zweig, nicht freigegeben, nicht gemergt.**

## Änderungen und Belege
| UX | Ergebnis im Entwicklungszweig | Status |
|---|---|---|
| UX-01 | `dashboard_settings.py` auf kanonische Rendererwerte umgestellt; Speicherdatei unter XDG-Konfiguration, atomarer Schreibvorgang, Übernahme alter Schlüssel; `qt_ui.py` bindet Zustand an sichtbare Steuerelemente | Code umgesetzt; Tests in CI ausstehend |
| UX-02 | `qt_main_layout.py`: global sichtbare 2×2-Einstellungsleiste mit Auflösung, Qualität, Bildeffekt und Ausgabeordner | Code umgesetzt; Sichtabnahme offen |
| UX-03 | Vier Hauptreiter, keine dauerhaft sichtbare zweite Phase-3-Navigation; Werkzeuge/Hilfe separat; erweiterte Optionen ohne doppelte Grundeinstellungen | Code umgesetzt; Qt-Prüfung offen |
| UX-04 | Normaler Audio-/Bildimport inkl. Phase-3-Kompatibilitätsadapter führt in einen gemeinsamen `MediaImportDialog`; sichtbare Bildminiaturen werden im Hintergrund dekodiert | Bildbasis umgesetzt; persistenter Cache/Videominiaturen weiterhin offen |
| UX-05 | Startknopf erklärt auch ohne Quellen die nötigen Schritte. `_parity_start` validiert bevor gerendert wird | Code umgesetzt; Wayland-Smoketest offen |
| UX-06 | Grundschrift mindestens 12pt, einzeilige Medienlisteneinträge, flexible Tabellenbreiten, ältere Themen auf mind. 12pt begrenzt | Code umgesetzt; echte DPI-/Fensterprüfung offen |
| UX-07 | `_parity_options` überschreibt Grundwerte aus dem Dashboard nicht mehr; `quick_mode='custom'` beim tatsächlichen Auftrag; FFmpeg-Befehls- und Phase-3-Smoke-Tests erweitert | Code umgesetzt; vollständige CI ausstehend |

## Zusätzlich entdeckte Kompatibilitätsrisiken
1. `qt_phase3.py` und alte Werkzeugdienste verwenden `mode`; ein **unsichtbarer** Kompatibilitätsadapter verhindert Attributfehler, ist aber keine zweite sichtbare Einstellung.
2. `qt_legacy_parity_completion.py` ersetzte die Basisauswahl stillschweigend durch den alten System-Dateidialog: jetzt auf gemeinsamen Medienbrowser umgestellt.
3. Ursprüngliche Qt-Vertragstests bezogen sich auf entfernte 'Ausgabe festlegen'-Schritte. Erwartungswerte wurden bewusst auf die neue Architektur umgestellt.
4. Die native Wayland-Smokeprüfung erwartete zu Recht einen für Hilfestellung klickbaren Startknopf. Dies wurde unter Beibehaltung der verbindlichen Vorprüfung wiederhergestellt.

## Offene Checkpoints und Abnahme
- [ ] Auf **aktuellem** Commit Qt6-Orchestrator und nativen Wayland-Smoke vollständig grün.
- [ ] Tests im CI: `test_dashboard_settings_contract.py` und `test_dashboard_ffmpeg_contract.py` grün.
- [ ] Reale Bedienung auf Kubuntu Plasma Wayland bei 100/125/150/200 % ohne verdeckte Kernbedienelemente.
- [ ] Bildimporte mit realen PNG/JPEG/WEBP/AVIF, Fehlerfällen und großen Ordnern getestet.
- [ ] Caching/Index für ausschließlich Videos, Downloads, Bilder mit Medienfilter und Ausschlüssen implementiert (CP-E).
- [ ] Rendering und Diashows inklusive technischer Effekte und Fallbacks vollständig geprüft.
- [ ] Kein Merge/Stable bis vollständiger Abnahme.

## Nächste Reihenfolge
1. CI-Fehler auf PR #239 anhand der Logs beheben; die Änderungsregeln nicht umgehen.
2. Reale Skalierungs-/Fensterprüfung; UI-Elemente bei Bedarf erneut anordnen.
3. CP-E: dauerhafter SQLite-Medienindex und Thumbnail-Dateicache mit XDG-Verzeichnisfilter, danach Leistungsmessung.
