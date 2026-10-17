# CP-UX – Implementierungs- und Prüfstand (15.10.2026)

Masterauftrag: #234 · CP-A: #238 · Entwicklungs-PR: #239
Status: **Implementiert im PR-Zweig, nicht freigegeben, nicht gemergt.**

## Änderungen und Belege
| UX | Ergebnis im Entwicklungszweig | Status |
|---|---|---|
| UX-01 | `dashboard_settings.py` auf kanonische Rendererwerte umgestellt; Speicherdatei unter XDG-Konfiguration, atomarer Schreibvorgang, Übernahme alter Schlüssel; `qt_ui.py` bindet Zustand an sichtbare Steuerelemente | Code umgesetzt; Tests in CI ausstehend |
| UX-02 | `qt_main_layout.py`: global sichtbare 2×2-Einstellungsleiste mit Auflösung, Qualität, Bildeffekt und Ausgabeordner | Code umgesetzt; Sichtabnahme offen |
| UX-03 | Vier Hauptreiter, keine dauerhaft sichtbare zweite Phase-3-Navigation; Werkzeuge/Hilfe separat; erweiterte Optionen ohne doppelte Grundeinstellungen | Code umgesetzt; Qt-Prüfung offen |
| UX-04 | Normaler Audio-/Bildimport inkl. Phase-3-Kompatibilitätsadapter führt in einen gemeinsamen `MediaImportDialog`; sichtbare Bildminiaturen werden im Hintergrund dekodiert | Bild-/Videominiaturen mit persistenten Cache-Dateien umgesetzt; visuelle Geräteprüfung offen |
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
- [x] CP-E-Code: SQLite-Index nur für Videos, Downloads, Bilder, Dateifilter, sichere Abbrüche, Hintergrundaktualisierung und Lese-Cache implementiert.\n- [x] Ausgeschlossene Entwicklungsordner über erweiterte Qt-Einstellungen verwaltbar.\n- [x] Optionale Linux-inotify-Überwachung mit begrenzter Zahl von Verzeichniswächtern und zeitgesteuertem Sicherheitsabgleich implementiert.\n- [ ] Leistungsnachweis mit 100.000 gemischten Dateien und aktuellem Commit erfolgreich abgeschlossen.
- [ ] Rendering und Diashows inklusive technischer Effekte und Fallbacks vollständig geprüft.
- [ ] Kein Merge/Stable bis vollständiger Abnahme.

## Nächste Reihenfolge
1. CI-Fehler auf PR #239 anhand der Logs beheben; die Änderungsregeln nicht umgehen.
2. Reale Skalierungs-/Fensterprüfung; UI-Elemente bei Bedarf erneut anordnen.
3. CP-E/CP-F: 100.000-Dateien-Benchmark, echte Miniaturansichten und Skalierungsprüfungen; später Gesamtabnahme.

## Entwicklungsiteration 1 – 17.10.2026

**Referenz:** main `e728d47`; Ausgangs-PR-Head `4b0a57b`; Folge-Commits `f219662`, `fc0216f`, `a4c657f`.

### Konsolidierung / Bestandsabgleich

- Der aktuelle Umbau bleibt in PR #239 (Draft); main und das historische RC24-Releasepaket sind unberührt.
- #239 umfasst am Ausgangsstand 45 geänderte Dateien und 120 Commits: zusammenhängende Bereiche sind Dashboard/Qt, Medienbrowser/Vorschau, SQLite-Index/Watcher, Tests und Dokumentation.
- PR #231 und #232 behandeln denselben alten Autosave-Doppelaufruf und dürfen nicht unabhängig ohne Kollisionsprüfung integriert werden.
- PR #236 und #237 sind reine Planungsdokumentation: als Referenz nutzbar, keine zweite Implementierungsquelle.
- Der dokumentierte Gesamtstatus 97 Prozent bezieht sich ausschließlich auf die ursprüngliche RC24-Evidence, nicht auf eine neu vermessene Fertigstellung von PR #239.
- Die Merge-Sperre ist nachvollziehbar: historisches Release-Manifest 496 Dateien, aktueller PR-Dateibaum erwartet 517. Keine automatische Neudeklaration von RC24 als freigegeben.

