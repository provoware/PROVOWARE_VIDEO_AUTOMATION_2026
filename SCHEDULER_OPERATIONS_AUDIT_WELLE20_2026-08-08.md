# Scheduler Operations & Recurrence Audit – Welle 20 – 2026-08-08

## Ziel

Die in Welle 19 freigegebene lokale Startzeituhr wird zu einer begrenzten, nachvollziehbaren Scheduler-Verwaltung erweitert. Wiederholungen dürfen weder unendlich laufen noch bei Zeitumstellungen, verspätetem Start oder parallelen Renderprozessen unkontrolliert auslösen.

## Systemvertrag

- Pläne sind Schema 2; bestehende Schema-1-Pläne werden explizit als einmalige Schema-2-Pläne migriert.
- Unterstützte Serien: einmalig, täglich oder wöchentlich mit Intervall 1–30 und höchstens 366 geplanten Vorkommen.
- Jede Serie speichert eine IANA-Zeitzone und eine deterministische DST-Regel.
- Nicht existente lokale Zeiten beim Wechsel auf Sommerzeit werden als `dst_skipped` historisiert und nicht erfunden.
- Doppelte lokale Zeiten beim Wechsel auf Winterzeit verwenden deterministisch den späteren Zeitpunkt.
- systemd erhält für jedes Vorkommen einen konkreten UTC-Zeitpunkt; dadurch bleibt der tatsächliche Trigger eindeutig.
- Catch-up ist explizit `skip` oder `run_once`. `run_once` ist zusätzlich durch das konfigurierte maximale Verspätungsfenster begrenzt.
- Jede Serienausführung wird einzeln historisiert. Maximal 500 Verlaufseinträge werden aufbewahrt.
- Mehrere Pläne pro Projekt sind erlaubt; die Verwaltung zeigt aktive, abgeschlossene und abgebrochene Pläne sowie den Verlauf.
- Plan bearbeiten ersetzt den alten Plan erst nach erfolgreicher Registrierung des neuen Plans. Bei Fehler wird der neue Plan zurückgerollt.
- Plan duplizieren erzeugt eine neue Scheduler-ID und übernimmt die Planparameter, ohne die alte Serie zu verändern.
- Eine globale prozessübergreifende Render-Lease verhindert parallele Batches aus GUI und Scheduler.
- Bei belegter Render-Lease darf ein Schedulerlauf höchstens bis zum Catch-up-Ende verzögert werden. Danach wird das Vorkommen als Konflikt abgeschlossen und die Serie kontrolliert fortgeführt.

## DST- und Zeitzonenregeln

VideoBatch berechnet Wiederholungen als lokale Wandzeit in der gespeicherten IANA-Zeitzone. Der nächste konkrete Trigger wird anschließend nach UTC transformiert. Damit wird die lokale Nutzerabsicht von der systemd-Ausführung getrennt:

1. Normale Tage behalten die lokale Uhrzeit.
2. Eine nicht existente Uhrzeit in der Frühlingsumstellung wird übersprungen.
3. Eine doppelte Uhrzeit in der Herbstumstellung verwendet den späteren der beiden realen Zeitpunkte.
4. Ein später geänderter System-Zeitzonenwert verändert eine bereits gespeicherte Serie nicht stillschweigend.

## Konflikt- und Catch-up-Policy

- Regulärer Start: bis zwei Minuten nach geplantem Zeitpunkt ohne Sonderbehandlung.
- `skip`: spätere Aktivierung überspringt das konkrete Vorkommen.
- `run_once`: spätere Aktivierung darf genau einmal innerhalb des konfigurierten Catch-up-Fensters ausführen.
- Renderkonflikt: neuer Versuch standardmäßig nach zehn Minuten, jedoch niemals jenseits des Catch-up-Endes.
- Stale Projekt-/Quelldaten: Serie wird blockiert statt mit geänderten Medien weiterzulaufen.

## Bedienung

Die bisherige Einmal-Startzeit wurde durch `Zeitpläne verwalten` ersetzt. Die Ansicht enthält:

- Liste aller Pläne des geöffneten Projekts,
- nächsten Termin,
- Wiederholungsart,
- Status und Fortschritt der Serie,
- separaten Verlauf abgeschlossener Vorkommen,
- Neu, Bearbeiten, Duplizieren, Löschen und Aktualisieren.

## Validierung

- 624/624 Gesamtregressionstests in acht vollständigen Xvfb-Batches bestanden.
- Welle-20-Scheduler-Fachtests: 15/15 bestanden.
- Coverage: 81,42 % Lines / 65,76 % Branches / 78,21 % kombiniert; Mindestvertrag 80/65 bestanden.
- Interne Codequalität: 318 Python-Dateien, 2.744 Funktionen, maximale Komplexität 29, 0 Befunde.
- Architektur: 0 Befunde; größte Python-Datei bleibt `ui.py` mit 700 Zeilen.
- Ereignisarchitektur und Ereignisregister: 0 Befunde.
- Designvertrag, Dokumentationsvertrag, Release-Literal und isolierte Python-Kompilierung: bestanden.

## Offene externe Stable-Nachweise

Ruff, MyPy, Bandit, pip-audit, physische KDE-X11-Abnahme und der reale 96-Job-Slow-Target-Soak bleiben unabhängig von Welle 20 offen. Sie wurden weder simuliert noch als bestanden markiert.
