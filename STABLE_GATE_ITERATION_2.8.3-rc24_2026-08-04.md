# Stable-Gate-Iteration 2.8.3-rc24 vom 4. August 2026

## Kandidat und Umgebung

| Feld | Wert |
| --- | --- |
| Kandidatenkennung | `c934de8aa98fd3d1addaf81065b5375b8b4aef79` |
| Build | `2.8.3-rc24` |
| Qualitätslauf | 2026-08-04, 17:12:36–17:13:21 UTC |
| Betriebssystem | Ubuntu 24.04.4 LTS |
| Kernel | Linux 6.12.13, x86_64 |
| Desktop | nicht vorhanden oder nicht an die Prüfumgebung angebunden |
| Sitzungstyp | nicht gesetzt; keine Logind-Sitzung erreichbar |
| Anzeige | weder `DISPLAY` noch `WAYLAND_DISPLAY` gesetzt |

Der Arbeitsbaum war vor dem Lauf sauber. Die Kandidatenkennung blieb während des
Qualitätslaufs unverändert. Von der Werkzeugvorbereitung erzeugte lokale Dateien
wurden anschließend entfernt; sie gehören nicht zum dokumentierten Kandidaten.

## Ergebnis der vorgeschalteten Qualitätsprüfung

`./quality.sh` endete mit Status 43. Die gesperrten Versionen Ruff 0.16.1,
MyPy 2.3.0, Bandit 1.9.4 und pip-audit 2.10.1 waren vorhanden, aber jedes der vier
externen Qualitätswerkzeuge meldete `fail`. Der Lauf endete deshalb vor den
internen Prüfungen und vor pytest.

- **Ursache:** Jedes externe Werkzeug endete mit einem Fehlerstatus; der
  Gate-Treiber fasste die Einzelausgaben nur als `fail` zusammen, sodass die
  jeweilige Detailursache in diesem Lauf nicht erhalten blieb.
- **Auswirkung:** Der Qualitätslauf ist nicht bestanden. Für diesen Kandidaten
  darf weder die nachfolgende Releaseprüfung noch das Stable-Gate als bestanden
  gelten.
- **Automatische Schutzmaßnahme:** Der Lauf brach mit Status 43 ab. `./test.sh`
  wurde nicht gestartet, damit die vorgeschriebene Reihenfolge erhalten bleibt.
- **Lösung:** Die vier Einzelberichte in einer neuen Kandidateniteration sichern,
  die Befunde gezielt beheben und `./quality.sh` einmal für den neuen,
  unveränderten Kandidaten ausführen.
- **Alternative:** Wenn ein Werkzeug selbst fehlerhaft startet, zunächst nur die
  gesperrte Qualitätsumgebung reparieren und belegen; ein rotes Werkzeug darf
  nicht übersprungen oder als bestanden umgedeutet werden.

## Echte grafische Releaseprüfung

`./test.sh` wurde **nicht ausgeführt**. Neben dem roten Qualitätslauf stand in
dieser Umgebung keine echte grafische Sitzung zur Verfügung. Eine simulierte
Anzeige mit Xvfb wurde ausdrücklich nicht als Ersatz verwendet.

| Messwert | Ergebnis dieser Iteration |
| --- | --- |
| Testzahl | nicht erhoben, weil `./test.sh` nicht gestartet wurde |
| Zeilenabdeckung | nicht erhoben |
| Branch-Abdeckung | nicht erhoben |
| Kombinierte Coverage | nicht erhoben |
| Übersprungene Tests | keine beobachtet, da die Testsammlung nicht lief |

Damit ist das Gate **blockiert und nicht bestanden**. Die bereits veröffentlichten
Zahlen anderer Berichte werden nicht als Ergebnis dieser Iteration übernommen.

## Namespace-Isolierung

Die beiden zielsystemabhängigen Namespace-Tests
`PluginIsolationTests.test_validator_runs_in_os_isolation` und
`PluginIsolationTests.test_plugin_cannot_open_arbitrary_host_file` wurden in dieser Iteration
**nicht ausgeführt**. Sie wurden auch nicht als pytest-Übersprünge gezählt, weil
pytest wegen des vorgeschalteten roten Qualitätslaufs gar nicht gestartet wurde.

Die Namespace-Isolierung ist auf dem vorgesehenen Zielsystem daher nicht belegt.
Nach einem grünen Qualitätslauf muss `./test.sh` in einer echten Linux-Desktop-
Sitzung ausgeführt werden, in der User-, Netzwerk-, PID- und Mount-Namespaces
zugelassen sind. Beide genannten Tests müssen dort tatsächlich laufen; ein Skip
mit `Linux namespaces unavailable` hält dieses Gate weiterhin offen.

## Unveränderte offene Folgeprüfungen

1. Externe Qualitätsbefunde beheben und den Qualitätslauf für einen neuen
   unveränderten Kandidaten einmal wiederholen.
2. Danach `./test.sh` in einer echten X11- oder Wayland-Desktop-Sitzung ausführen
   und Testzahl, Coverage sowie alle Skips aus genau diesem Lauf dokumentieren.
3. Falls die beiden Namespace-Tests auf dem Zielsystem überspringen, denselben
   Kandidaten zusätzlich auf einem geeigneten Linux-Rechner mit freigegebenen
   Namespaces prüfen. Bis dahin bleibt das Isolationstor offen.
