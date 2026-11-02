# PROVOWARE – verbindlicher Zeitlimit- und Stillstandsvertrag (PW-TIMEOUT-v1.0)

**Gültig ab:** 02.11.2026 · **Zweck:** Endlose Prüfungen, blockierte Aktionen und unklare Wartezustände sicher beenden, ohne Originaldaten, Spielstände oder laufende Renderprozesse zu gefährden. Dieser Vertrag ist eine **Entwicklungsregel**, nicht bereits der Nachweis, dass jeder Programmprozess technisch überwacht wird.

## 1. Arten von Zeitgrenzen
- **Warnzeit:** Nur anzeigen/protokollieren, niemals ungeprüft abbrechen.
- **Stillstand:** Seit dem letzten **echten** Fortschritt ist zu lange nichts geschehen. Ein laufender Spinner oder ständig wiederholte Logmeldung zählt **nicht** als Fortschritt.
- **Maximallaufzeit:** Absolute Obergrenze für einen **konkret begrenzten** Test/Schritt; längere legitime Medien-/Spielaufgaben brauchen ein begründetes eigenes Profil.
- **Manuelle Wartezeit:** Nutzer liest Dialog, wählt Dateien oder bestätigt ausdrücklich – niemals blind als „Hänger“ töten.

## 2. Vorgabewerte – nur wo nicht schon ein strengeres, geprüftes Profil gilt
| Aktion | Warnen nach | Kein echter Fortschritt | Harte Schranke |
|---|---:|---:|---:|
| Lokaler Start-/Gesundheitscheck | 10 s | 30 s | 60 s |
| Kurzer externer Befehl / Datei-Metadaten | 10 s | 30 s | 120 s |
| Einzelner automatischer UI-/Browser-Test | 15 s | 45 s | 120 s, Ausnahmen dokumentieren |
| Schneller Modul-/Einheitstest | 60 s | 120 s | 5 min |
| Vollständiger CI-Testlauf | 5 min | 5 min prüfpflichtiger Stillstand | Projektbezogen 10–30 min je Job; längere belegte Jobs explizit |
| Netzwerkabruf | 15 s bis Verbindungsaufbau | 60 s ohne Nutzdaten | 10 min für einen abgegrenzten Abruf |
| FFmpeg, Kopierlauf, großer Spiel-/Datenlauf | 120 s ohne verifizierbare Ausgabe | 300 s mit Ursachenprüfung | Kein pauschaler 5-Minuten-Kill: nachvollziehbar konfiguriert nach Aufgabe, Datenmenge und Hardware |
| Manueller Dialog | 120 s Hinweis bei Bedarf | Nicht automatisch als Fehler werten | Kein heimlicher Autoabbruch während legitimer Nutzeraktion |

**Vorhandene projektbezogene, getestete Grenzen bleiben gültig**; ein neuer Standard darf sie nicht stillschweigend lockern. Prozessweite GitHub-Jobs erhalten ein echtes `timeout-minutes`-Limit (wenn bisher keines gesetzt ist). Aufwändige Langzeit- und Hardwaretests nutzen ihren eigens dokumentierten längeren Rahmen.

## 3. Pflichtablauf bei Stillstand/Fehler (fail closed)
1. Bei Start protokollieren: `auftrag_id`, Phase, monotone Startzeit, festgelegtes Zeitbudget, letzte verifizierte Fortschrittszeit, Versuchszahl und erwartete Ausgabedateien. Keine geheimen Token/Privatpfade ins öffentliche CI-Log.
2. Nach Warnzeit Status `VERZÖGERT` anzeigen, letzte reale Änderung und Systemressourcen prüfen. Einen **aktiven** FFmpeg-/Kopier-/Spieletest niemals allein aufgrund verstrichener Zeit abschießen.
3. Bei belegtem Stillstand nur den **eigenen** betroffenen Kindprozess/Job kontrolliert stoppen (Signal, 5–15 s Aufräumfrist, erst danach gezielte Prozessgruppenbeendigung). Kein `killall`, keine fremden Prozesse, keine ungesicherten Originale entfernen.
4. Vor Wiederholung Ausgabe/Teilkopie/Journal/Sperre prüfen. Nur **nachweislich idempotente** (gefahrlos wiederholbare) Schritte automatisch erneut ausführen. Maximal **zwei zusätzliche Versuche** mit Wartezeiten 15 s und 60 s. Dauerhafte Daten-, Rechte-, Prüfsummen- und Sicherheitsfehler sofort `PRÜFEN/BLOCKIERT`, **ohne** automatische Wiederholung.
5. Bei Erschöpfung: Fehler `TIMEOUT` bzw. `STILLSTAND`, Ursache, letzte Phase, Zeit, Versuche, Belegpfad und sichere nächste Handlung protokollieren; andere unabhängige Aufträge weiterarbeiten lassen. **Ein TIMEOUT ist niemals PASS.**
6. Beim Neustart zuerst verifizierte Artefakte/Journale/Lock-Eigentümer sichten, dann ggf. sicher fortsetzen. Sperre eines anderen aktiven Prozesses nicht wegen Alters löschen.

## 4. CI und Entwicklungsgates
- Queued ohne Runner >10 min: Infrastruktur-Warnung, nicht „Test gescheitert“ und nicht grüner Status. In Bearbeitung ohne neue Belege >5 min: Logs/Schrittstatus prüfen; legitime lange Tests weiterlaufen lassen.
- Testsysteme: explizites Test-/Schritt-/Gesamtbudget, gezielte Wiederholung nur flüchtiger Infrastrukturfehler; aktuelle HEAD-SHA, Exitcode und Artefakte verbindlich. Keine automatische Schönfärbung mit `continue-on-error`.
- Umsetzungspflicht im jeweiligen Repo: prüfen, welche `subprocess`-, Netzwerk-, Browser- und Renderpfade noch **keine** technischen Zeitlimits besitzen; als priorisierte TODO mit Negativtests nachführen. Diese Dokumentation alleine bestätigt keine Runtime-Implementierung.
- Bei nur dokumentierter Regel ist der Status **STANDARD DOKUMENTIERT, RUNTIME OFFEN**, nicht „vollständig fertig“.
- Finale Nutzer-/Kubuntu-/Hardwareabnahme bleibt der **letzte** Schritt nach Implementierung und gemeinsamen Tests.

**Kennung:** NI-20261102-02 · Kein globales starres Timeout, keine neuen Laufzeitpakete und kein unbemerkter Eingriff in bestehende Freeze-/Releaseentscheidungen.

## Besonderheiten von PROVOWARE Video Automation 2026
Qt-/KDE-Dialoge, FFmpeg-Renderläufe, Build- und Wayland-Smoke-Jobs brauchen getrennte Budgets. Langzeitrender und echte Zielsystemabnahme niemals durch eine pauschale Kurzfrist beenden. Bereits vorhandene CI-Zeitbudgets und Release-Freeze haben Vorrang. Ein Watchdog wird nur nach Negativtests mit gezieltem Kill eigener Kindprozesse eingeführt.

## Historische Referenzregel des Herkunftsprojekts (nicht für dieses Produkt verbindlich)

Bei FFmpeg muss fehlender echter Fortschritt erkannt werden; das Lesen der Prozessausgabe darf nicht unbegrenzt blockieren. Für Browserstatus und Diagnose gelten getrennte kurze Zeitbudgets. Bestehende 15-Minuten-GitHub-Prüfung nicht verlängern. Der Benutzer-Stopp ist kein technischer Fehlversuch.
