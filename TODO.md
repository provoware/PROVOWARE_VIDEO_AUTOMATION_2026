# Offene Punkte nach RC24-Finalbereinigung

## Erledigt

- [x] Projektstamm von historischen RC-Berichten bereinigt; Nachweise verlustfrei archiviert.
- [x] Doppelte veraltete visuelle Baselines entfernt.
- [x] Releasefertige eigenständige Unterlagen mit `_save_` gekennzeichnet.
- [x] Fertig/unfertig maschinenlesbar in `RELEASE_FILE_STATUS.json` und zweispaltig in README dokumentiert.
- [x] Vorschauerzeugung für FFmpeg 7+ und beschädigte Cacheziele gehärtet.
- [x] Hilfe-, Cache- und Auswahltexte zentralisiert und Tooltips verbessert.
- [x] Ubuntu 22.04/24.04 × X11/Wayland als verpflichtende PR-Matrix etabliert.
- [x] Typisierten und versionierten `AppEvent`-Vertrag als zentrale UI-Ereignisgrenze eingeführt.
- [x] `BatchRunner` vollständig auf direkte `AppEvent`-Ausgabe mit typisierten Kern-Payloads migriert.
- [x] AST-Wächter blockiert neue freie `(name, payload)`-Ereignistupel außerhalb der Legacy-Grenze.
- [x] Ruff 0.16.1, MyPy 2.3.0, Bandit 1.9.4 und pip-audit 2.10.1 gebunden ausgeführt.

## Noch offene Stable-Gates

- [ ] Physische KDE-Abnahme unter X11 und Wayland dokumentieren.
- [ ] Langzeitrender mit großer Medienauswahl und langsamem externem Ziel durchführen.

Stable bleibt bis zum vollständigen Nachweis der beiden bewusst geparkten Realabnahmen gesperrt.
