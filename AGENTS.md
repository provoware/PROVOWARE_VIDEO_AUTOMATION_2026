# AGENTS.md

## Produktziel und Prioritäten

`provoware – videoautomation – 2026` ist eine robuste, laienfreundliche Linux-Anwendung für lokale FFmpeg-Automatisierung.

Prioritäten gelten in dieser Reihenfolge:

1. **abruchsfreie Lauffähigkeit und sichtbare Fehlerdiagnose**,
2. **Datenintegrität und unveränderte Originalmedien**,
3. **verständliche Bedienung und Wiederherstellung**,
4. **Codesparsamkeit und Wartbarkeit**,
5. **Performance und Ressourcenschonung**,
6. **Erscheinungsbild und Komfort**.

Ein optischer oder architektonischer Umbau darf niemals einen nachgewiesenen stabilen Startpfad verschlechtern.

## Effiziente Entwicklungsregel

Jede Änderung folgt strikt diesem Ablauf:

1. **Reproduzieren:** realen Fehler, Screenshot, Log oder eindeutig fehlende Funktion erfassen.
2. **Eingrenzen:** kleinste verantwortliche Stelle bestimmen; keine Nachbarbereiche vorsorglich umbauen.
3. **Minimal korrigieren:** vorhandene Funktionen, Module, Tests und Prüfpfade wiederverwenden.
4. **Gezielt prüfen:** zuerst nur den betroffenen Vertrag/Test ausführen.
5. **Lokal integrieren:** erst danach die passende bestehende Sammelprüfung ausführen.
6. **Automatisch absichern:** GUI-, Start-, Datei- und Renderänderungen mit fokussierten Simulationen, Smoke- und Regressionstests kontrollieren; reale vollständige Zielsystemabnahme erst am final eingefrorenen Releasekandidaten.
7. **Finalisieren:** Release-Manifest und Abschlussberichte erst aus dem endgültigen, unveränderten Dateibaum erzeugen.

Nur **reproduzierbare Befunde** werden korrigiert. Vermutete Probleme werden zuerst als Hypothese dokumentiert und nicht durch spekulative Architektur beantwortet.

## Scope- und Patchbudget

- Ein Patch bearbeitet **ein klar benennbares Problem oder einen eng zusammengehörigen Befundblock**.
- Bevorzugt werden höchstens **3 Produktdateien + 1 fokussierte Testdatei** pro Einzelbefund. Größere Änderungen benötigen eine dokumentierte technische Notwendigkeit.
- **Vor einer neuen Datei** prüfen, ob eine bestehende verantwortliche Datei die Änderung verständlich aufnehmen kann.
- **Vor einer neuen Abstraktion** prüfen, ob eine kleine Funktion oder Dataclass genügt.
- Keine Abstraktion nur für einen einzelnen Aufrufer, außer sie bildet eine echte Sicherheits-, Prozess- oder Persistenzgrenze.
- Keine neue Mixin-Schicht, wenn eine reine Hilfsfunktion oder ein bestehendes Modul genügt. Änderungen an der MRO benötigen einen fokussierten Vertragstest.
- Keine parallelen Implementierungen derselben Funktionalität. Alte Pfade werden nach nachgewiesener Migration entfernt oder ausdrücklich als Kompatibilitätsgrenze markiert.
- Standardbibliothek und vorhandene Abhängigkeiten haben Vorrang vor neuen Paketen.
- Kommentare erklären **warum**, nicht den unmittelbar lesbaren Code.

## Größen- und Komplexitätsziele

- Neue Produktmodule: bevorzugt **≤ 400 Zeilen**, hart **≤ 700 Zeilen**.
- Bestehende große Module dürfen durch eine Änderung nicht weiter wachsen, wenn dieselbe Aufgabe durch Extraktion oder Vereinfachung kleiner gelöst werden kann.
- Funktionen: bevorzugt **≤ 40 Zeilen** und geringe Verzweigung; harte Projektgrenzen werden vom vorhandenen Qualitätsgate bestimmt.
- Wiederholte Bedingungen, Stringkonstanten, Pfadlogik und Fehlerformatierung werden an **einer** Stelle gehalten.
- Maschinenlesbare Quellen bleiben maßgeblich. Zahlen wie Coverage-, Versions- oder Dependency-Grenzen werden nicht zusätzlich in `AGENTS.md` dupliziert, wenn bereits eine kanonische Konfiguration existiert.

