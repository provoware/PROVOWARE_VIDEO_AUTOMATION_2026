# Implementierungsbericht 2.8.3-rc13

## Ziel

Portable Offline-Laufzeit und automatisiertes Fehlerlabor gemeinsam umsetzen.

## Umsetzung

1. Portabler Laufzeitvertrag für Linux x86-64 eingeführt.
2. CPython 3.13.5 einschließlich Tk und vier exakten Runtime-Paketen eingebettet.
3. FFmpeg/FFprobe 7.1.3 samt dynamischem Linux-Lader und rekursiv ermittelten Bibliotheken eingebettet.
4. Vollständiges SHA-256-Dateimanifest ergänzt.
5. Selbstentpackenden Ein-Datei-Starter mit inhaltsgebundenem Cache erstellt.
6. Portable Laufzeit direkt im Bootstrap verifiziert; kein venv-Aufbau und kein Netzwerkzugriff.
7. Explizite portable FFmpeg-/FFprobe-Auswahl implementiert.
8. Zwölf isolierte Fehler- und Recovery-Szenarien implementiert.
9. Fehlerlabor in Hilfezentrum, Shell-Einstieg und Qualitätsgate integriert.
10. Frische UI-Startprüfung aus der eingebetteten Laufzeit durchgeführt.

## Ergebnis

- Python-Tests: 198/198
- Zeilenabdeckung: 81,84 %
- Branch-Abdeckung: 66,91 %
- Anwendungssimulationen: 12/12
- Fehlerlabor: 12/12
- visuelle Szenarien: 16/16
- interne Qualitätsbefunde: 0
- maximale Komplexität: 28/30

## Grenzen

Die portable `.run`-Ausgabe ist ein selbstentpackender Linux-Ein-Datei-Starter, kein SquashFS-AppImage. `appimagetool` und `mksquashfs` waren in der Buildumgebung nicht vorhanden. Die Funktionalität ist dennoch vollständig portable und offline. Ruff, MyPy, Bandit und pip-audit bleiben verpflichtende Stable-Gates, konnten in der isolierten Buildumgebung mangels vorhandener Qualitäts-Wheels nicht real ausgeführt werden.

- byteidentische portable Doppelpaketierung: bestanden
