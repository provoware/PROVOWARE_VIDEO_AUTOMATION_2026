# Implementierungsbericht 2.7.0-rc1

## Umgesetzt

### Widerrufbare Plugin-Freigaben
Freigaben speichern Version, signierten Inhalts-Hash, Signaturschlüssel, Capability, Berechtigungs-Hash, sichtbare Berechtigungen und Freigabedatum. Jede Identitätsänderung setzt den Status automatisch auf `expired`. Eine aktive Freigabe kann im Berechtigungsdialog ausdrücklich widerrufen werden.

### Kalender-Aufgabenübersicht
Kalendernotizen sind zusätzlich als separate, filterbare Liste verfügbar. Die kompakte Monatsansicht bleibt unverändert.

### Dialog-Regression
Update-Assistent, Dateiablage, Plugin-Berechtigung und Recovery besitzen eigene wiederverwendbare Dialogkomponenten und feste visuelle Baselines.

### HTML-Prüfoberfläche
Ein Offline-HTML-Dashboard verbindet Szenarien, Referenzen, Ist-Bilder, Differenzen, Status und JSON-Manifeste.

### Zusätzlich behobener Layoutbefund
Die strengere Sichtbarkeitsprüfung erkannte, dass Dateiauswahlaktionen bei 1366×768 unterhalb des sichtbaren Notebookbereichs lagen. Die Hauptaktionen wurden in eine dauerhaft sichtbare Dateikopfzeile verschoben und die vertikale Arbeitsbereichsaufteilung kompakter gestaltet.
