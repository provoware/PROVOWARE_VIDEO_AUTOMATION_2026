# Scheduler Forecast Calibration Audit – Fortsetzungswelle 23

## Ergebnis

Fortsetzungswelle 23 erweitert die Welle-22-Prognoseschicht um eine messbare Qualitäts- und Kalibrierungsebene. Prognosen werden nicht mehr nur erzeugt, sondern nach realen Läufen gegen Ist-Werte geprüft und per Rolling-Origin-Backtest ohne Zukunftsdaten rückwirkend bewertet.

## Umgesetzte Verträge

1. Persistente Actual-vs-Predicted-Beobachtungen nach echten Scheduler-Batchabschlüssen.
2. Gemessene Laufzeit, tatsächliche Outputgröße, damalige P50/P75/P90-Prognose, Confidence, Matchtyp und Samplezahl werden gemeinsam historisiert.
3. Rolling-Origin-Backtest: Für jeden historischen Ziel-Lauf dürfen ausschließlich zeitlich ältere Samples als Trainingsbasis verwendet werden.
4. Backtest-Fenster über die letzten 30, 90 und 180 auswertbaren realen Läufe.
5. Genauigkeitsmetriken: MAE, RMSE, medianer absoluter Prozentfehler, P90-Prozentfehler, Bias und – soweit messbar – Outputgrößenfehler.
6. Fehlersegmentierung getrennt nach Codec, Profil und Auflösung.
7. Automatische Confidence-Kalibrierung: Historische Fehlerrate und Drift können eine nominelle `high`-/`medium`-Confidence begrenzen; schlechte Kalibrierung darf nicht als hohe Sicherheit erscheinen.
8. Kontrollierte Altersgewichtung historischer Samples: bis 30 Tage 1,0; bis 90 Tage 0,75; bis 180 Tage 0,5; ältere Samples 0,25.
9. Laufzeit-Level-Drift: jüngste Sekunden-pro-Job-Mediane werden gegen eine ältere Baseline geprüft.
10. Error-Drift: jüngste Backtest-Fehler werden gegen die vorherige Fehlerbaseline geprüft.
11. Operations-UI um den Reiter `Prognosequalität` mit Backtestfenstern, Segmentfehlern und echten Actual-vs-Predicted-Vergleichen erweitert.
12. Scheduler-Export enthält `forecast-quality.json` und `forecast-actual-vs-predicted.json` zusätzlich zum bestehenden SHA-256-Manifest.
13. Kalibrierungsfehler dürfen den Rendererfolg nicht umklassifizieren: Kann Evidence nicht geschrieben werden, bleibt ein erfolgreicher Render erfolgreich.
14. Alte oder beschädigte Kalibrierungsdateien sind begrenzt, schema-validiert und werden nicht als Prognosebasis interpretiert.

## Methodische Entscheidungen

- Median/P50 bleibt der robuste zentrale Laufzeitwert; P75/P90 bleiben Sicherheitsbänder. Python dokumentiert den Median als weniger ausreißerempfindlich als den Mittelwert.
- Backtests arbeiten nach Rolling-Origin: Der Trainingssatz eines historischen Testpunkts enthält ausschließlich Beobachtungen, die vor diesem Punkt lagen. Damit entsteht keine Future-Leakage.
- MAE und RMSE werden gemeinsam ausgewiesen. Prozentfehler werden nur bei positiver Ist-Laufzeit verwendet, da Division durch Werte nahe null instabil wäre.
- Confidence wird nicht allein aus der Anzahl ähnlicher Samples abgeleitet. Reale Backtest-Fehler dürfen die Confidence herabstufen.
- Alte Daten werden nicht gelöscht, aber kontrolliert geringer gewichtet. Dadurch bleiben seltene historische Konfigurationen nutzbar, ohne aktuelle Systemleistung zu überstimmen.
- Drift ist ein Warnsignal, kein automatischer Datenlöschbefehl. Welle 23 verändert keine historischen Journale und trainiert kein undurchsichtiges ML-Modell.

## Externe Referenzen

- Python `statistics`: https://docs.python.org/3/library/statistics.html – Median und Quantile; Median als robuste zentrale Lage.
- Forecasting: Principles and Practice, Time-series cross-validation: https://otexts.com/fpp3/tscv.html – Rolling forecasting origin ohne Nutzung zukünftiger Beobachtungen.
- Forecasting: Principles and Practice, Forecast accuracy: https://otexts.com/fpp3/accuracy.html – MAE/RMSE und Grenzen prozentbasierter Fehlermaße.

## Finaler Teststand

- 672/672 Tests bestanden.
- Coverage: 81,40 % Lines / 65,30 % Branches / 78,03 % kombiniert.
- Coverage-Mindestvertrag 80/65 bestanden.
- Interne Codequalität: 334 Dateien / 2.913 Funktionen / maximale Komplexität 30 / 0 Befunde.
- Architektur: 0 Befunde.
- Ereignisarchitektur/-register: 0 Befunde.
- Isolierte Python-Kompilierung bestanden.

## Nicht behauptet

Die sechs externen Stable-Gates bleiben offen: Ruff, MyPy, Bandit, pip-audit, physische KDE-X11-Abnahme und realer 96-Job-Slow-Target-Soak. Welle 23 verändert deren externen Nachweisstatus nicht.
