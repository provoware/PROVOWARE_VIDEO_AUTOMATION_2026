# Recovery-Audit – Fortsetzungswelle 9

Stand: 2026-08-07

## Ergebnis

Welle 9 erweitert die bestehende atomare Persistenz um prozessuebergreifende Schreibserialisierung und Restart-Bereinigung nach harten Prozessabbruechen. Das zerstoerungsfreie Fehlerlabor umfasst nun 21 reproduzierbare Szenarien; 21/21 bestanden.

## Neu implementierte Schutzmechanismen

1. `exclusive_file_lock()` serialisiert kooperierende Backup-Mutationen unter Linux/POSIX via `flock` mit harter Timeout-Grenze. Eine haengende Instanz kann dadurch keine unbegrenzte Warteschleife ausloesen; nach Prozess-Tod gibt der Kernel die Sperre frei.
2. Atomare Tempdateien tragen die PID des Erzeugerprozesses. Vor einem neuen atomaren Schreiben werden Temp-Artefakte nachweislich toter Prozesse entfernt. Tempdateien einer lebenden PID werden nie geloescht; alte Legacy-Tempnamen werden nur nach einer Sicherheitswartezeit entfernt.
3. `create_project_backup`, Rotation und History-Self-Healing verwenden denselben Backup-Lock. Zwei parallele Sicherungsprozesse verlieren dadurch weder Archiv noch Historieneintrag.
4. ENOSPC wird nicht nur am `replace`, sondern auch beim Datei-`fsync` getestet. Der letzte gueltige Zielzustand bleibt erhalten.
5. EACCES vor Tempdateierzeugung wird explizit getestet; der bestehende Zielzustand bleibt unveraendert.
6. Beschädigte `history.json` wird beim Wiederanlauf aus erneut verifizierten Archiven rekonstruiert.
7. Read-only-Ausgabeziele werden weiterhin vor Renderstart erkannt und blockiert.

## Recovery-Invarianten

- Kein fehlgeschlagener Schreibpfad darf eine gueltige Zieldatei durch einen Teilzustand ersetzen.
- Atomare Umschaltung erfolgt erst nach erfolgreichem Schreiben und Datei-`fsync`; danach wird das Verzeichnis synchronisiert.
- Ein Prozess-Kill darf weder dauerhafte Locks noch unkontrollierte Tempdatei-Ansammlung erzeugen.
- Parallelitaet darf die Backuphistorie nicht durch Lost Updates beschaedigen.
- Recovery vertraut nicht blind der Historie, sondern verifiziert die Archive selbst.
- Rotationen loeschen weiterhin nur verifizierte VideoBatch-eigene Archive.

## Externe technische Grundlage

- Python `tempfile.mkstemp()` erstellt Tempdateien race-resistent und verlangt bei Low-Level-Verwendung explizite Bereinigung: https://docs.python.org/3/library/tempfile.html
- Linux `fsync(2)` synchronisiert Dateiinhalt und Metadaten; fuer dauerhafte Verzeichniseintraege ist zusaetzliche Directory-Synchronisation erforderlich: https://man7.org/linux/man-pages/man2/fsync.2.html
- Linux `rename(2)` ersetzt ein bestehendes Ziel atomar, sodass Leser keinen Zwischenzustand mit fehlendem Ziel sehen: https://man7.org/linux/man-pages/man2/rename.2.html
- NIST SP 1339 (2026) fordert regelmaessige Backups, Tests und Review in Recovery-Uebungen: https://csrc.nist.gov/pubs/sp/1339/final
- NIST Contingency Planning behandelt Recovery-Verfahren, Tests und fortlaufende Pflege als zusammenhaengenden Resilienzprozess: https://csrc.nist.gov/topics/security-and-privacy/security-programs-and-operations/contingency-planning

## Abgrenzung

Die Tests simulieren Host-Fehler zerstoerungsfrei oder erzeugen sie ausschliesslich in temporaeren Testbereichen. Ein echter physischer Stromausfall, Hardware-Controller-Cachefehler, defektes Laufwerk oder ein reales vollgelaufenes Produktionsdateisystem wird nicht behauptet. Diese Faelle gehoeren in eine spaetere physische Soak-/Recovery-Abnahme.
