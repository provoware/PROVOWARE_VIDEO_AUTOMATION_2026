# VideoBatch – QA- und Refactoring-Umsetzung vom 20.10.2026

**Status:** Entwicklungsstand; keine Stable-Freigabe und keine physische Endabnahme.  
**Basis:** PR #252, Commit `3e5862fadfcbcd50d2370017dd6e0b90f4c570df`.  
**Arbeitszweig:** `work/videobatch-audit-qa-ui-recovery-20261020`.

## Umgesetzt

1. **Kleine Fenster:** Das Qt-Mindestfenstermaß wurde von 980×640 auf 800×600 gesenkt. Kopfbereich und Ressourcen-/Fortschrittsanzeige erhalten eigene volle Rasterreihen; das Einstellungsfeld bleibt vertikal scrollbar.
2. **Schaltflächen:** Die neue `ResponsiveControlRow` ordnet zusammengehörige Aktionen dynamisch horizontal oder vertikal an. Die Dateiauswahl, die Übernahme der Produktionsreihenfolge, die Produktionsaktionen und die Ergebnisaktionen teilen die gleiche Regel. Ein begrenzter vertikaler Scrollbereich hält Produktionsaktionen bei großer Schrift erreichbar.
3. **Prüfcode:** Veraltete Annahmen zur früheren Einstellungs-Zweispaltenansicht werden durch Prüfungen der sechs tatsächlich vorhandenen Qt-Felder ersetzt. Die sieben Schriftstufen werden für den Schaltflächenumbruch parametrisiert. Die bestehende 42-Fälle-Rastermatrix bleibt erhalten.
4. **Update-Sicherheit:** Update-Sicherungen bekommen eindeutige Namen und werden vor dem Umschalten weder gelöscht noch überschrieben. Fehler beim Austausch oder beim anschließenden Synchronisieren führen zum Versuch, die alte Installation zurückzusetzen. Fehler-Einspritztests prüfen diese Pfade.

## Explizite Grenzen

- Eine **statische Quelltextprüfung** oder der **Qt-Offscreen-Test** ersetzt keine Sichtabnahme der vollständig gestarteten Oberfläche.
- Die 42 Fälle (sechs Fensterformate × sieben Schriftstufen) sind derzeit für die **Rasterberechnung** abgebildet; ein vollständiger grafischer 42-Fälle-Screenshotnachweis aller Seiten und Bedienelemente steht aus.
- Die bisherige Qt-/Tk-Parität nutzt an mehreren Stellen nachträglich installierte Methoden. Sie wird absichtlich nicht ohne Funktionsvergleich entfernt. Zu bereinigen sind insbesondere `qt_phase3_components.py`, `qt_legacy_parity.py`, `qt_legacy_parity_completion.py` und alte `ui*_mixin.py`-Bausteine.
- Die Update-Korrektur garantiert keine Wiederherstellung nach einem plötzlichen Stromausfall zwischen zwei Dateisystem-Umbenennungen. Dafür ist ein **separater Transaktions-Wiederanlauf beim nächsten Start** mit persistentem Journal und Fehlereinspritzung erforderlich.
- Jede Änderung an Programm- und Testdateien erfordert die anschließende **Neugenerierung des Release-Manifests und des Git-Dateiindex** auf genau dem letzten Commit; nicht mit historischen RC24-Belegen verwechseln.
- Die automatische Gesamtprüfung muss für **einen einzigen unveränderten Commit** nachgewiesen werden, inklusive Qt6/Wayland, FFmpeg, Installation/Start aus frisch entpacktem ZIP, Update-Rückfall und Sicherheitsverträgen. Es liegt für diesen neuen Arbeitszweig noch kein solcher Abschlussnachweis vor.

## Refactoring-Reihenfolge

**R1 – Erfassen:** Alle aktiven Aufrufketten zu Tk-/Legacy-Adaptern systematisch verfolgen und mit realen Qt-Bedienfunktionen vergleichen. `__main__.py` und der produktive Bootstrap starten Qt Phase 3; das ist kein Beleg, dass Legacy-Adapter entbehrlich sind.

**R2 – Ersetzen:** Ein einzelnes, bereits gleichwertiges Teilmodul nach direkten Funktions- und Wiederherstellungstests ablösen. Methodenersetzung beim Import und mehrere Zustandsquellen vermeiden, ohne vorhandene Projektformate zu verändern.

**R3 – Prüfen:** Nach jeder Entfernung die vollständige Quellcode-, Paket- und Startprüfung erneut ausführen. Kein massenhaftes Löschen von Altmodulen auf Verdacht.

## Freigabevertrag / verbleibende Schritte

- [ ] Design-/Release-Index auf finalem Commit erzeugen und verifizieren.
- [ ] Sämtliche automatisierten Prüfungen einschließlich zuvor nicht ausgeführter älterer Qt-Tests auf einem unveränderten Commit grün.
- [ ] Visuelle Mess- und Screenshotmatrix auf vollständig gestarteter Qt-Oberfläche: 800×600, 1024×768, 1280×720, 1366×768, 1920×1080, 2560×1440; jeweils 80/100/110/125/150/175/200 %.
- [ ] Ungewollte horizontale Überläufe, unlesbare oder verdeckte Schalter, unerreichbaren Tastaturfokus und mögliche Endlosschleifen beim Layoutwechsel reparieren.
- [ ] Absturz- und Stromausfall-Recovery bei Update-Umschaltung vollständig entwickeln und prüfen.
- [ ] Qt-/Tk-Migrationsrest mit messbarer Funktionsparität schrittweise beseitigen.
- [ ] Freeze, einmalige physische Kubuntu-26.04/KDE/Wayland-Abnahme bei 100/125/150/200 %, reale Videos/FFmpeg und Langzeitrender.
- [ ] Erst danach eine Stable-Freigabe erwägen.

**Qualitätsprinzip:** Ein grüner CI-Teiltest ist kein Beleg für den vollständigen Releasevertrag. Fehlende Nachweise bleiben ausdrücklich offen.
