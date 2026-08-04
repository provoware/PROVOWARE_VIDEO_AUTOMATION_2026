# VideoBatch Fast 2.8.3-rc13 – distributionssichere Portable- und Signaturkette

## Behobener Produktionsfehler

RC12 führte FFmpeg über den mit Python gebündelten dynamischen Linux-Lader und ein globales `LD_LIBRARY_PATH` aus. Auf Kubuntu endete der FFmpeg-Smoke-Test deshalb mit `SIGABRT` und `*** stack smashing detected ***`.

RC13 trennt die Laufzeiten vollständig:

- Der eingebettete Lader gilt ausschließlich für Python/Tk.
- FFmpeg und FFprobe werden niemals mit der eingebetteten glibc gestartet.
- Medienprogramme erhalten eine bereinigte Umgebung ohne `LD_LIBRARY_PATH`, `PYTHONHOME`, `PYTHONPATH`, `TCL_LIBRARY` und `TK_LIBRARY`.
- Der Starter prüft FFmpeg und FFprobe real, bevor die Oberfläche geöffnet wird.
- Die selbstentpackende Nutzlast wird vor dem Entpacken über SHA-256 geprüft.

## Kryptografische Lieferkette

- Ed25519-Signaturen für Portable-Datei, Quell-ZIP, TAR-Archiv, Manifest und Buildbericht
- eingebetteter öffentlicher Release-Schlüssel
- privater Schlüssel bleibt außerhalb aller Releasepakete
- offizielle Updatepakete enthalten `update_signature.json`
- veränderte Dateien, fremde Schlüssel und manipulierte Update-Manifeste werden abgewiesen

## Kubuntu-Buildmatrix

Automatisierte Ziele:

- Ubuntu/Kubuntu-Basis 22.04 · X11
- Ubuntu/Kubuntu-Basis 22.04 · Wayland-Vertrag
- Ubuntu/Kubuntu-Basis 24.04 · X11
- Ubuntu/Kubuntu-Basis 24.04 · Wayland-Vertrag

Jedes Ziel prüft Tests, Coverage, Fehlerlabor, AAC-Smoke, Portable-Build, Manifest, UI-Handschlag, Signatur und byteidentischen Doppelbuild.