## Verbindliche Laufzeit- und Sicherheitsregeln

1. Offline- oder fehlende Projektpfade niemals automatisch löschen.
2. Originalmedien niemals verändern, um einen Fehler zu reparieren.
3. Ausgabeziele vor Prozessstart exklusiv reservieren.
4. Dateiablagen nur transaktional, journalisiert und nach erforderlicher Integritätsprüfung abschließen.
5. Jeder Hintergrundvorgang liefert genau ein terminales Abschlussereignis.
6. Prozessabbrüche, externe Programme und Worker besitzen feste Zeitgrenzen; keine unbegrenzten Wiederholungsschleifen.
7. Start-, Import-, UI-Aufbau- und Callbackfehler müssen an einer äußeren Grenze erfasst werden und dürfen nicht still verschwinden.
8. In Start-, Speicher-, Recovery- und Produktionspfaden ist `except Exception: pass` verboten. Bewusst best-effort ausgeführte UI-Aufräumarbeiten müssen eng begrenzt sein und dürfen keinen relevanten Fehler verschlucken.
9. Ein Startfehler muss mindestens **Was? Wie? Wo? Lösung?** ausgeben und einen lokalen Diagnosepfad nennen.
10. Der persistente Debugmodus bleibt standardmäßig aktiv, bis der Benutzer ihn im Tool ausschaltet. Absturzberichte bleiben lokal und werden nicht automatisch versendet.
11. Ein normaler Programmabschluss muss vom Crash-Wächter unterscheidbar sein.
12. `shell=True`, `os.system` und `tempfile.mktemp` sind verboten.
13. Plugins nur mit vorhandenen Sicherheits-, Berechtigungs- und Isolationsverträgen ausführen; fehlende Capabilities fail-closed behandeln.
14. Private Schlüssel dürfen niemals Bestandteil eines Releasepakets sein.

## Ereignisarchitektur

- Ereignisproducer liefern `AppEvent`; freie `(name, payload)`-Tupel sind verboten.
- Nicht migrierte Producer verwenden ausschließlich die bestehende Legacy-Grenze.
- Ereigniskennung, Payloadtyp, UI-Handler, Terminal-/Noisy-Klassifizierung und Vertragstest bleiben zentral konsistent registriert.
- Ein neuer Ereignistyp wird nicht eingeführt, wenn ein bestehender Typ semantisch korrekt erweitert werden kann.

## UI- und Musterentwicklung

- Die reale Benutzeroberfläche wird **nicht aus Erinnerung** an ein Muster umgebaut.
- Bei einem Mustervergleich müssen zuerst Referenzbild und tatsächlicher Screenshot für dieselbe relevante Situation vorliegen.
- Für die aktuelle reale Zielsystemabnahme gilt `docs/KUBUNTU_26_04_QT_ABNAHME.md`; ältere Bildvergleichschecklisten liegen nur noch im historischen Archiv.
- Vor dem ersten UI-Patch wird eine vollständige Soll/Ist-Liste erstellt: Struktur, Maße, Proportionen, Typografie, Farben, Abstände, Zustände, Clipping und Überlagerungen.
- Reihenfolge der UI-Korrektur: **Absturz → Überlagerung/Clipping → unerreichbare Bedienung → falsche Geometrie/Proportion → Typografie → Farbe/Feinschliff**.
- Ein UI-Punkt gilt während der Entwicklung erst als **technisch geprüft**, wenn passende automatisierte Tests beziehungsweise nachvollziehbare Bildvergleiche vorliegen. Als **real abgenommen** gilt er erst nach der gebündelten Sicht- und Bedienprüfung am finalen Releasekandidaten; ein statischer Vertrag allein ersetzt diese nicht.
- Pixel-, Zonen- und Mindestabstandswerte werden erst nach Messung eines bestätigten Musters festgeschrieben; keine erfundenen Sollwerte.
- Der geometrische GUI-Wächter wird nach der Bildkorrektur mit den bestätigten Sollbereichen und Mindestabständen erweitert.
- Das Designmanifest bleibt internes Regelwerk für Tool und Untermodule; es ist **kein eigener GitHub-Merge-Blocker**.

