# Iteration 39B · Core-vs.-Tk-Transfermatrix für PySide6/QML

Datum: 2026-09-04  
Quelle: 39A-Head `121211244d90932775348ac26039b3d7315e60b2`  
Zielarchitektur: PySide6/QML  
Status: Transferentscheidung vorbereitet; noch kein Produktcode portiert

## Entscheidungsregel

- **A · direkt**: GUI-/Toolkit-unabhängiger Vertrag oder Service. Transfer trotzdem erst nach komponentenspezifischem Test-Gate.
- **B · Adapter/Extraktion**: fachlich wertvoll, aber mit Tk-, Shell-, Plattform- oder Präsentationscode vermischt. Vor Übernahme trennen.
- **C · neu implementieren**: konkrete Tk-/Widget-/Layoutdarstellung. Nicht kopieren; Verhalten und Akzeptanzkriterien nativ in PySide6/QML umsetzen.

Die vollständige maschinenlesbare Entscheidung liegt in `A33_PYSIDE6_TRANSFER_MATRIX.json`.

## A · direkt wiederverwendbarer Core

| Komponente | Status | Warum |
|---|---|---|
| Error Contract · `error_handling.py` + `runtime_error_guidance.py` | READY_AFTER_COMPONENT_TEST | Fehlercodes, Registry, Klassifikation und Fingerprints sind GUI-frei |
| AppEvent Contract · `app_events.py` | READY_AFTER_COMPONENT_TEST | immutable/versionierte Ereignisgrenze, ideale Core↔Qt-Schnittstelle |
| Single Instance · `instance_lock.py` | READY_AFTER_COMPONENT_TEST | Toolkit-frei; Linux/POSIX-Lock + atomarer Focus Request |
| Startup Handshake · `startup_handshake.py` | READY_AFTER_COMPONENT_TEST | UI_READY-Prozessvertrag ohne Tk-Abhängigkeit |
| Architecture Audit | READY | AST-/Repository-Qualitätsgate unabhängig von UI |
| Release File Contract | READY | deterministische Paketgrenze, Cache-/Backup-/Bytecode-Ausschluss |
| Long Render Target | **BLOCKED_TEST_GAP** | technisch GUI-frei, aber reale Slow-Target-/Coverage-Evidence fehlt |

**Wichtig:** A bedeutet nicht automatisch „jetzt kopieren“. `long_render_target.py` bleibt zum Beispiel ausdrücklich blockiert, bis Unit-Gaps und der reale Slow-Target-Soak geschlossen sind.

## B · zuerst Adapter oder Core extrahieren

| Komponente | Transferaktion |
|---|---|
| `start.sh` + `STARTEN.sh` | CLI-/Preflight-Vertrag behalten, Qt-Entrypoint neu verdrahten |
| `scripts/debug_launcher.py` | Prozess-/Watchdog-Core vom Incident-Presenter trennen |
| `debug_runtime.py` | DebugIncident/Report Writer behalten, Tk-Dialog verwerfen |
| `runtime_error_hooks.py` | Never-Crash-Corehook von Tk-Handler/SolutionDialog trennen |
| `selection_preview_controller.py` | Preview-Worker behalten, Selection-Auflösung in Qt-Adapter verschieben |
| `theme.py` | WCAG-Kontrast + semantische Tokens extrahieren, ttk-Styles nicht portieren |
| `canonical_shell_contract.py` | Navigation/semantische UX-Regeln behalten, Pixel-/Tk-Layout verwerfen |
| A33-CI-Package-Workflow | Gate-Reihenfolge behalten, Qt-Offscreen/X11/Wayland-Umgebung neu definieren |

## C · bewusst nicht portieren

- `canonical_ui.py`
- `canonical_shell_workspace.py`
- `canonical_shell_chrome.py`
- `canonical_dashboard_mixin.py`
- `canonical_help_status_mixin.py`
- `canonical_kpi_detail_mixin.py`

Diese Dateien repräsentieren die Tk-Shell bzw. konkrete Widget-/Layoutimplementierung. Die PySide6/QML-Linie übernimmt daraus **keinen UI-Code**. Übernommen werden nur fachliche Akzeptanzkriterien wie Navigation, keine Doppel-Skalierung, Tastaturzugänglichkeit, verständliche Statusanzeige und sichtbare Fehlerführung.

## A33-Pflichtscope vollständig klassifiziert

Die acht A33-Prozess-/Produktpfade aus 39A sind vollständig in der Matrix vertreten:

1. `.github/workflows/a33-consolidated-package.yml` → B
2. `STARTEN.sh` → B
3. `start.sh` → B
4. `scripts/architecture_audit.py` → A
5. `scripts/release_file_contract.py` → A
6. `src/videobatch_fast/canonical_shell_contract.py` → B
7. `src/videobatch_fast/canonical_shell_workspace.py` → C
8. `src/videobatch_fast/canonical_ui.py` → C

## Empfohlene Reihenfolge nach Benutzerfreigabe

1. **AppEvent Contract** als kleinster, GUI-freier Grenzvertrag.
2. **Error Contract** als zweiter klarer Core-Slice.
3. **Startup Handshake + Single Instance** als Linux-Start-Core.
4. **Debug/Runtime Error** erst nach sauberer Core-/Presenter-Trennung.
5. **Selection Preview** erst nach Herauslösen der UI-Auswahlsemantik.
6. **Long Render Target** erst nach seinem eigenen Test-/Soak-Gate.
7. UI/Theme/Shell erst danach nativ in QML.

Die Reihenfolge ist eine Empfehlung, keine automatische Transferfreigabe.

## Automatische 39B-Gates

Der neue Vertragstest prüft:

- gültige Klassen A/B/C und Transferstatus;
- vollständige Abdeckung aller A33-Pflichtpfade;
- keine Tk-/PySide-/`ui_components`-Imports in direkt übernehmbaren Python-Dateien;
- `canonical_ui.py` und `canonical_shell_workspace.py` dürfen niemals als A markiert sein;
- `runtime_error_hooks.py`, `debug_runtime.py` und `theme.py` dürfen wegen ihrer aktuellen Tk-Kopplung niemals A sein;
- `long_render_target.py` muss bis zur realen Evidence als `BLOCKED_TEST_GAP` markiert bleiben;
- Quelle der Matrix bleibt exakt der eingefrorene 39A-Head.

## Stable-Gates bleiben unverändert

39B ist eine Architektur-/Transferentscheidung und schließt keinen Releaseblocker:

1. Coverage 80/65 bleibt offen.
2. Physische KDE-X11-/Wayland-Abnahme bleibt offen.
3. Large-Media-/Slow-Target-Soak bleibt offen.

## Nächster Schritt

Nach grünem 39B-Governance-Gate entscheidet der Benutzer anhand dieser Matrix, welcher **einzelne A-Komponenten-Slice** in die PySide6/QML-Linie übernommen wird. Empfohlen ist `application-event-contract`, weil er klein, immutable und GUI-frei ist.
