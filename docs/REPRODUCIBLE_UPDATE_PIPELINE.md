# Reproduzierbare Update- und Prüfstrecke

## Trennung

- `build_artifacts.sh` erzeugt Screenshots, HTML und Manifeste.
- `test.sh` prüft ausschließlich lesend und führt visuelle Tests in einer temporären Projektkopie aus.
- `quality.sh` verlangt die externen Qualitätswerkzeuge zwingend.

## Update-Kandidat

Nach Anwendung des Updates wird `RELEASE_MANIFEST.json` vollständig validiert. Vor und nach `test.sh` werden sämtliche distributiven Dateien gehasht. Jede Veränderung oder neu entstandene Nutzdatei blockiert die Aktivierung.

ZIP-Pakete werden auf doppelte Namen, Links, Traversal, Dateizahl, entpackte Größe, Kompressionsrate, deklarierte Operationen und SHA-256 geprüft. `delete` ist explizit deklarierbar; rekursive Verzeichnislöschungen sind verboten.