## Prüfstrategie: schnell vor teuer

Die kleinste passende Prüfung läuft zuerst. Keine vollständige Releasekette für eine reine Text- oder Layout-Hilfsänderung.

Bevorzugte Reihenfolge:

```bash
./test.sh --docs   # nur Dokumentation
./test.sh --core   # Kernverträge ohne externe Qualitätswerkzeuge
./verify_release.sh # praktische lokale Qualitätsprüfung
```

Die strenge reproduzierbare Releaseprüfung wird nur auf einem finalen Kandidaten ausgeführt:

```bash
./verify_release.sh --strict
```

Zusätzlich gilt:

- Bestehende Test- und Prüfpfade erweitern statt neue parallele Runner oder GitHub-Workflows einzuführen.
- Ein neuer GitHub-Workflow oder neuer Required-Status benötigt einen nachgewiesenen, nicht lokal oder in einem bestehenden Workflow lösbaren Bedarf.
- Lokale Design-, Dokumentations- oder Hilfsverträge werden nicht allein deshalb zu Merge-Gates gemacht.
- Keine leeren Trigger-Commits und keine wiederholten Neustarts unveränderter Jobs.
- Tests dürfen manifestierte Paketdateien nicht verändern.
- Schreibende Build-Schritte und lesende Verifikation bleiben strikt getrennt.

## Gestaffelte Prüfung: Entwicklung, Integration, finale Release-Abnahme

**Während der Entwicklung:** Jeder PR braucht passende automatisierte Tests, Architektur-/Sicherheits-/Datenvertragsprüfungen und nachgewiesene Integrationsfähigkeit. Betroffene Start-, Qt-/GUI-, Rendering-, Speicher- und Wiederanlaufpfade werden mit bestehenden automatisierten Smoke-, Simulations- und Regressionstests abgesichert. Offene Fehler und fehlende reale Prüfungen werden sichtbar dokumentiert, nicht als PASS ausgegeben. Die eigene dokumentierte Code- und Risikoprüfung genügt; ein externer oder unabhängiger Reviewer und eine fremde GitHub-Approval sind bei diesem Privatprojekt keine Voraussetzung.

**Bei Integration nach `main`:** Nur passende automatische Pflichtprüfungen für den unveränderten PR-Commit und nachvollziehbare Konfliktprüfung. Ein PR mit bekannten kritischen Laufzeit- oder Datenverlustfehlern bleibt gesperrt. Ein erfolgreiches CI-Ergebnis ist eine *Integrationsentscheidung*, keine Releasefreigabe. Es ist **keine** wiederholte vollständige persönliche Kubuntu-/Sichtabnahme für jeden Entwicklungs-PR erforderlich.

**Einmal am Entwicklungsende, kurz vor Release:** Nach Bündelung aller gewünschten Funktionen und Oberflächenänderungen wird der Endkandidat eingefroren. Erst dann erfolgen die vollständige reale Zielsystemabnahme auf **Kubuntu 26.04 · KDE Plasma · natives Wayland** (einschließlich 100/125/150/200 %), echter Programmstart, visuelle Bedienungsprüfung, reale FFmpeg-Ausgabe und der vorgeschriebene Langzeitrender. Danach vollständige finale Prüfkette und Veröffentlichung. Jede anschließende Änderung an abnahmerelevanten Funktionen macht nur die davon betroffenen Belege ungültig; der abschließende Gesamtvertrag muss zum endgültig unveränderten Kandidaten passen.

Nicht ausgeführte Prüfungen heißen ausdrücklich **offen**. Keine Simulation wird als reale Abnahme ausgegeben. Historische RC24-Nachweise bleiben archiviert und werden nicht zur Integration aktueller Entwicklungsstände vorausgesetzt.

## Release- und Manifestdisziplin

