# Welle 25 – UI Phase 1: Project Home Dashboard

## Ziel

Die im freigegebenen Musterbild festgelegte Startaufteilung wird als reale Tk/X11-Oberfläche in PROVOWARE VIDEO AUTOMATION umgesetzt, ohne die vorhandenen Produktions-, Recovery-, Scheduler- oder Release-Funktionen zu ersetzen. Phase 1 bleibt bewusst leer: Nur allgemeine Informationen, Grundeinstellungen und Navigation sind aktiv.

## Umgesetzte Aufteilung

1. Kopfbereich mit Produktname, Schrittbezeichnung und Hilfe.
2. Vier gleichgewichtete Hauptkacheln: Projektbasis, Medienquellen, Automationsregeln, Render & Export.
3. Zwei breite Mittelkarten: Infodashboard und Tipps.
4. Vier bewusst leere Ausbauflächen: Quellenübersicht, Workflow-Module, Render-Profile, Historie / Logs.
5. Vier Grundeinstellungsaktionen: Allgemeine Einstellungen, Projektregeln, Benachrichtigungen, Systempfade.
6. Footer mit Claim und drei Schriftgrößenstufen.

## Integrationsstrategie

Die neue Startseite liegt als Overlay über der vollständig aufgebauten kanonischen Arbeitsoberfläche. Dadurch bleiben alle bisherigen Module erhalten und können über die neuen Kacheln geöffnet werden. Die Sidebar-Aktion Dashboard führt zurück auf die neue Startseite. So kann die Oberfläche iterativ migriert werden, ohne bestehende Fachlogik zu duplizieren oder abzuschneiden.

## Leere-Felder-Vertrag

Die vier unteren Ausbauflächen enthalten in Phase 1 ausschließlich Titel, Platzhalter-Icon, „Noch leer“ und „Für spätere Inhalte“. Sie enthalten bewusst keine Treeviews, Notebook-Unterseiten oder versteckte Fachinhalte.

## X11-Abnahme dieser Entwicklungsstufe

Der reale Tk-Aufbau wurde automatisiert unter Xvfb/X11 mit 1500×920 gestartet und als Screenshot kontrolliert. Die Startseite baut innerhalb der bestehenden Ready-Handshake-Kette fehlerfrei auf. Dieser interne Screenshot ersetzt ausdrücklich nicht die weiterhin offene physische KDE-X11-Stable-Abnahme.

## Qualitätsgrenzen

- Die neue Datei `project_home_dashboard.py` bleibt unter der Architekturgrenze.
- Die bestehende Fachlogik bleibt unangetastet unter der neuen Startschicht erreichbar.
- Die neue Startschicht ist als reine Tk/UI-Datei aus dem Business-Coverage-Scope ausgeschlossen; Fachmodule bleiben vollständig im Coverage-Vertrag.
- Dashboard-Navigation, Hilfe und Schriftgrößensteuerung verwenden bestehende geprüfte Funktionen statt paralleler Implementierungen.

## Nächster iterativer UI-Schritt

Die vier leeren Ausbauflächen werden einzeln und nacheinander mit realen Projektfunktionen befüllt. Zuerst sollte „Quellenübersicht“ die vorhandene Medienbibliothek in die neue Kartensprache überführen; die übrigen drei Felder bleiben dabei weiterhin leer.
