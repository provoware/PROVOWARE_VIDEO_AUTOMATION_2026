# Status VideoBatch Fast 2.8.3-rc24

- Kanal: Release Candidate
- RC24-Iteration: 100 % · 18 von 18 Punkten erledigt
- vollständiges Projekt-ZIP ist die primäre Ausgabe vor Stable
- Absturzpfad der bereits ausgewählten Bilderliste strukturell beseitigt
- exakt ein serieller Vorschauarbeiter statt unbegrenzter FFmpeg-Vorschauprozesse
- Klick-Debounce und Generationstoken aktiv
- Fokuszeile der Mehrfachauswahl steuert die Vorschau
- defensive Pillow-Prüfung vor Übergabe an Tk
- interaktive Aktionen „Datei technisch prüfen“ und „Extern öffnen“ funktionsfähig
- Diagnose-Logging besitzt sicheren Temp-Fallback
- Plugin-Sandbox wird real auf Namespacefähigkeit geprüft
- 272/272 Tests bestanden; 2 Sandboxfälle korrekt übersprungen
- 82,89 % Zeilen- und 66,80 % Branch-Abdeckung
- 18/18 visuelle Szenarien bestanden
- reale GUI-Stressprüfung mit 120 schnellen Medienklicks bestanden

## Offene Stable-Gates

1. Ruff 0.16.1 real ausführen
2. MyPy 2.3.0 real ausführen
3. Bandit 1.9.4 real ausführen
4. pip-audit 2.10.1 real ausführen
5. physische KDE-X11-/Wayland-Abnahme
6. Langzeitrender mit großer Medienauswahl und langsamem externem Ziel