- Produktname, Version, Build und Kanal ausschließlich aus `VERSION.json` beziehungsweise der dafür vorhandenen kanonischen Versionslogik lesen.
- Abhängigkeiten ausschließlich über die vorhandenen Lock-/Toolchainverträge festlegen.
- `RELEASE_MANIFEST.json` **genau einmal** nach dem endgültigen Dateibaum regenerieren und danach nur noch read-only prüfen.
- Nach einer Änderung am finalen Dateibaum ist die vorherige Manifestabnahme ungültig.
- README, STATUS, CHANGELOG und andere Berichte werden nur aktualisiert, wenn sich deren tatsächliche Aussage ändert; kein pauschaler Dokumentationschurn pro Iteration.
- Stable-Gates werden pro unverändertem Kandidaten einmal vollständig ausgeführt. Nach einer Codeänderung beginnt eine neue Kandidateniteration.

## Git- und PR-Disziplin

- Branch vom aktuellen `main` erstellen; vor PR-Eröffnung `behind_by = 0` anstreben.
- Kleine, nachvollziehbare Commits; keine Commitserien nur zum Auslösen von Infrastruktur.
- PR bleibt Draft, solange zutreffende automatisierte Pflichtprüfungen, eigene Code- und Risikoprüfung oder relevante Integrationsvoraussetzungen offen sind; eine fremde Review-Freigabe wird nicht verlangt. Die persönliche Kubuntu-/Sichtabnahme ist erst am eingefrorenen Releasekandidaten Pflicht.
- Keine automatische Mergefreigabe aufgrund eines einzelnen grünen Signals.
- Kein weiterer Workflow, Statuskontext oder Infrastrukturpatch, wenn derselbe Nachweis einfacher lokal oder im bestehenden Prüfpfad möglich ist.

## Abschluss jeder Entwicklungsiteration

Kurz und prüfbar dokumentieren:

- **geändert:** welche reale Ursache behoben wurde,
- **geprüft:** welche Befehle/Läufe tatsächlich erfolgreich waren,
- **offen:** welche reale Abnahme noch fehlt,
- **Risiko:** was durch die Änderung bewusst nicht angefasst wurde,
- **nächster Schritt:** genau der kleinste technisch folgende Schritt.

Ziel ist nicht maximale Änderungsmenge, sondern der **kleinste nachweisbar richtige Fortschritt**.
---

## PROVOWARE GLOBAL DEVELOPMENT CONTRACT

Dieser globale Kern gilt zusätzlich zu den projektspezifischen Regeln. Bei Sicherheits- oder Nachvollziehbarkeitskonflikten hat er Vorrang; lokale Regeln dürfen ihn verschärfen, nicht stillschweigend abschwächen.

- **Frozen Current Plan:** Laufenden freigegebenen Plan nicht durch neue Ideen erweitern; Neues in die nächste Iteration einordnen.
- **Conflict Gate:** Unterbrechen nur bei nachgewiesenem Konflikt mit Planvoraussetzung, Sicherheit, Ausgangs-SHA, Scope oder Invariant.
- **Single Writer:** Pro produktivem Scope nur ein autorisierter Executor; Analyse/Planung/Prüfung dürfen parallel lesen.
- **SHA + Scope:** Vor Mutation HEAD und erlaubten/verbotenen Scope prüfen; keine stillen Nebenrefactorings.
- **Evidence:** Kein PASS ohne echten Test; Evidence muss zum geprüften HEAD gehören.
- **Controlled Evidence Lab:** Echte Mutationen, Fehler-Injektion und Recovery-Tests nur in isolierten Testbereichen; Produktivdaten bleiben geschützt.
- **Next Queue:** Neue Anforderungen/Findings append-only erfassen und Beziehungen wie BLOCKS, REQUIRES, SUPERSEDES, DUPLICATE oder CONFLICTS dokumentieren.
- **Statusklarheit:** OBSERVED/SUSPECTED/REPRODUCED/CONFIRMED/DISPROVED nicht vermischen.
- **Recovery Key:** Nach Abbruch oder Agentenwechsel müssen Stand, Ziel, Frozen Plan, Scope, Findings, Gates und nächster erlaubter Schritt ohne alten Chat rekonstruierbar sein.
- **Traceability:** Requirement/Decision → Finding → Plan → Change → Test/Evidence → Gate/Checkpoint nachvollziehbar halten.
- **Negativtests:** Schutzmechanismen absichtlich gegen falschen SHA, zweiten Writer, Scope-Verstoß und unbelegtes PASS testen.
- **Sichtbarer Fortschritt:** Längere Prüfungen mit Schritt, Fortschritt, Ergebnis und Ampelstatus darstellen.

