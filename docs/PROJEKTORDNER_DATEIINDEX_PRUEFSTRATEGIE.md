# VideoBatch – Ordner, Dateiindex und intelligente Prüfplanung

## Befund und Ziel
Der Repository-Hauptordner enthält mehr als 50 einzelne Dateien. Darunter sind
historische Nachweise, ausführbare Einstiegsskripte und von vielen Quellstellen
referenzierte Vertragsdateien. Eine sofortige physische Verschiebung würde
Startpfade, Paketlisten und Freigaben gefährden.

**Regel:** Zunächst virtuelle Gruppierung im Dateiindex, danach schrittweise
Pfadmigration ausschließlich mit Verbraucherprüfung und Tests.

## Startansicht für Einsteiger
- `STARTEN.sh`: einziger empfohlener Startpunkt.
- `README.md`: erste Hilfe.
- `STATUS.md`: aktueller Stand und offene Abnahmen.

Die sichtbare Zielstruktur lautet `app/`, `config/`, `docs/`,
`development/`, `quality/`, `reports/`, `registries/`,
`resources/` und `release/`. **Dies ist vorerst eine Planstruktur.**
Bestehende Pfade `src/`, `scripts/`, `tests/` und root-Verträge
bleiben erhalten, bis Migrations- und Rückfalltests bestanden sind.

## Dateiindex: ein Register, keine Status-Suffixe
`scripts/project_file_index.py` beobachtet die tatsächlichen Dateien und
verwaltet Größe, SHA-256-Prüfsumme und Fachkategorie. Dadurch erkennt es
hinzugefügte, geänderte und entfernte Dateien. Umbenennungen mit unverändertem
Inhalt werden als solche vermutet; Namensgleichheit oder gleiche Prüfsumme
allein begründet keine Freigabe.

```bash
python3 scripts/project_file_index.py          # einmal aktualisieren
python3 scripts/project_file_index.py --watch  # alle 5 Sekunden aktualisieren
python3 scripts/project_file_index.py --json   # maschinenlesbare Änderungsliste
```

Die Ausgabe befindet sich außerhalb des Projekts unter
`~/.local/state/videobatch/project_index/` (oder `XDG_STATE_HOME`).
Dadurch verursachen Indexaktualisierungen keine zusätzlichen Git-Änderungen
und keinen sich selbst aktualisierenden Release-Manifest-Kreislauf.

**Trigger-Regel:** Bei aktivem `--watch` werden Änderungen spätestens im
nächsten Prüfintervall entdeckt; ohne laufenden Wächter wird der Index bei
expliziter Ausführung neu erstellt. Änderungen durch externe Werkzeuge lassen
sich ohne aktivierten Wächter nicht augenblicklich erkennen.

## Prüfungen ohne Qualitätsverlust
`test.sh --docs` für reine Dokumentation. Für Codeänderungen zunächst
`test.sh --core`; GUI- und Integrationspfade erfordern zusätzliche
`test.sh --local` und echte Sicht-/Medienprüfung.

Ein Prüfungsergebnis darf nur wiederverwendet werden, wenn **Commit,
vollständiger relevanter Quellen-Hash, Umgebung, Prüfbefehl und Testversion**
identisch sind und das Ergebnis nachweislich erfolgreich ist. Der neue Index
enthält deshalb nur eine **Empfehlung** und setzt keine Prüfschritte automatisch
auf PASS. Ein fehlender, veralteter oder beschädigter Prüfstatus bedeutet:
erneut prüfen. Keine Freigabe aufgrund von Dateinamen, Zeitstempeln oder
einem bloß grünen Hinweis.

## Nicht einsparbar
- Verpflichtende CI-Prüfungen und Code-Sicherheitsgates für einen neuen Commit.
- Signatur-, Paketintegritäts- und Release-Manifestprüfung.
- Reale Kubuntu/Plasma/Wayland-Sichtprüfung nach UI-Änderungen.
- Realer Langzeit-/Abbruch-/Wiederanlauf-Test vor Release.
- Freigabeentscheidung auf dem **unveränderten** Kandidaten.

