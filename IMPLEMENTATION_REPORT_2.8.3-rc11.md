# Implementierungsbericht 2.8.3-rc11

## Ziel

Die Startroutine bestätigt erstmals technisch, dass die Hauptoberfläche tatsächlich aufgebaut wurde. Ein erfolgreicher Prozessstart allein gilt nicht mehr als Erfolg.

## Umgesetzt

1. UI-Bereitschaftshandshake mit atomarer Markierung.
2. Startaufsicht mit Zeitlimit und Protokollierung der Anwendungsausgabe.
3. Automatischer zweiter Startversuch mit neutraler Konfiguration und neutralem Projekt.
4. Verifizierter System-Python-Rückfall, wenn die isolierte Laufzeit nicht aufgebaut werden kann.
5. Automatische Reparatur verlorener oder beschädigter Laufzeit-Bereitschaftsmarken.
6. Zweitstart aktiviert das bereits laufende Fenster statt einen Fehler auszugeben.
7. Startprüfung meldet Einschränkungen als `degraded` oder `warning`, blockiert die Oberfläche aber nicht.
8. Sichtbare Startstatus-Pills für bereit, eingeschränkt und sicherer Startmodus.

## Sicherheitsgrenzen

- Der System-Python-Rückfall wird nur verwendet, wenn alle benötigten Laufzeitimporte erfolgreich geprüft wurden.
- Der sichere Start lädt weder die zuletzt gewählte Konfiguration noch das zuletzt geöffnete Projekt.
- Nach 35 Sekunden ohne UI-Bereitschaft wird der fehlerhafte Kindprozess kontrolliert beendet.
- Qualitätswerkzeuge bleiben vollständig vom Nutzerstart getrennt.
