# VideoBatch 2026 – echte Kubuntu-26.04-Qt-Abnahme

Diese Abnahme ist **kein CI-Test**. Sie ist für den echten Zielrechner gedacht:

**Kubuntu 26.04 LTS · KDE Plasma · Wayland · PySide6/Qt 6**

Der bestehende kanonische Startpfad wird durch diese Prüfung **nicht** umgestellt.

## Start

Im Projektordner die Datei **`KUBUNTU_26_04_QT_ABNAHME.sh`** ausführen. In Dolphin kann eine ausführbare Skriptdatei direkt gestartet werden.

Der Durchlauf erledigt vier Schritte:

1. echtes Kubuntu 26.04, KDE Plasma und Wayland prüfen,
2. die bereits definierte, geprüfte Qt-Laufzeit vorbereiten,
3. den realen `STARTEN.sh`-Pfad mit automatischem Test-Schließen prüfen,
4. die native Phase-3-Qt-Oberfläche öffnen, wichtige Ansichten fotografieren und die Ampelkarte anzeigen.

Fehlen lokale Python-/Qt-Pakete, darf die vorhandene Toolchain sie online reparieren. **Vor dem ersten DNS-/PyPI-Zugriff erscheint die bereits implementierte grafische KDE-Bestätigung.** Ohne Zustimmung bleibt die Abnahme offline und unverändert.

## Was automatisch geprüft wird

- Kubuntu 26.04 + KDE Plasma + Wayland,
- Qt läuft tatsächlich über das Wayland-Backend,
- Tkinter ist im neuen Qt-Abnahmepfad nicht geladen,
- verifizierte Runtime,
- FFmpeg und FFprobe,
- echter `STARTEN.sh`-Start bis `UI_READY` und sauberer Test-Abschluss,
- Mindestbildschirmfläche 1024 × 700,
- Hauptfenster, Status, Start-Schaltfläche, Auftragstabelle und Workspace-Navigation,
- Projekt- und Diagnosebereich,
- Screenshots von Dashboard, Medien, Vorschau, Projekt und Diagnose.

## Ergebnis

Jeder Lauf bekommt einen eigenen Ordner unter:

`~/.local/state/VideoBatchFast/acceptance/<datum_uhrzeit>/`

Darin liegen:

- `AMPEL.html` – leicht lesbare Ampelkarte,
- `ABNAHME.txt` – Klartextbericht,
- `acceptance.json` – maschinenlesbarer Bericht,
- `startpfad.log` – Ergebnis des echten Startpfads,
- `screenshots/` – native Qt-Screenshots.

Es werden **keine Projekt- oder Mediendateien** für die Abnahme benötigt oder verändert.

## Manuelle Sichtfreigabe

Nach den automatischen Prüfungen bleibt ein kleines Abnahmefenster offen. Die eigentliche VideoBatch-Oberfläche bleibt dabei bedienbar.

Nur wenn alle automatischen Punkte grün sind, wird der Button **„Sichtprüfung bestanden“** freigeschaltet. Für eine grüne Gesamtfreigabe ist zusätzlich ein Prüfername erforderlich.

Schließen oder **„Noch nicht freigeben“** bedeutet:

**🟡 technisch bestanden, aber noch keine endgültige Freigabe.**

Erst ein vollständig grüner Bericht darf als Grundlage für den **separaten, reversiblen Schritt zur Umschaltung des kanonischen Startpfads auf Qt** verwendet werden.
