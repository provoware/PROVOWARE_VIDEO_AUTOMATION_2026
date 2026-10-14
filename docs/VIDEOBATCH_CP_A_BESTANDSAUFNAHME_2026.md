# CP-A · Nachgewiesene technische Bestandsaufnahme (14.10.2026)
Bezug: #234 · Plan-PR #237. **Status: statische Codeprüfung; keine Laufzeitabnahme.**

## Nachgewiesene Befunde
| Datei | Beobachtung | Folge | Priorität |
|---|---|---|---|
| `qt_media_import_dialog.py` | `_set_view_mode("icons")` setzt IconMode und GridSize, `_render_records()` erzeugt `QListWidgetItem` ohne `setIcon()` | Bildminiaturen fehlen im Importauswahldialog | P1 |
| `qt_source_panel.py` | getrennte DropList plus Standard-Dateidialog durch `_choose_media` / `_choose_audio` | unterschiedliche Importwege; Medienbrowser nicht konsequent genutzt | P1 |
| `qt_phase2.py` | erweiterter `MediaImportDialog` nur unter 'Weitere Werkzeuge' | doppelte Medienauswahlwege | P1 |
| `qt_theme.py` / `qt_ui_polish.py` | Basisschrift 11 pt, Hilfetexte 9,5 pt, Lastanzeige 8,5 pt | normale Darstellung teilweise zu klein | P1 |
| `qt_ui_polish.py` | `configure_job_table` setzt feste Spaltenbreiten 42/105/145, kein flexibles Größenmodell | beengte Dateinamen/Status | P2 |
| `qt_media_list.py` | Dateieinträge aus Dateiname + Größe/Datum in zwei Zeilen, Bilder 72x54 als Icon | unnötig hohe Dateilisten | P2 |
| `qt_main_layout.py` / `qt_workspace_layout.py` | `QStackedWidget` mit dashboard/media/effects/queue; KPIs nur auf Übersicht; globale Grundeinstellungen fehlen | Basis für Umbau bereits vorhanden, keine komplette Neuentwicklung nötig | P1 |
| `qt_ui.py` | `_settings_panel` verwaltet Zielordner und Schnellmodus auf eigener Seite | Grundbedienung nicht global sichtbar | P1 |
| `quick_modes.py` | `apply_quick_mode` und `processing_options_for_job` überschreiben Auflösung, Effekt und andere Parameter | Gefahr widersprüchlicher Dashboard-/Renderwerte | P0 bei Umbau |
| `qt_preview_panel.py` | besitzt asynchronen `SelectionPreviewController`, Token-Prüfung und seitenverhältnisgetreue Darstellung | vorhandene Architektur wiederverwenden | positiv |
| `models.py` | `BatchOptions` enthält `resolution` und `visual_effect`, aber keine separate einfache Qualitätseinstellung | Modelländerung nötig; Migration absichern | P1 |

## Festlegung Architektur
1. **Eine einzige Quelle für Nutzerwerte**; globale Anzeige dockt nur an dieses Modell an.
2. Schnellmodus ist Vorlage, nicht dauerhafter heimlicher Vorrang über Nutzervorgaben.
3. Vorhandenen `SelectionPreviewController` und Vorschaukomponenten verwenden; Thumbnail-Generierung asynchron und per Cache.
4. XDG-Benutzerordner für Videos, Downloads, Bilder; ignorierte Entwicklungsordner; keine Verfolgung fremder Symlink-Bäume.
5. Bestehende Qt-Seiten umbauen; keine unnötige neue Oberfläche parallel.
6. Erst CP-B/C synchron planen, danach CP-D/E; reale Sichtabnahme erst CP-F.

## CP-A Prüfnachweise
- [x] Benannte Kern-Quelldateien gelesen und statische Defekte nachgewiesen.
- [x] Risiko heimlicher Renderparameter-Überschreibung erkannt.
- [x] Migrationspfad für vorhandene UI-Bausteine festgelegt.
- [ ] Realen Start auf Kubuntu 26.04/Plasma/Wayland geprüft.
- [ ] Screenshots 100/125/150/200 % gesammelt.
- [ ] Aktuelle Test-Suite und Performance-Baseline ausgeführt.
**Ergebnis:** CP-A **teilweise erfüllt**, nicht freigegeben. Kein Release/kein Merge allein auf Basis dieses Dokuments.

## Arbeitsanweisung als nächstes
- CP-A fehlende reale Nachweise ergänzen.
- B/C: Ein schlankes Dashboard-State-Modell als separaten PR mit Tests liefern; sichtbare UI danach anschließen.
- Zur GitHub-Prüfung jede Teiländerung mit Datei, Test, Screenshot, Rückrollweg und Master-Issue #234 dokumentieren.
