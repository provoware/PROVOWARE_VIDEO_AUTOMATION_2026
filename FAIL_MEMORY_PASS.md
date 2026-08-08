# FAIL_MEMORY_PASS

## Pflichtablauf jeder Folge-Iteration

1. Diese Datei vor Analyse, Planung oder Änderung vollständig lesen.
2. Genau einen klar abgegrenzten offenen Punkt auswählen.
3. Ziel, betroffene Dateien, Risiken und bewusste Nicht-Änderungen festhalten.
4. Den kleinsten vollständigen Patch umsetzen.
5. Syntax, Logik, Fehlerpfade, Dokumentation und betroffene Regressionen prüfen.
6. Ergebnisse, neue Erkenntnisse und Restpunkte hier aktualisieren.

## Kurzzeitgedächtnis – abgeschlossene RC24-Finalisierung

### Ziel

Das Repository für `2.8.3-rc24` konsolidieren, reale Schwachstellen beheben, freigabefähige Unterlagen eindeutig kennzeichnen und unfertige Stable-Nachweise sichtbar getrennt halten.

### Umgesetzt

- 323/323 automatisierte Tests unter deterministischem X11 bestanden
- Text-, Versions-, Dokument-, Release-Datei- und Manifestverträge bestanden
- interne Qualitätsprüfung: 203 Python-Dateien, 1.602 Funktionen, maximale Komplexität 29, 0 Befunde
- Statement-/Zeilenabdeckung 82,43 %, Branch-Abdeckung 67,21 %
- FFmpeg-7-kompatible atomare PNG-Erzeugung ergänzt
- beschädigte oder zu kleine Vorschau-Cacheziele werden vor einem Neuaufbau sicher entfernt
- Vorschau-Cache auf 1 GiB und 2.000 eigene PNG-Dateien begrenzt
- pro Cache-Schlüssel arbeitende Erzeugungssperre aktiv
- Diagnose, sichere Leerung, verständliche Hilfetexte und bildschirmgebundene Tooltips ergänzt
- 56 historische RC-Nachweise nach `docs/archive/release-history/` verschoben
- 16 doppelte alte visuelle Baselines entfernt
- zehn eigenständige freigabefähige Unterlagen tragen `_save_`
- acht bewusst unfertige Stable-Nachweise stehen in `RELEASE_FILE_STATUS.json`, README und STATUS
- temporäre Audit-, Payload- und Transformationsdateien vollständig entfernt

### Bewusst nicht behauptet

`2.8.3-rc24` bleibt ein Release Candidate. Stable ist nicht freigegeben.

## Dauerhafte Schutzregeln

- `_save_` nur für eigenständige Nutzer- und Releaseunterlagen verwenden; Module, Workflows, Manifeste, Einstiegsskripte und README behalten stabile technische Namen.
- Cachebereinigung darf niemals Originalmedien, Projektdateien oder fremde Dateien anfassen.
- Generierte Dateien atomar bereitstellen; keine halbfertigen Ergebnisse unter endgültigem Namen veröffentlichen.
- GUI-Threads dürfen keine FFmpeg-, Bilddekodierungs- oder Verzeichnisbereinigungsarbeit ausführen.
- Releaseberichte, Statusdateien und Manifeste dürfen keinen höheren Reifegrad behaupten als die Nachweise tragen.
- Historische Nachweise archivieren statt löschen; aktive Build- und Portable-Pakete müssen das Archiv ausschließen.
- Test- und Compile-Caches vor Release- und Dateibaumprüfungen entfernen.
- Stable niemals aus Teiltests oder einer grünen Ubuntu-Matrix ableiten.

## Fehlerwissen

### Behoben

- FFmpeg 7 konnte das Ausgabeformat einer atomaren Datei mit `.partial`-Endung nicht zuverlässig ableiten; PNG-Format und Codec werden nun explizit gesetzt.
- Ein beschädigtes oder unterschrittenes Cacheziel konnte nach fehlgeschlagenem Neuaufbau liegen bleiben; ungültige Ziele werden nun vor der Erzeugung entfernt.
- Tooltips konnten sofort erscheinen, den Bildschirmrand überschreiten oder beim Fokuswechsel hängen bleiben; Verzögerung, Fokusführung, Randbegrenzung und `TclError`-Schutz sind zentralisiert.
- Historische Berichte, doppelte Baselines und temporäre Auditdateien belasteten den aktiven Projektstamm; sie wurden archiviert oder vollständig entfernt.
- Das Projektgedächtnis nannte eine alte 256-MiB-Grenze und eine bereits umgesetzte Sperre als offen; dieser Stand ist korrigiert.

### Noch zu beobachten

- reale Langzeitmessung mit mehreren tausend Medien auf langsamem externem Datenträger
- physische KDE-X11-Abnahme auf den Zielsystemen
- vollständige Ausführung der exakt gepinnten Ruff-, MyPy-, Bandit- und pip-audit-Werkzeuge

## Aktuelle offene Stable-Gates

1. Ruff `0.16.1`
2. MyPy `2.3.0`
3. Bandit `1.9.4`
4. pip-audit `2.10.1`
5. physische KDE-X11-Abnahme
6. dokumentierter Langzeitrender mit großer Medienauswahl und langsamem externem Ziel

## Nächster bevorzugter Entwicklungspunkt

Die exakt gepinnte Offline-Qualitätswerkzeugkette vollständig ausführen und nur konkrete, reproduzierbare Befunde als kleine Folgepatches bearbeiten.

## Alternative mit hohem Nutzen und geringem Risiko

Den dokumentierten Langzeitrender als rein lesenden Abnahmejob mit festen Zeit-, Ressourcen- und Abbruchgrenzen vorbereiten, ohne Stable vorzeitig freizugeben.
