# VideoBatch Fast 2.8.3-rc24 hochladen

## Nur zwei Aktionen nötig

1. Oben rechts **Add file → Upload files** wählen.
2. Die geprüfte RC24-ZIP in das große Upload-Feld ziehen und unten **Commit changes** anklicken.

Die ZIP darf ihren vorhandenen Dateinamen behalten, beispielsweise:

`VideoBatch_Fast_2.8.3-rc24(3)(1).zip`

## Danach vollständig automatisch

GitHub prüft vor jeder Änderung:

- genau eine ZIP im Ordner `incoming`
- Dateigröße `4.013.380 Bytes`
- SHA-256 `c54c19141f4d08fbb19f6f38e40ce06c589a86725b988864ad8e22f28ad7501a`
- fehlerfreie ZIP-Struktur
- Version und Manifest `2.8.3-rc24`
- exakt 396 Projektdateien

Erst danach werden Manifestprüfung und 274 Tests ausgeführt. Nur bei vollständigem Erfolg wird `main` atomar durch RC24 ersetzt, der unveränderliche Tag `videobatch-fast-2.8.3-rc24` erstellt, die ZIP dem Release beigefügt und Issue #11 geschlossen.

Bei einem Fehler bleibt der bisher veröffentlichte Projektstand unverändert und Issue #11 erhält eine verständliche Diagnose.

> Wichtig: Die ZIP nicht entpacken und keine zweite ZIP gleichzeitig in diesen Ordner laden.