### Code und Regression

- Dashboard-Speicherung benutzt die bereits vorhandene zentrale dauerhafte Schreibfunktion `safe_io.atomic_write_json`; eigene Speicherroutine entfernt.
- Neue Tests decken Schreibfehler ohne Zerstörung vorhandener Einstellungen und Nutzung des gemeinsamen Schreibpfads ab.
- Neuer End-to-End-Vertrag auf Befehlsebene: ausdrücklich gewählte Auflösung, Qualität, Effekt und Ausgabeordner bleiben gegenüber einem nachfolgenden Preset erhalten und fließen in den erstellten FFmpeg-Befehl ein.
- Die vorhandenen echten Bild+Ton- und Diashow-FFmpeg-Tests bleiben maßgeblich; der neue Vertragstest ist *kein* neuer physischer Medienlauf.

### Verbindliche Restprüfungen

1. Sämtliche CI-Prüfungen auf dem **neuen finalen Commit** abwarten und eventuelle Fehler beheben. Kein grünes Ergebnis älterer Commits übertragen.
2. Renderpfade für Video, Diashow, Abbruch, Wiederanlauf und Kopierpfad erweitern und auf echten Ausgabedateien kontrollieren.
3. Das Release-Manifest erst für den endgültigen Kandidaten synchronisieren. Historisches RC24-Nachweispaket unverändert lassen.
4. Physische Kubuntu-26.04-/Plasma-/Wayland-Sichtprüfung bei 100, 125, 150 und 200 Prozent bleibt gesondert offen.
5. Kein Merge, keine Stable-Promotion und kein fingierter Benutzer-Abnahmenachweis.

## Entwicklungsiteration 2 – tatsächliche FFmpeg-Ausgaben

**Ausgangs-Commit:** `c58b512f8f2a6c54d6aff0b63e9b36cac3da22a4`.

### Prüfauswertung auf dem Ausgangs-Commit

- Bestanden: PR ancestry guard, Trusted ancestry guard, Release contract sync, CP-09 FFmpeg evidence audit, Qt6 Phase 3 orchestrated validation, Kubuntu 26.04 Wayland preview contract.
- Nicht bestanden: Repository merge preflight / Design manifest contract. Ursache: historisches RC24-Release-Manifest ist noch nicht auf die neuen Entwicklungsdateien zugeschnitten. Dies bleibt bis zur echten Kandidatenfinalisierung eine **bewusste Freigabesperre**.
- Alle Prüfergebnisse gelten **nur** für den jeweils genannten Commit. Keine Übertragung auf spätere Teständerungen.

### Neue echte Medienregression

`tests/test_real_ffmpeg_smoke.py` ergänzt einen vierteiligen, vollständig synthetischen Test:
1. Einzelbild mit Ton, Turbo ohne Bildeffekt.
2. Einzelbild mit Ton, Qualitätsprofil `quality` und `vivid`.
3. Zweibild-Diashow mit Ton, Turbo ohne Bildeffekt.
4. Zweibild-Diashow mit Ton, Qualitätsprofil `quality` und `vivid`.

Die Prüfkriterien sind FFmpeg-Rückgabecode, MP4-Datei, tatsächliche Videoauflösung und vorhandene Audiospur per FFprobe, Dauer, dekodierbare Videoframes und unveränderte SHA-256-Quellhashes. Damit wird die Prüfung über den bloßen FFmpeg-Befehl hinaus ausgedehnt.

**Wichtig:** Die Tests auf dem neuen Commit dürfen erst nach bestätigtem GitHub-Prüflauf als bestanden bezeichnet werden. Die vorhandenen Wiederanlauf- und Retry-Tests verwenden teilweise simulierte Laufzeitergebnisse; echte Systemunterbrechungen bzw. Neustarts bleiben ein separater, offener Integrationsnachweis. Eine Metadaten- und Dekodierprüfung allein beweist nicht die subjektive Stärke oder Sichtbarkeit eines Bildeffekts.

**Freigabe:** weiterhin gesperrt – kein Merge, keine Stable-Promotion, keine erfundene reale Sichtprüfung.
