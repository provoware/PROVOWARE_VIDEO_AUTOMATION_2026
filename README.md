<!-- release-status:start -->
# provoware - videoautomation - 2026 · 2.8.3-rc24

**Kanal:** rc
**Kanonische Quelle:** `diagnostics/release_readiness/RELEASE_EVIDENCE.json`
**Freigegebener Qualitätsbericht:** `VideoBatch_Fast_2.8.3-rc24_BUILD_REPORT_save_.json`

- 323/323 automatisierte Tests bestanden
- 82.43 % Zeilenabdeckung
- 67.21 % Zweigabdeckung
- 18/18 visuelle Szenarien bestanden
- Release-Manifest: 365 Dateien
- Kubuntu-CI-Matrix: 4/4 Kombinationen bestanden

### Offene Stable-Gates

- Physische KDE-X11-/Wayland-Abnahme: Reale Zielsystem-Abnahme fehlt; die CI-Matrix ist nur deterministisch/headless
- Langzeitrender mit großer Medienauswahl: Realer Lauf auf langsamem externem Ziel fehlt
<!-- release-status:end -->

<!-- release-files:start -->
## Release-Dateistatus

Only standalone user and release deliverables receive _save_. Source modules, CI workflows, canonical manifests, entrypoints and README retain stable technical names.

| Releasefertig (`_save_`) | Noch nicht releasefertig |
|---|---|
| `START_HIER_save_.md`<br>Schnellstart: Geprüfter Nutzerstart und sichere erste Schritte | `TODO.md`<br>Offene Arbeitsliste: Enthält bewusst die verbleibenden Stable-Gates |
| `AUTOINSTALLATION_save_.md`<br>Installationsanleitung: Benutzerpfade, A/B-Slots und Berechtigungsschutz dokumentiert | `STABLE_GATE_ITERATION_2.8.3-rc24_2026-08-04.md`<br>Stable-Freigabeiteration: Stable-Freigabe ist ausdrücklich noch blockiert |
| `PROJEKTORDNERSTRUKTUR_save_.md`<br>Projektübersicht: Ordner, Start, Sicherheit und Funktionen beschrieben | `docs/LONG_RENDER_2.8.3-rc24.md`<br>Langzeitrender: Realer Langzeitrender mit großer Auswahl und langsamem Ziel fehlt |
| `RELEASE_NOTES_save_.md`<br>Releasehinweise: Aktueller RC24-Funktionsstand dokumentiert | `docs/STABLE_ACCEPTANCE_EVIDENCE.md`<br>Stable-Abnahmenachweis: Physische Desktop- und Langzeitnachweise fehlen |
| `TEST_REPORT_save_.md`<br>Testbericht: Automatisierte und offene Prüfungen getrennt ausgewiesen | `VISUAL_DESKTOP_APPROVAL.md`<br>Desktop-Sichtprüfung: Physische KDE-X11-/Wayland-Abnahme bleibt offen |
| `FRESH_PACKAGE_REPORT_save_.md`<br>Paketbericht: Saubere Paketprüfung für RC24 dokumentiert | `VISUAL_INSPECTION_MANIFEST.json`<br>Visuelles Prüfmanifest: Aktueller physischer Lauf ist nicht vollständig bestätigt |
| `CODE_QUALITY_REPORT_2.8.3-rc24_save_.md`<br>Codequalitätsbericht: Interne Qualitätsprüfung ohne Befund | — |
| `QUALITY_GATE_REPORT_2.8.3-rc24_save_.md`<br>Exakter Offline-Qualitätsbericht: Ruff, MyPy, Bandit und pip-audit vollständig bestanden | — |
| `IMPLEMENTATION_REPORT_2.8.3-rc24_save_.md`<br>Implementierungsbericht: Umgesetzte Funktions- und Sicherheitsverträge dokumentiert | — |
| `FINAL_AUDIT_2.8.3-rc24_save_.md`<br>RC-Abschlussaudit: RC-Gates und offene Stable-Gates ehrlich getrennt | — |
| `VideoBatch_Fast_2.8.3-rc24_BUILD_REPORT_save_.json`<br>Maschinenlesbarer Buildbericht: Aus der kanonischen RELEASE_EVIDENCE.json erzeugt | — |
<!-- release-files:end -->

**Ausgabe vor Stable:** immer als vollständiges Projekt-ZIP. Teil- und Onlineupdates bleiben bis nach der Stable-Freigabe ein deaktivierter Nachrelease-Mechanismus.

## Zentrale Verbesserungen

- interaktive Fehlerlösung mit konkreten Aktionsschaltern
- sicherer Ausgabe- und Projektordner kann direkt aus dem Lösungsfenster erstellt werden
- automatische Reparatur vergessener oder ungültiger Schnellmodus- und Pfadeinstellungen
- intelligenter Wechsel zum Diashowmodus bei ungleichen Audio-/Bildmengen
- korrigierte Vorschau bei Mehrfachauswahl: maßgeblich ist der zuletzt aktiv angeklickte Eintrag
- mehrere Auswahlrunden im selben Ordner über „Auswahl übernehmen + im Ordner bleiben“
- bereits übernommene Dateien werden in der Liste sichtbar markiert
- globale Headerstatistik mit Audio-, Bild-, Video- und Auftragszahl sowie Modus, Übergang, Szenenkopplung und Schnellprofil
- Lösungsdialoge mit dauerhaft erreichbaren Aktionen; lange Erklärungen und technische Details sind scrollbar
- dauerhafter Thumbnail-Datenträgercache mit 1-GiB-/2.000-Dateien-Grenze, LRU-Bereinigung und atomarer Speicherung
- Cache-Diagnose direkt in der Medienauswahl mit Größe, Anzahl, Auslastung, Pfad und letzter Bereinigung
- sichere manuelle Leerung ausschließlich eigener VideoBatch-Vorschaudateien
- pro Cache-Schlüssel arbeitende Erzeugungssperre gegen doppelte parallele FFmpeg-Berechnungen