## Migration der technischen Root-Dateien
1. Reale Leser und Schreiber je Datei über Quellcode-Suche und Paketlisten ermitteln.
2. Root-Dateien zunächst nach Kategorie im Index dokumentieren.
3. Kleine Gruppe nur bei bestandenen Tests verschieben und ihre Verbraucher
   gemeinsam umstellen; alte Startskripte als kompatible Einstiegspunkte lassen.
4. Historische Release-Nachweise nicht umschreiben; neue Entwicklungsstände
   separat dokumentieren.
5. Erst nach erfolgreicher Kubuntu-Abnahme die reduzierte Startansicht finalisieren.

Die Datei `registries/PROJECT_FILE_POLICY.json` definiert die minimalen
Registrierungs- und Schutzregeln maschinenlesbar.

## Physische Teilmigration: erster sicherer Block
`DEVELOPER_GUIDE.md`, `UPDATE_SYSTEM.md` und `CHANGELOG.md` wurden
mit unveränderten Git-Blobs in `docs/` verlagert. Der Dokumentationsindex,
die Klassifikation und betroffene Nutzerverweise wurden gleichzeitig
angepasst. Die historisch freigegebenen `_save_`-Dateien, Startskripte
und kanonischen technischen Verträge bleiben bis zur gesonderten und
nachgewiesenen Migration an ihrem Ort. Die Stable-Freigabe bleibt gesperrt.

## Verbindliches Entwicklungs-Prüfregister (PR #244)
Das vollständige lokale Register liegt unter
`registries/TEST_EVIDENCE_POLICY.json`; sein ausführbarer Verwalter unter
`scripts/test_evidence_registry.py`. Das Werkzeug startet **nur explizit
hinterlegte** kurze Python-Prüfungen, zeichnet ihr echtes Ergebnis auf und
verwendet ausschließlich bei identischem, sauberem Git-Commit,
Dateibaum-Fingerabdruck, Python-/Paketumgebung und Prüfbefehl ein bereits
bestandenen Nachweis.

```bash
python3 scripts/test_evidence_registry.py list
python3 scripts/test_evidence_registry.py run file_index
python3 scripts/test_evidence_registry.py run docs_validation --reuse
python3 scripts/test_evidence_registry.py check docs_validation
```

Ohne `--reuse` wird stets ausgeführt. Bei schmutziger Arbeitskopie, fehlendem
Git, veränderten Eingaben während der Prüfung, geänderter Umgebung oder
fehlendem Ergebnis wird **nicht** wiederverwendet. Lokale Nachweise befinden
sich außerhalb des Repositories unter `XDG_STATE_HOME/videobatch/test_evidence/`.
**Wichtig:** `test.sh`, vorgeschriebene GitHub-CI-Prüfungen,
`verify_release.sh`, Sicherheit, Paketintegrität und reale Kubuntu-Abnahme
werden nie automatisch übersprungen.

Der gesetzliche beziehungsweise technische Dateistatus ist **nicht** Teil
eines Dateinamens. Technische Fehler in einem Test werden protokolliert,
niemals zu einem grünen Freigabestatus umgedeutet.

### Automatische Migrationsprüfung
```bash
python3 scripts/project_file_index.py --audit-migration --json
```
Die Prüfung kontrolliert originale Git-Blobs, Ordnerklassifikation und
verbliebene Codeverweise auf alte Root-Dateipfade. Positive Ergebnisse sind
keine Freigabe von CI-, Signatur- oder Releaseprüfungen.

## Verschärfung des Nachweisregisters
Wiederverwendbare Einträge müssen neben identischem Commit, Quellenstand,
Umgebung und Testdefinition auch einen **tatsächlich protokollierten
Exit-Code 0**, `reuse_allowed=true` und einen gültigen Abschlusszeitpunkt
enthalten. Fehlt ein Feld, wird erneut geprüft. Der Hinweis darf niemals
eine echte Releasefreigabe ersetzen.

## Aktueller Stand der physischen Bereinigung
Die ersten drei Dokumente wurden nachweisbar verschoben. Weitere Root-Dateien
sind teils historisch eingefrorene Nachweise oder zentrale Verträge:
Deshalb werden sie **nicht auf Verdacht verschoben**. Für jeden weiteren
Umzug ist eine aktualisierte Liste der Verbraucher und ihrer Pfadbezüge
Voraussetzung, einschließlich Shell-Skripten und des Release-Dateivertrags.
