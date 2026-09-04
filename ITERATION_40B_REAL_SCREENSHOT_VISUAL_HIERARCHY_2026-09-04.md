# Iteration 40B · Real-Screenshot Visual Hierarchy

Datum: 2026-09-04  
Basis: Iteration 40A · `3f88a4411c34b6c1c6ba11576cfa669d1a2dcd02`  
Version: `2.8.3-rc24`

## Ausgangsevidence

Der reale Nutzer-Screenshot (1858 × 1080) zeigt die Canonical-Shell im Bereich **Effekte**. Die dominanten Flächenfarben entsprechen dem Legacy-Theme `toxic_candy` (`#0D2927`, `#0B2220`, `#173B37`) und nicht dem 40A-Standard `Midnight Blue`. Damit war die sichtbare Abweichung reproduzierbar erklärt: Die Theme-ID blieb aus gespeicherten Nutzereinstellungen aktiv, während nur der öffentliche Name bereits `Violet Pulse` lautete.

## Vergleich zur kanonischen SVG

Die Referenz verwendet einen ruhigen Navy-Grund (`#061426`), subtile Containerkonturen (`#193756`/`#214361`), erhöhte Kartenflächen und helle Akzentfarben nur für Auswahl, Status und Primäraktionen. Der reale Screenshot zeigte dagegen durch `#36BFA6`/`#256B60` nahezu jede Fläche gleich stark gerahmt. Dadurch gingen Hierarchie, Weißraum und Fokus verloren.

## 40B-Korrektur

1. `Violet Pulse` erhält eine echte Navy/Violet-Palette statt der alten Toxic-Candy-Grünpalette.
2. Normale Rahmen verwenden `border_subtle`; helle Farben bleiben Fokus/Status vorbehalten.
3. Header, Sidebar, KPI-Karten und Aktionsleiste erhalten konsistente, ruhige Surface-Grenzen.
4. Schnellmodus-Auswahl nutzt `selection` statt vollflächigem Informations-Cyan.
5. Eingabefelder und Comboboxen sind im Ruhezustand dezent und werden erst bei Fokus deutlich.
6. KPI-Metadaten bleiben vollständig im internen Vertrag erhalten, erscheinen aber als eine tertiäre Zeile statt als zwei gleichgewichtete technische Zeilen.
7. Der Einstellungen-Shortcut wird nicht als zweite aktive Seite markiert; Tastaturfokus erhält keine aktive Vollfläche.
8. Der deaktivierte Scheduler wird aus der Primäraktionsleiste entfernt; die verbleibenden sechs Hauptaktionen werden auf breiten Fenstern bevorzugt in einer Zeile angeordnet.

## Bewusst nicht verändert

Render-/FFmpeg-Pipeline, Queue-/Retry-Logik, Medienimport, Fehlerbehandlungsverträge, Scheduler-Funktionalität, Screenshot-Harness/Baselines und PySide6/QML-Transferlinie bleiben unverändert.

## Abnahmekriterien

Palette und Name konsistent · Kernkontraste mindestens 4,5:1 · Containerrahmen schwächer als Fokus · Schnellmodus klar ohne Neon-Cyan · KPI-Diagnosedaten erhalten · Vollregression und Architektur grün · Manifest und deterministischer Vollprojektbau grün.
