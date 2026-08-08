# Scheduler Environment Baseline Audit – Fortsetzungswelle 24

## Ergebnis

Fortsetzungswelle 24 trennt Forecast-Messwerte nach renderrelevanter Laufzeitumgebung und führt kontrollierte Performance-Epochen ein. Prognosen aus deutlich unterschiedlichen CPU-/Thread-, FFmpeg-, Encoder- oder Zielmediumzuständen werden nicht mehr unbemerkt vermischt. Eine anhaltende Leistungsverschiebung innerhalb derselben Umgebung kann eine neue Baseline-Epoche eröffnen, ohne ältere Messungen zu löschen.

## Umgesetzte Verträge

1. Datensparsames Environment-Profil ohne Hostname oder Benutzerkennung.
2. Profilmerkmale: Maschinenarchitektur, CPU-Modell, CPU-Anzahl, Threadlimit, FFmpeg-Version, SHA-256 der FFmpeg-Buildkonfiguration, Encoderpfad sowie Ziel-Dateisystem-/Mediumklasse.
3. SHA-256-Environment-Fingerprint über ausschließlich renderrelevante Profilfelder.
4. Software-Codecwechsel allein erzeugt keinen falschen Environment-Wechsel; Hardware-/Encoderpfadwechsel bleibt getrennt.
5. Erfolgreiche BatchJournale speichern das beim realen Start eingefrorene Environment-Profil inklusive Performance-Epoche.
6. Live-Forecasts bevorzugen ausschließlich Samples derselben Umgebung und aktiven Epoche.
7. Frühere Epochen derselben Umgebung dürfen nur als expliziter Low-Confidence-Fallback verwendet werden.
8. Fremde Umgebungen werden ohne Legacybasis nicht als Forecast-Training missbraucht.
9. Legacy-Historie aus Welle 23 und früher bleibt lesbar und migrationskompatibel.
10. Automatisches Re-Baselining bei mindestens zehn passenden Beobachtungen und einer anhaltenden Medianverschiebung von mindestens 35 Prozent.
11. Alte Epochen werden archiviert und bleiben auditierbar; maximal 20 Epochen je Environment werden im aktiven Registry-Vertrag behalten.
12. Re-Baselining wird zentral nach erfolgreichen realen Batchabschlüssen geprüft und lernt dadurch auch aus manuellen GUI-Läufen.
13. Scheduler-Actual-vs-Predicted-Evidence enthält Environment-ID, Epoch-ID, Environment-Match und tatsächliche Sekunden pro Job.
14. Qualitätsbericht unterscheidet `environment_change`, `performance_drift_same_environment`, `forecast_model_drift`, `watch` und `stable`.
15. Operations-UI zeigt aktuelle Environment-/Epoch-Information und Drift-Ursache.
16. Scheduler-Export enthält zusätzlich `forecast-environment-epochs.json`.
17. Forecast/Dry-Run ist strikt read-only: Das Ermitteln einer Prognose darf kein Epochenregister oder andere State-Datei anlegen.
18. Re-Baselining ist nicht kritisch für den Rendererfolg; Fehler der Evidence-/Baseline-Schicht dürfen einen erfolgreichen Batch nicht umklassifizieren.

## Methodische Entscheidungen

- FFmpeg stellt `-version` und `-buildconf` als offizielle Build-/Versionsdiagnostik bereit. Deshalb werden Version und ein SHA-256 der Buildkonfiguration getrennt gebunden.
- Python `platform` liefert portable Maschinen-/Prozessorinformationen. Hostname und Netzwerkname werden bewusst nicht aufgenommen.
- Environment und Renderkonfiguration bleiben getrennte Ebenen: Codec/Profil/Auflösung sind weiterhin Forecast-Signaturmerkmale; die Environment-ID beschreibt die Ausführungsumgebung.
- Ein Umgebungswechsel wird nicht mit Modell-Drift gleichgesetzt. Die Ursache wird separat klassifiziert, damit eine reale Hardware-/FFmpeg-/Zieländerung nicht fälschlich als schlechtes Forecast-Modell erscheint.
- Drift führt nicht zur Löschung historischer Daten. Stattdessen entsteht eine neue Epoche; die alte Baseline bleibt forensisch erhalten.
- Automatisches Re-Baselining braucht mindestens fünf ältere und fünf jüngere passende Messwerte und mindestens 35 % robuste Medianverschiebung. Dadurch reagiert das System nicht auf einzelne Ausreißer.

## Externe Referenzen

- FFmpeg-Dokumentation: `-version` zeigt die Version und `-buildconf` die Buildkonfiguration: https://ffmpeg.org/ffmpeg.html
- Python `platform`: Maschinen- und Prozessorinformationen: https://docs.python.org/3/library/platform.html
- NIST AI RMF Playbook, MEASURE 2.4: Produktionsmetriken überwachen und Drift gegenüber früheren Leistungsindikatoren dokumentieren: https://airc.nist.gov/airmf-resources/playbook/measure/
- NIST Engineering Statistics Handbook: Drift über zeitlich geordnete Residuen/Messwerte beobachten: https://www.itl.nist.gov/div898/handbook/pmd/section4/pmd443.htm

## Finaler Teststand

- 686/686 Tests bestanden.
- Coverage: 81,35 % Lines / 65,33 % Branches / 77,98 % kombiniert.
- Coverage-Mindestvertrag 80/65 bestanden.
- Interne Codequalität: 336 Dateien / 2.960 Funktionen / maximale Komplexität 30 / 0 Befunde.
- Architektur: 0 Befunde.
- Ereignisarchitektur/-register: 0 Befunde.

## Nicht behauptet

Die sechs externen Stable-Gates bleiben offen: Ruff, MyPy, Bandit, pip-audit, physische KDE-X11-Abnahme und realer 96-Job-Slow-Target-Soak. Welle 24 verändert deren externen Nachweisstatus nicht.
