# Iteration 39B · Core-vs.-Tk-Transfermatrix für PySide6/QML

Datum: 2026-09-04  
Produkt: PROVOWARE VideoBatch Fast  
Ausgangsbasis: Iteration 39A, `121211244d90932775348ac26039b3d7315e60b2`  
Ziel: Nur fachlich belastbare A33-/39A-/A32.2-Härtung in eine spätere PySide6/QML-Linie übernehmen – keine Tk-Technik mitschleppen.

## Entscheidungssystem

- **A – direkt wiederverwendbar:** Core oder Vertrag ist toolkit-neutral. Der fachliche Code kann in die Qt-Linie übernommen werden.
- **B – Adapter/Entkopplung erforderlich:** Die Fachlogik ist wertvoll, aber mit Tk, Dialogen, Prozessdarstellung oder heutigen Shell-Annahmen vermischt. Erst trennen, dann übertragen.
- **C – nicht portieren:** Konkrete Tk-/ttk-Widget-, Layout-, Mainloop- oder Skalierungsimplementierung. In PySide6/QML nativ neu bauen.

Die maschinenlesbare Quelle ist `docs/architecture/PYSIDE6_QML_TRANSFER_MATRIX.json`. `tests/test_pyside6_qml_transfer_matrix.py` schützt die Klassifikation gegen versehentliche Rückvermischung.

## A · Direkt übernehmen

| Komponente | Warum | Qt-Aktion |
|---|---|---|
| `start.sh` | CLI-Routing, Hilfe, Doctor/Repair/Quality sind toolkit-neutral | Startvertrag beibehalten; GUI-Ziel hinter `STARTEN.sh` austauschbar halten |
| `STARTEN.sh` | Python-Preflight und klare Fehlerführung ohne GUI-Toolkit | beibehalten; `debug_launcher.py` als getrennte Adaptergrenze behandeln |
| `scripts/architecture_audit.py` | AST-/Dateiprüfung unabhängig von Tk; Never-Crash-Verhalten | auf neue Qt-Python-Module erweitern |
| `scripts/release_file_contract.py` | Release-Hygiene ist toolkit-neutral | QML/Qt-Ressourcen als normale Nutzdateien aufnehmen |
| `scripts/package_release.py` | deterministischer manifestgeführter Paketbau | unverändert weiterverwenden |
| `scripts/verify_release_zip.py` | ZIP-/Manifest-Integrität unabhängig von GUI | unverändert als Release-Gate behalten |
| `error_handling.py` | Fehlerdomänenmodell und Registry-Fallbacks ohne Tk | als Backend-Quelle für Qt-Fehlerdarstellung verwenden |
| `runtime_error_guidance.py` | Exception-Klassifikation, Position, Fingerprint ohne GUI | um `qt`/`qml`-Scope ergänzen, Kern nicht duplizieren |
| `RUNTIME_ERROR_REGISTRY.json` | menschenlesbarer Fehlervertrag unabhängig vom Toolkit | dieselben Action-IDs über Qt-Adapter bedienen |

### Bewertung

Diese Gruppe ist die risikoärmste erste Transferwelle. Besonders wichtig ist, dass Fehlercodes, Recovery-Texte, Paketverträge und Start-CLI **nicht** für Qt neu erfunden werden. Sie bilden die bereits geprüfte fachliche Kontinuität zwischen alter und neuer Oberfläche.

## B · Erst entkoppeln

| Komponente | Vermischung | Erforderlicher Schnitt |
|---|---|---|
| `scripts/debug_launcher.py` | Prozess-/Log-Wächter ist neutral, Incident-Dialog ist heutige UI | Monitoring-Core auslagern; Präsentation über Callback/Interface anbinden |
| `runtime_error_hooks.py` | Capture/Dedupe/Reporting plus `SolutionDialog` und `tk_exception_handler` | `runtime_error_core` + Qt-Exception-Bridge + Qt/QML-Presenter |
| `canonical_shell_contract.py` | semantische Navigation plus Notebook-Indizes/Pixelgeometrie | neutrales `NavigationModel` mit Route-IDs/Capabilities; keine Widget-Indizes |
| `.github/workflows/a33-consolidated-package.yml` | Governance neutral, Testumgebung mit Tk/Xvfb verknüpft | 80/65, Manifest und Packaging behalten; Qt-headless + reale X11/Wayland-Gates einsetzen |

### Wichtigster B-Schnitt: Fehlerbehandlung

`runtime_error_hooks.py` darf **nicht** als Ganzes kopiert werden. Die korrekte Trennung ist:

