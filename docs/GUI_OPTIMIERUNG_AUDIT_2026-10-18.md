# Qt-Oberfläche und Videoeinstellungen – Prüfung und Optimierung (18.10.2026)

**Status:** Entwicklungszweig `feature/bedienung-effekte-20261018`. Keine Stable-Freigabe; historische RC24-Nachweise bleiben unverändert. Die Bestandsaufnahme beruht auf dem Quellcode. Eine reale Kubuntu-/Wayland-Bedienprüfung ist weiterhin erforderlich.

## 1. Problem- und Ursachenanalyse

Der Qt-Arbeitsbereich trennt Medien, Ausgabe und Produktion. Trotzdem lagen Auflösung, Profil und Effekte in der nachgelagerten Tk-Paritätsoberfläche (`qt_legacy_settings.py`). Dazu kam eine zweite Steuerebene: Schnellmodi in `qt_ui.py` und manuelle Optionen in `qt_legacy_parity.py`. Die technischen Videooptionen sind nur dann wirksam, wenn die Verarbeitung den Modus `custom` erhält. Ein Klick auf die vermeintliche Option kann daher bei aktivem Schnellmodus ohne Änderung an der Ausgabe bleiben.

Die Diashow-Überblendung (`slideshow.py`) und die Ein-/Ausblendung des vollständigen Videos (`effects.py`) sind eigenständige Funktionen. Sie dürfen nicht über einen irreführenden gemeinsamen Regler gesteuert werden.

## 2. Entscheidung für Bedienelemente

| Bereich / Bedienelement | Entscheidung | Begründung und Umsetzung |
|---|---|---|
| Dateiimport Audio / Bild / Video | BEHALTEN | Zentrale Aufgabe, unmittelbar sichtbar auf der Dateiseite |
| Dateiliste / Paarungsanzeige | BEHALTEN | Kontrolliert richtige Quelldateien und Aufträge |
| Ausgabeordner und Ordnerwahl | BEHALTEN | Fehlerprävention und Orientierung |
| Schnellmodus / Automatik | BEHALTEN | Geeigneter Einstieg, `custom` explizit anwählbar |
| Auflösung (Original/HD/FHD/QHD/UHD) | VERLAGERN UND ERWEITERN | Direkt auf der Ausgabeseite, gemeinsame Verarbeitung mit bestehender FFmpeg-Skalierung |
| Kodierungsprofil / Qualität | VERLAGERN UND ERWEITERN | Direkt auf der Ausgabeseite, neue höchste angebotene Stufe `Maximum`; verlustfrei wird nicht versprochen |
| Bildeffekt | VERLAGERN | Direkt erreichbar, im Paritätsdialog nicht doppelt anzeigen |
| Effektstärke | ERGÄNZEN | 0–100 %; 50 % entspricht dem bisherigen Effekt, 100 % verstärkt ihn. Blitzamplitude bleibt sicherheitsbegrenzt; bei „Keine“ ist die Einstellung deaktiviert. |
| Diashow-Überblendung | ERWEITERN | Automatik/alte Vorgaben weiterhin verfügbar, eigene Dauer 0,0–5,0 Sekunden mit 0,1-Schritt |
| Ein-/Ausblendung des Gesamtvideos | BEHALTEN UND PRÄZISIEREN | Eigener, seltener benutzter Expertenwert mit eindeutiger Bezeichnung |
| Ausgabeart / Codec | BELASSEN IM EXPERTENBEREICH | Für normale Anwender selten notwendig |
| Prüfung Schnell/Vollständig | BEHALTEN | Wichtiges Sicherheits-/Zeitprofil |
| Originalschutz | KOMPAKT BEHALTEN | Schutzinformation ohne viel Flächenverbrauch |
| Sicherheitsdetails | EINKLAPPEN | Bei Bedarf abrufbar |
| Erscheinungsbild, Schriftgröße | BELASSEN IM EXPERTENBEREICH | Nicht Bestandteil der täglichen Ausgabe |
| Archivfunktion / automatisches Ordneröffnen / Listen behalten | BELASSEN IM EXPERTENBEREICH | Eigene Arbeitsorganisation, nicht zentral für Video-Qualität |
| Diagnoseprotokoll | EINKLAPPEN | Nur bei Problemen benötigt, trotzdem erreichbar |
| Werkzeug-Docks (Playlist, Kalender, Wartung) | BELASSEN IM MENÜ | Eigenständige Werkzeuge, nicht in die Hauptkonfiguration aufnehmen |
| Einstellungen & Werkzeuge | ZUGANG VERBESSERN | Ein Klick direkt auf der Ausgabeseite, Menü und Strg+, bleiben erhalten |
| Doppelte, unverwaltete Alt-Comboboxen | AUSBLENDEN | Als interne Kompatibilitätsbrücke erhalten, kein zweites sichtbares Formularfeld |

## 3. Technische Durchgängigkeit

| Eingabe | Bedienoberfläche | Zwischenzustand | Videoverarbeitung |
|---|---|---|---|
| Auflösung | `quick_resolution` | `BatchOptions.resolution` | `_scale_filter` / `_slideshow_canvas` |
| Qualität | `quick_profile` | `BatchOptions.profile` | FFmpeg `-preset`, `-crf` |
| Effekt | `quick_effect` | `BatchOptions.visual_effect` | `effect_filter` |
| Intensität | `quick_intensity` | `BatchOptions.effect_intensity` | `effect_filter(key, intensity)` |
| Diashow-Überblendung | `transition_duration` | `BatchOptions.slideshow_transition` + `PairJob.slide_transition` | FFmpeg `xfade` |
| Ein-/Ausblendung | `parity_transition` | `BatchOptions.transition` | FFmpeg `fade` |

Manuelle Änderungen der unmittelbar sichtbaren Ausgabeparameter schalten auf `custom`, sodass Schnellmodi nicht unbemerkt die Benutzerwahl überschreiben. Der ausgewählte Wert wird sowohl in `config.json` als auch in den Projektdateien übernommen.

## 4. Verifikation

Zusätzliche automatisierte Prüfungen in `tests/test_2026_10_compact_video_options.py` decken ab: 0/0,1/1/3/5 Sekunden; Begrenzung bei kurzen Szenen; unzulässige Überblendwerte; Effektintensität für alle vorhandenen Effekte; Kopierpfad bei Intensität 0; FFmpeg-Befehlsargumente; Speichern der Einstellungen.

**Offene manuelle Abnahmen:**

1. Kubuntu 26.04, Wayland, bei 100 %, 125 %, 150 % und 200 %: keine überdeckten oder abgeschnittenen Bedienfelder, verständliche Tab-Reihenfolge, Tastaturbedienbarkeit.
2. Reales Vergleichsvideo mit identischen Medien und 0/50/100 % Effektstärke: sichtbare Wirkung und Qualitätsprüfung.
3. Reale Diashow mit mindestens drei Bildern und 0/1/3/5 Sekunden: kontrollierte Übergänge ohne Lücken, Framefehler oder Tonversatz.
4. Projektspeicherung, Schließen, Wiederöffnung, Absturz-/Wiederanlaufpfad: gleiche Auflösung, gleiches Profil, gleicher Effekt und korrekte Überblendwerte.
5. CPU/RAM und lange Stapelaufträge: keine signifikante Verschlechterung durch Filter- und UHD-Auswahl.

**Freigaberegel:** Keine Übernahme nach Stable vor grünen Testläufen und realer Kubuntu-Abnahme. Eine statische Quellcodeprüfung ersetzt keine praktische Sichtprüfung.
