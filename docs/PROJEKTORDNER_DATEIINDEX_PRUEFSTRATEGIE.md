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