1. Exception erfassen,
2. stabil klassifizieren,
3. Fingerprint/Dedupe durchführen,
4. Incident/Evidence erzeugen,
5. daraus ein toolkit-neutrales Präsentationsmodell bilden,
6. erst am Rand durch PySide6/QML anzeigen.

QML soll also Daten erhalten – nicht Python-Widgetdialoge aufrufen.

### Zweiter B-Schnitt: Navigation

Aus `canonical_shell_contract.py` sind vor allem stabile semantische Kennungen wie `dashboard`, `media`, `queue`, `preview`, `diagnostics` und `settings` wertvoll. Nicht übernommen werden sollen feste `page_index`-Kopplungen, Notebook-Annahmen oder die Tk-spezifische Sidebar-Geometrie. In Qt sollen Route-IDs/Capabilities die Navigation bestimmen.

## C · Bewusst nicht portieren

| Komponente | Warum nicht | Qt-Ersatz |
|---|---|---|
| `canonical_ui.py` | `Tk()`, `mainloop`, Tk-Callbackhandler, Tk-Scaling, Mixin-App-Shell | neue `QApplication`/`QQmlApplicationEngine`-Composition |
| `canonical_shell_workspace.py` | `ttk.Frame`, `grid`, `ttk.Notebook`, Bindings, `trace_add` | QML `StackLayout`/`Loader`, Models, Properties und Signals |
| `canonical_shell_chrome.py` | `ttk.Style`, `StringVar`, `TclError`, Tk-Widgetaufbau | QML Controls + zentraler Token-/Theme-Layer |

Das bedeutet ausdrücklich **nicht**, dass Informationshierarchie, Begriffe oder Bedienkonzept verworfen werden. Nur die konkrete Tk-Ausführung wird nicht übertragen.

## Was aus A33 fachlich erhalten bleibt

- laienfreundliche Start-/Diagnoseführung,
- sichere Python-Preflight-Logik,
- Never-Crash-Architekturprüfung,
- kompakte Informationshierarchie und semantische Navigationsbereiche,
- Respekt vor Systemskalierung statt Doppel-Skalierung,
- reproduzierbare Packaging-/Manifest-Governance,
- zentrale verständliche Fehlercodes, Lösungen und Recovery-Evidence.

## Was nicht in Qt übernommen wird

- `ttk`-Styles,
- `grid`-Geometrie,
- `ttk.Notebook` und dessen Seitenindizes,
- `StringVar`/`trace_add`,
- `Tk()`/`mainloop`,
- `report_callback_exception`,
- `VIDEOBATCH_TK_SCALING`,
- Tk-spezifische Dialogklassen,
- alte Pixelbreiten als Architekturvertrag.

## Empfohlene Transferreihenfolge

1. Fehlerdomänenmodell + Registry + Guidance.
2. Release-/Packaging-/Audit-Governance.
3. Shell-Startvertrag + Python-Preflight.
4. Runtime-Error-Core aus Tk-Präsentation herauslösen.
5. Debug-Monitoring aus GUI-Präsentation herauslösen.
6. semantisches NavigationModel extrahieren.
7. neue PySide6/QML-App-Shell nativ aufbauen.
8. Workspace, Chrome und Theme nativ in QML umsetzen.

Diese Reihenfolge minimiert das Risiko: Zuerst wird geprüftes Verhalten konserviert, danach werden Adapter geschaffen, und erst zuletzt entsteht die neue Darstellung.

## Unveränderte Release-Gates

39B ist eine Architekturentscheidung, keine Stable-Freigabe. Deshalb bleiben unverändert:

- Zeilen-Coverage >= 80 %, aktuell 39A: 73,16 % → blockiert.
- Branch-Coverage >= 65 %, aktuell 39A: 58,82 % → blockiert.
- physische Kubuntu/KDE-X11-Abnahme.
- physische Kubuntu/KDE-Wayland-Abnahme.
- realer Large-Media-/Long-Render-Soak auf langsamem externem Ziel.

Keines dieser Gates wird für die Qt-Migration abgesenkt oder umgangen.

## Nächster Implementierungsschritt nach 39B

**39C – Toolkit-neutralen Runtime-Error-Core extrahieren.**

Das ist der beste erste echte Code-Transfer, weil er hohen Robustheitsnutzen hat, die Qt-Linie nicht mit Tk belastet und anschließend sowohl Tk als auch PySide6/QML denselben Fehlerkern verwenden können. Erst wenn dieser Schnitt mit Regressionen grün ist, sollte eine Qt-App-Shell erzeugt werden.