## Dauerhafter Thumbnail-Datenträgercache

Vorschaubilder werden unter dem XDG-Benutzercache gespeichert und bei erneutem Öffnen wiederverwendet. Der Cache wächst nicht unbegrenzt: Standardmäßig gelten maximal 1 GiB und 2.000 VideoBatch-PNG-Dateien. Bei Überschreitung werden zuerst die am längsten nicht verwendeten Einträge entfernt. Originalmedien, Projektdateien, fremde PNGs und andere Dateitypen werden niemals gelöscht.

Der Cache-Schlüssel berücksichtigt Quellpfad, Änderungszeit, Dateigröße und gewünschte Breite. Eine geänderte Quelldatei erhält deshalb automatisch eine neue Vorschau. Neue Vorschaubilder werden zunächst als Teil-Datei erzeugt und erst nach erfolgreicher Prüfung atomar unter dem endgültigen Namen veröffentlicht.

### Cache-Diagnose und Bedienung

In der Bilder- und Videoauswahl steht der Schalter **„Vorschau-Cache“** bereit. Der Dialog zeigt:

- aktuelle Anzahl der Vorschaubilder
- belegten Speicher und 1-GiB-Grenze
- maximale Dateianzahl
- prozentuale Auslastung
- letzten Bereinigungslauf
- vollständigen Cachepfad

Der Schalter **„Vorschau-Cache leeren“** fordert zuerst eine Bestätigung an. Entfernt werden ausschließlich eindeutig benannte VideoBatch-Vorschaubilder und veraltete eigene Teildateien. Aktuell erzeugte oder verwendete Schlüssel werden über eine kurze Sperrprüfung geschützt. Originalmedien, Projekte und fremde Dateien bleiben unangetastet.

### Parallele Vorschauanfragen

Für jeden Cache-Schlüssel existiert eine eigene Erzeugungssperre. Fordern zwei Threads oder Kubuntu-Prozesse gleichzeitig dieselbe Vorschau an, startet FFmpeg nur einmal. Der wartende Aufruf verwendet anschließend das vollständig erzeugte Cachebild. Unterschiedliche Cache-Schlüssel können weiterhin parallel verarbeitet werden. Das vorhandene atomare Speicherprinzip bleibt unverändert bestehen.

## Fortschritt der aktuellen Folge-Iteration

**Fortschritt:** 100 % für den abgegrenzten Funktionspatch „Cache-Diagnose, 1 GiB und Schlüssel-Sperre“.

**Erledigt:** Cachegrenze auf 1 GiB erhöht, Statusfunktion ergänzt, Bedienoberfläche in die Medienauswahl integriert, sichere Leerung ergänzt, fremde PNGs zusätzlich geschützt, letzter Bereinigungslauf protokolliert, parallele identische FFmpeg-Erzeugung serialisiert und fokussierte Regressionstests erweitert.

**Offen:** Stable-Gates bleiben unverändert offen; keine physische KDE-Abnahme und kein Langzeitrender wurden in dieser Iteration durchgeführt.

## Sicheres Berechtigungskonzept

VideoBatch arbeitet ohne pauschale Rootrechte, `chmod 777` oder rekursive Besitzänderungen. Schreibziele werden durch reale Schreibproben geprüft. Bei Problemen kann der Nutzer:

1. einen neuen Benutzerordner anlegen,
2. einen anderen Ordner auswählen,
3. einen geprüften Standardordner verwenden,
4. den betroffenen optionalen Schritt für diesen Lauf deaktivieren.

Originaldateien und bestätigte Projektzustände bleiben bei Fehlern unverändert.

## Bedienablauf

1. Audios und Medien auswählen.
2. Auswahlstatistik im Header kontrollieren.
3. Bei Bildern und Videos optional **„Vorschau-Cache“** öffnen und Status prüfen.
4. Modus und Einstellungen wählen oder die Automatik verwenden.
5. Produktion starten.
6. Fehlende Angaben werden automatisch ergänzt oder mit direkten Lösungsaktionen abgefragt.
7. Bei Unsicherheit zuerst `PROJEKTORDNERSTRUKTUR_save_.md` öffnen und die Schritt-für-Schritt-Anleitung nutzen.

## Laienfreundliche Projektübersicht

Die Datei `PROJEKTORDNERSTRUKTUR_save_.md` erklärt Ordner, wichtige Dateien, sichere Startbefehle, Funktionsbereiche, Barrierefreiheitsprinzipien und sinnvoll mitlieferbare Basisabhängigkeiten in einfacher Sprache.
