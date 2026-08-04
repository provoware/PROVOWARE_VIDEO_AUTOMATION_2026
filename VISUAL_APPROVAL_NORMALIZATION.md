# Normalisierte visuelle Freigabe

## Ziel

Eine erneute identische Screenshotprüfung darf die Freigabe nicht allein wegen Zeitstempeln, Pfaden oder gering schwankenden Messwerten ungültig machen.

## Signaturrelevant

- Build und Manifestversion
- Szenarioverträge
- Pflichttexte und Farben
- Auflösungen und Zoomstufen
- Pass-/Fail-Status
- Baseline-Bundle
- normalisierter Prüfbericht

## Nicht signaturrelevant

- Erzeugungszeit
- lokale Pfade
- aktuelle Screenshotpfade
- Differenzbildpfade
- Pixelmittelwert
- dHash-Abstand
- beschreibende Laufzeitmeldungen

Die ausgeschlossenen Werte bleiben im Manifest und HTML sichtbar.
