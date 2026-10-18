# Datei- und Ordnerindex – PROVOWARE VideoBatch

## Für Anfänger
Zuerst den Ordner **01_START_HIER/** öffnen und dort **STARTEN.sh** verwenden.
Im technischen Hauptverzeichnis verbleiben aus Kompatibilitätsgründen notwendige Konfigurations- und Startdateien. Sie dürfen nicht ohne Verweisprüfung verschoben werden.

## Ordner und Aufgaben
- **01_START_HIER/**: einfacher Einstieg.
- **docs/start/**: Start, Installation und Projektstruktur.
- **docs/manuals/**: Entwickler-, Fehler- und Updatehandbuch.
- **docs/archive/rc24/**: historische RC24-Dokumente, keine neue Stable-Freigabe.
- **src/videobatch_fast/**: Programm und Oberfläche.
- **scripts/**: Entwicklung, Bereinigung und Prüfungen.
- **tests/**: automatisierte Tests.
- **registries/**: Dateiindex und Prüf-Registry.
- **diagnostics/**: Protokolle und Nachweise.
- **resources/**: Bilder, Stile und Texte.
- **.github/workflows/**: bestehende CI-Verträge.

## Automatische Aktualisierung
Der maschinenlesbare Index in **registries/PROJECT_FILE_INDEX.json** hält Datei, Pfad, Git-Blob-Inhaltshash, Kategorie, Status und zugeordnete Ordner fest. Er ist kein Freigabebeleg und schließt sich selbst und flüchtige Arbeitsumgebungen aus.

Die Linux-Ereignisüberwachung wird bei Bedarf im Projektstamm gestartet:

    python3 scripts/project_file_index.py --watch

Sie reagiert auf Erstellen, Ändern, Löschen und Umbenennen und gleicht regelmäßig vollständig ab. Es wird ohne ausdrücklichen Start kein Hintergrunddienst eingerichtet.

Ein optionaler Git-Haken wird einmalig im lokalen Klon aktiviert:

    git config core.hooksPath .githooks

Dann wird bei Commits die gestagte Dateistruktur neu erfasst und der Index vorgemerkt. Normale Nutzer benötigen kein Git. Eine reine Überprüfung ohne Schreiben:

    python3 scripts/project_file_index.py --check --git-index

## Prüf-Registry
Die Registry **registries/CHECK_PLANNING_REGISTRY.json** klassifiziert die bestehenden Prüfgruppen und ihre Änderungen. Ein Prüfplan lässt sich beispielsweise erzeugen mit:

    python3 scripts/plan_quality_checks.py --changed docs/start/START_HIER_save_.md
    python3 scripts/plan_quality_checks.py --base main --head HEAD
    python3 scripts/plan_quality_checks.py --base main --head HEAD --final

Nur eindeutig nicht betroffene Prüfgruppen werden als nicht erforderlich für diese Teiländerung ausgewiesen. Die vorhandenen GitHub-Pflichtprüfungen werden nicht deaktiviert. Wiederverwendete Ergebnisse benötigen einen lückenlosen Nachweis gleicher Quell-, Test- und Umgebungsdaten. Schlussabnahmen bleiben verbindlich.

## Regelwerk
1. Statuswörter wie PASS, FERTIG und FREIGEGEBEN gehören nicht als Scheinnachweis in Dateinamen.
2. Status und Abhängigkeiten gehören in Registries, tatsächliche Prüfergebnisse in belegbare Nachweise.
3. Historische RC24-Inhalte bleiben unverändert; die ursprünglichen RC24-Manifestdaten gelten ausschließlich für ihren damaligen Dateibaum.
4. Startskripte, Sperrdateien und Freigabeverträge dürfen nur nach vollständiger Verweis- und Funktionstests verschoben werden.
5. Indexprüfung ist schreibgeschützt; automatische Mutationen beschränken sich auf den ausdrücklich aktivierten Index.
6. Unbekannte Änderungen erzwingen eine strengere Prüfung statt automatischen Überspringens.
7. Physische Kubuntu- und reale Render-Abnahmen dürfen nicht durch einen alten CI-Lauf ersetzt werden.
