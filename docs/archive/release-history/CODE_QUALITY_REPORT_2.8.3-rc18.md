# Code-Qualitätsbericht 2.8.3-rc18

## Ergebnis

- 227/227 Python-Tests bestanden
- 81,34 % Zeilenabdeckung bei Mindestwert 80 %
- 66,02 % Branch-Abdeckung bei Mindestwert 65 %
- 12/12 Anwendungssimulationen bestanden
- 16/16 visuelle Referenzszenarien bestanden
- 0 Registrybefunde
- 0 Architekturbefunde
- 0 interne Qualitätsbefunde
- maximale Funktionskomplexität: 28 bei Grenze 30
- größte Python-Datei: `ui.py` mit 684 Zeilen bei Grenze 700

## RC18-Schwerpunkte

- stabile Hauptnavigation über sechs vollflächige Tabs
- keine Wiederherstellung alter verschachtelter Splitterpositionen
- individueller Zoom je Hauptbereich
- große Medien- und Audioauswahl mit Vorschau, Sortierung und Downloads-Startordner
- Menüleiste und Tastaturkürzel
- benutzereigene Installation ohne `sudo`
- automatische Quarantäne oder Ausweichpfade bei unbrauchbaren Installationsordnern
- Regressionstests für Berechtigungen, Tabs, Medienauswahl und Zoomzustände

## Coverage-Abgrenzung

Reine Tk-Oberflächenmodule und der große Medienauswahldialog werden über GUI-, Visual- und Quellverträge geprüft und nicht in die Kern-Coverage eingerechnet. Berechtigungsdienst, Konfiguration, Dateisicherheit, Runner, Updates und Recovery bleiben Bestandteil der Branch-Coverage.
