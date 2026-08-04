# Testsystem 2.8.3-rc11

## Schreibender Build

`./build_artifacts.sh` erzeugt Designanalyse, visuelle Kandidaten, HTML-Prüfung und Release-Manifest. Dieser Schritt wird bewusst vor der Freigabe ausgeführt.

## Schreibgeschützte Vollprüfung

`./test.sh` validiert das Release-Manifest vor und nach allen Prüfungen. XDG-Daten, Coverage, Diagnosen und visuelle Kandidaten liegen in temporären Verzeichnissen. Standardmäßig sind Ruff, MyPy, Bandit und pip-audit verpflichtend.

## Externe Qualitätsstrecke

`./quality.sh` führt interne Gates, alle vier externen Werkzeuge und pytest-cov aus. Die Werkzeuge werden exakt über `requirements-quality.lock` installiert.

## Kernprüfungen

- Datenintegritäts- und Recoverytests
- Runner-Terminalereignis und Prozesseskalation
- Plugin-Namespace-/Chroot-/Seccomp-Isolierung
- Update-Kandidaten-Byteidentität
- 12 Anwendungssimulationen
- 16 visuelle Szenarien
- GUI-Rasterprofil-Roundtrip
- mindestens 74 % Kern-Coverage
- Dateigrößen- und Komplexitätslimits
