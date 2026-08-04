# Code- und Qualitätsbericht 2.8.3-rc11

## Schwerpunkt

Startaufsicht, UI-Bereitschaft, sicherer Rückfall und konfliktfreier Zweitstart.

## Ergebnis

- 192/192 Python-Tests bestanden
- 80,45 % Zeilenabdeckung
- 65,93 % Branch-Abdeckung
- 12/12 Anwendungssimulationen
- 16/16 visuelle Referenzen
- 0 Registrybefunde
- 0 Architekturbefunde
- 0 interne Qualitätsbefunde
- maximale Komplexität 28/30
- größte Python-Datei 655/700 Zeilen

## Neue Regressionen

- atomarer UI-Bereitschaftshandshake
- automatischer sicherer Zweitversuch
- verifizierter System-Python-Rückfall
- Fokusanforderung bei vorhandener Instanz
- Reparatur verlorener Laufzeitmarken ohne Neuinstallation
- Qualitätsumgebung bleibt aus dem Nutzerbootstrap ausgeschlossen
- Startprüfung verwendet keinen blockierenden Status
