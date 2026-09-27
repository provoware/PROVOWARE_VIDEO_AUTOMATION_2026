# Best Practices – gehärteter Entwicklungsvertrag

- Offline-Pfade als Zustand behandeln, nicht als Löschsignal.
- Vor jedem externen Prozess sämtliche Ziele reservieren.
- Quelldaten erst nach bestätigtem Zielhash entfernen.
- Wiederaufnahme über Journale statt Annahmen steuern.
- Hintergrundthreads immer über `finally` abschließen.
- Prozesse als Gruppe starten und begrenzt beenden.
- Pluginfähigkeiten erst nach vollständiger Implementierung freischalten.
- Sicherheitsversprechen technisch durchsetzen oder Funktion blockieren.
- Build und Verifikation nie im selben schreibenden Ablauf vermischen.
- Releaseprüfungen müssen vor und nach Ausführung denselben Dateivertrag bestätigen.
- Qualitätswerkzeuge exakt sperren und in einem separaten Entwickler-Venv installieren.