Leitsatz: **Kein Agent muss sich erinnern. Kein Agent darf raten. Keine Änderung verliert ihren Ursprung. Kein PASS existiert ohne Evidence.**


## Benutzer-Hauptordner (8-Dateien-Vertrag)

- Im Git-Repository und im unverpackten Benutzerpaket liegen höchstens acht direkte Dateien im Hauptordner. Versteckte Dateien zählen mit; Ordner zählen nicht.
- `STARTEN.sh` und `README.md` bleiben direkt sichtbar; technische Start-/Prüf-/Installationsskripte liegen unter `scripts/`.
- Die Pfade in `config/`, `registries/`, `scripts/`, `resources/` und `docs/` sind Teil des Versions-, Installer-, CI- und Paketvertrags. Beim Umzug Referenzen und Tests gemeinsam aktualisieren.
- Historische RC24-Freigaben bleiben unverändert; reine Entwicklungsläufe bedeuten keine Stable-Freigabe.


## Draft-PR-Schuldenbremse und Qualitätsvorrang (29.10.2026)

Die GitHub-PR-Bestandsaufnahme gehört **vor die Planung neuer optionaler Arbeiten**. Für offene Draft-PRs je Repository gilt: **0–5 = normal**, **6–10 = P1-Abarbeitung**, **ab 11 = P0-Abarbeitung**. Zielbestand: **höchstens fünf Drafts**. Maßgeblich ist die live über GitHub ermittelte Anzahl; bei API-Fehler/fehlendem Zugang lautet der Status UNBEKANNT, niemals 0.

- Bei Überschreiten der Grenze ist die **bestehende priorisierte To-do/Next Queue** maßgeblich: zuerst offene Arbeiten nach tatsächlichem Nutzen, Risiko, Alter, Blockern und Abhängigkeiten abarbeiten. Neue optionale Features zunächst nur dort vormerken, **keine zusätzlichen Drafts auf Vorrat**.
- Für jeden Draft den aktuellen HEAD, Zweck, Review, CI, Mergekonflikte, Sicherheitswirkung und Beziehungen (BLOCKS, REQUIRES, DUPLICATE, SUPERSEDES) erfassen. Klassifizieren: MERGE-BEREIT, KORREKTUR, BLOCKIERT, DUPLIKAT, ÜBERHOLT, GEPLANT.
- **Qualität vor Menge:** Fertigstellen mit minimaler Korrektur und passenden Negativ-/Regressionstests; Review, aktuelle CI, Schutzregeln und Abhängigkeiten vor Merge prüfen. Grün auf einem alten Commit ist kein Integrationsnachweis; grün auf PR-HEAD ersetzt nicht die Main-Nachkontrolle.
- **Nichts blind schließen oder mergen.** Duplikate/überholte Drafts nur mit Begründung, Quellen-/Nachfolgerverweis und gesichertem Arbeitsinhalt schließen. Unfertige Originalarbeit bleibt erhalten. Von Draft auf reviewbereit nur nach nachweislich erfüllten Projekt-Gates wechseln.
- Nach jedem Abschluss erneut zählen und in der To-do-Aufgabe dokumentieren: **vorher → nachher**, getesteter HEAD, Ergebnis, offene Blocker, nächste konkrete Handlung. Erst bei ≤5 Drafts wieder regulär optionale neue PRs priorisieren.
- **Ausnahmen:** P0-Sicherheits- und Datenintegritätsprobleme, zwingende Release-Gates und ein bereits freigegebener eingefrorener Plan haben Vorrang. Diese Regel **hebt keinen Freeze und keine Release-/Merge-Freigabe** auf. Bestehende kanonische/generierte To-do-Ansichten nicht manuell umschreiben; vorhandenen Generator bzw. Aufgaben-Workflow verwenden.

Zugehörige priorisierte GitHub-Aufgabe: https://github.com/provoware/PROVOWARE_VIDEO_AUTOMATION_2026/issues/294.
