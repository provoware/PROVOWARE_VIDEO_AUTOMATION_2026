# Implementierungsbericht 2.6.0-rc1

## Auftrag
Drei fehlerreduzierende Empfehlungen vollständig umsetzen:

1. Arbeitsbereich visuell absichern
2. Kalendertage mit Notizen verbinden
3. Plugin-Berechtigungen vor Aktivierung sichtbar machen

## Umsetzung

### Visuelle Arbeitsbereichsprüfung
Vier neue deterministische Szenarien wurden ergänzt. Jedes Szenario erzeugt eine echte Tk-Oberfläche unter Xvfb, befüllt sie mit reproduzierbaren Testmedien und prüft Pflichttexte, Fenstergrenzen sowie die Bildabweichung zur freigegebenen Referenz.

### Kalendernotizen
Das Projektschema wurde auf Version 2 erhöht. `calendar_notes` speichert Notiz, Typ und Farbstatus. Alte reine `calendar_marks` werden automatisch migriert. Ungültige Typen, Farben und überlange Texte werden sicher normalisiert.

### Plugin-Berechtigungen
`plugin_permissions.py` erzeugt aus der Registry eine laienlesbare Berechtigungsübersicht. Der Sandbox-Test startet erst nach expliziter Bestätigung. Die Entscheidung und das Resultat werden strukturiert protokolliert.

### Layoutkorrektur
Die bisher getrennt gepackten oberen und unteren Arbeitsbereiche wurden in einen vertikalen Splitter überführt. Dadurch bleiben Zuordnung, Fortschritt und Produktionsmonitor auch in den Referenzansichten sichtbar.

## Ergebnis

- 70 automatisierte Tests bestanden
- 8 visuelle Referenzszenarien bestanden
- 12 Anwendungssimulationen bestanden
- Registry- und Architekturprüfung bestanden
