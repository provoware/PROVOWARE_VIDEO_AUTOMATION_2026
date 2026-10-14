# CP-UX – Nutzerprüfung mit Schwerpunkt Einsteiger (Codeprüfung)

Bezug: #234 / #238 / PR #239. **Keine reale GUI-Abnahme**: Dies ist ein statisches Code-Audit des Entwicklungszweigs, keine getestete Nutzerstudie.

## Kritische Befunde
1. `dashboard_settings.py` ist aktuell nicht mit `qt_ui.py` und `qt_main_layout.py` verbunden. Zwei unabhängige Zustandsquellen bergen Inkonsistenzen. **P0**
2. `qt_main_layout.py` ordnet vier Auswahl-/Eingabefelder und Beschriftungen in einer einzigen horizontalen Zeile an. Unter 100/125/150/200 % und kleiner Fensterbreite drohen Platzmangel/abgeschnittene Texte. **P1**
3. `qt_workspace_layout.py` führt weiter dashboard/media/effects/queue, darunter die eigenständige Ausgabeseite. Schritttexte in `qt_main_layout.py` und `qt_ui.py` behaupten weiter '2 · Ausgabe'. Das widerspricht der globalen Dashboard-Konfiguration. **P1**
4. `qt_ui.py` nutzt für normale Audio-/Medienauswahl weiter `QFileDialog.getOpenFileNames`; `MediaImportDialog` ist bislang Sonderwerkzeug im Phase-2-Dock. **P1**
5. `qt_media_import_dialog.py`: IconMode/GridSize ohne Bild-Icons je `QListWidgetItem`. Reale Thumbnails fehlen. **P1**
6. `qt_ui.py`: `_dashboard_effects()` listet QUICK_MODES, welche sowohl visuellen Effekt als auch Übergang definieren. Beschriftung 'Effekt' verschleiert mögliche zusätzliche Eingriffe. **P1**
7. `dashboard_settings.py`: sprechende Labels (HD, Full HD) vs. Qt-Werte ('1280×720', '1920×1080'); 'Schnell' vs. 'turbo'. Vor Persistenz ist ein einheitliches Schlüssel-/Anzeige-Mapping nötig. **P1**
8. `qt_theme.py`: 8,5–11 pt Texte, `qt_ui_polish.py`: feste Tabellenspaltenbreiten, `qt_media_list.py`: Zweizeileneinträge. **P1**
9. Die vier neuen Bedienelemente werden noch nicht nachgewiesen gespeichert/wiederhergestellt, `qt_ui.py` setzt Ausgabeort beim Start. **P1**
10. Render-Konfiguration arbeitet mit `quick_mode='custom'`, verhindert Preset-Überschreibung; aber vollständige Qualitätssicherung über FFmpeg, Diashow, Wiederholung und Kopierpfad steht aus. **P0 für Release**.

## Verbindliche Einsteiger-Abnahmeszenarien
- **N1** Erster Start ohne Dateien: Auswahlort und nächster Schritt sofort klar, technische Details versteckt.
- **N2** Drei Bilder + drei Audios: einheitlicher Import, echte Thumbnails beim Auswählen und Großvorschau auf einfachen Klick.
- **N3** 100 %: sämtliche Beschriftungen lesbar; 125/150/200 %: keine abgeschnittene Kernbedienung, ggf. responsive Zeilen statt horizontalem Gedränge.
- **N4** Ausgabeordner/Qualität/Auflösung/Effekt ändern, Reiter wechseln, Anwendung neu starten: exakt dieselben Werte.
- **N5** Effekt erklärt, ob auch Übergang verändert wird; Qualität beschreibt Zeit/Dateigröße statt Codec/CRF.
- **N6** Fehlende Paare: Fehlermeldung direkt an problematischem Eintrag, sichere Korrekturmöglichkeit ohne Datenverlust.
- **N7** Große Downloads-Verzeichnisse: nur unterstützte Bild-/Audio-/Videodateien indizieren, Entwicklungspfade ignorieren; UI bleibt bedienbar.
- **N8** Falscher Ausgabeort, defektes Bild, fehlendes FFmpeg: deutliche Ursache und nächster Lösungsschritt in Alltagssprache.
- **N9** Abbruch und Wiederanlauf: keine Änderungen der Originale; kein unbemerkter Renderstart.
- **N10** Tastaturbedienung: Reihenfolge, Fokus, Tooltips und Auswahldialog ohne Maus nutzbar.

## Korrekturfolge
UX-01 Eine verbindliche Quelle für UI-/Render-Einstellungen mit validiertem Schlüsselmapping und Persistenz.
UX-02 Globale vier Einstellungen als flexibles 2x2-/4-Spalten-Raster, responsiv, ohne Überschneidungen.
UX-03 Veraltete Ausgabe-Seite/Schrittetexte entfernen, vier Arbeitsreiter klar beschriften.
UX-04 Importdialog vereinheitlichen, echte asynchrone Vorschaubilder und sofortige großformatige Vorschau implementieren.
UX-05 Fehlermeldungen und Dateipaarung laiengerecht überarbeiten.
UX-06 Schrift, Zeilenhöhen, Vorschaugrößen, Tastatur/Skalierung real prüfen.
UX-07 Renderbefehle, Presets, Diashow, Fast-Copy und Wiederholung mit expliziten Vorgaben prüfen.

## Checkpoint CP-UX
- [x] Statische Prüfung der betroffenen Quelltexte.
- [x] Verifizierbare Defektliste und Nutzer-Abnahmeszenarien erstellt.
- [ ] N1–N10 tatsächlich auf Kubuntu 26.04 / Plasma / Wayland durchgeführt.
- [ ] Screenshots 100/125/150/200 % vorhanden.
- [ ] UI-Fixes, Regressionstests und End-to-End-Renders abgeschlossen.

**Freigabe:** OFFEN; PR #239 nicht allein aufgrund dieses Dokuments mergen.
