# VideoBatch Fast · Videos aus Audio, Bildern und Clips

Mit VideoBatch Fast erstellst du aus Audiodateien, Bildern und Videoclips fertige Videos auf deinem Rechner. Du wählst die Quellen und einen Ausgabeordner aus; das Programm prüft die Aufträge und verarbeitet sie nacheinander. Programmierkenntnisse brauchst du dafür nicht.

**Der einfache Ablauf:** Dateien auswählen → Ausgabe festlegen → Videos erstellen.

> **Vor dem Einstieg:** Die Anwendung ist für **Kubuntu 26.04 LTS mit KDE Plasma und Wayland** vorgesehen. Sie befindet sich in Entwicklung; eine **Stable-Version** (abschließend freigegebene Version) ist noch nicht veröffentlicht. Beginne mit einem kurzen Testauftrag und Kopien deiner Medien.

[Zum Schnellstart](#schnellstart) · [Erstes Video](#erstes-video-erstellen) · [Hilfe bei Fehlern](#wenn-etwas-nicht-klappt) · [Anleitungen](#dokumentation) · [Technischer Hintergrund](#für-entwicklung-und-prüfung)

## Was du damit machen kannst

- Audio mit Bildern oder Videoclips zu Videos verarbeiten.
- Mehrere Aufträge sammeln und nacheinander erstellen lassen.
- Bildgröße, Qualität, Effekte und Blenden einstellen.
- Quellen in der Vorschau kontrollieren und den Fortschritt verfolgen.

Die Originalmedien werden nicht überschrieben. Die fertigen Videos landen im ausgewählten Ausgabeordner.

## Was du brauchst

- **Kubuntu 26.04 LTS**, KDE Plasma und eine **Wayland-Sitzung**. Wayland ist die verwendete grafische Sitzung; Hinweise dazu stehen in der [Installationsanleitung](docs/start/AUTOINSTALLATION_save_.md).
- Das **vollständig entpackte Projektpaket** in einem eigenen Ordner.
- Für den ersten Test **eine kurze Audiodatei und ein Bild oder einen Videoclip**.
- Einen Ordner, in dem du Dateien speichern darfst, und ausreichend freien Speicherplatz.

Der Starter prüft benötigte Programmteile und Medienwerkzeuge wie FFmpeg, das die Videos erzeugt. Falls etwas fehlt, lies die angezeigte Meldung und die [Installationsanleitung](docs/start/AUTOINSTALLATION_save_.md).

## Schnellstart

### 1. Projekt herunterladen und entpacken

Lade das vollständige Projekt-ZIP herunter und entpacke es in einen neuen Ordner. Auf GitHub findest du den Quellcode über **Code → Download ZIP**. Das ist der aktuelle Entwicklungsstand; ein heruntergeladenes ZIP bedeutet keine Stable-Freigabe.

Öffne den entpackten Ordner. Darin müssen **`STARTEN.sh`**, **`README.md`** sowie die Unterordner **`src`** und **`scripts`** liegen. Starte das Programm erst nach dem Entpacken.

### 2. Terminal in diesem Ordner öffnen

Ein Terminal ist ein Fenster zur Eingabe von Befehlen. Öffne es im Dateimanager im entpackten Projektordner, zum Beispiel über den Eintrag **„Terminal hier öffnen“** im Kontextmenü. Je nach Dateimanager kann die Bezeichnung abweichen.

### 3. Programm starten

Kopiere diesen Befehl ins Terminal und drücke die Eingabetaste:

```bash
bash ./STARTEN.sh
```

Damit musst du die Dateiberechtigung des Starters nicht ändern. Der Starter prüft die Voraussetzungen; anschließend sollte sich die Oberfläche öffnen.

<details>
<summary>Alternative: Starter direkt ausführen</summary>

Mache den Starter einmal ausführbar:

```bash
chmod +x STARTEN.sh
```

Danach startest du ihn mit:

```bash
./STARTEN.sh
```

Beide Wege verwenden denselben Starter und dieselben Vorprüfungen.

</details>

## Erstes Video erstellen

| Schritt | Das machst du | Daran erkennst du den nächsten Schritt |
|---|---|---|
| **1 · Dateien** | Über **„Audio auswählen …“** eine kurze Audiodatei hinzufügen. Über **„Bilder/Videos auswählen …“** ein Bild oder einen Clip ergänzen. | Beide Listen enthalten deine Quellen; die Vorschau zeigt die ausgewählte Datei. |
| **2 · Ausgabe** | Zunächst die vorgeschlagenen Einstellungen verwenden und einen eigenen **Ausgabeordner** wählen. | Der Zielpfad zeigt auf den gewünschten Ordner. |
| **3 · Produktion** | Kontrollieren, welche Quellen zusammen verarbeitet werden. **„Prüfen & Videos erstellen“** wählen; bei großer Schrift kann die Schaltfläche **„Prüfen & Starten“** heißen. | Die Vorprüfung läuft, danach siehst du den Fortschritt und die Abschlussmeldung. |

### Abschlussprüfung

Öffne die erzeugte Datei im Ausgabeordner und spiele Anfang, Mitte und Ende ab. Prüfe Bild, Ton und Dateiname. Erst wenn der kurze Test passt, beginne mit größeren Aufträgen.

Die ausführliche [Schritt-für-Schritt-Anleitung](docs/start/START_HIER_save_.md) erklärt auch die Dateiauswahl über mehrere Ordner und die Ergebnisprüfung.

## Ansicht und Bedienung anpassen

- **Größere Schrift:** Über **„Schrift“** kannst du die Ansicht zwischen 80 und 200 Prozent einstellen.
- **Per Tastatur vergrößern oder verkleinern:** `Strg` + `Alt` + `↑` beziehungsweise `↓`. Mit `Strg` + `Alt` + `0` kehrst du zu 110 Prozent zurück.
- **Kleine Fenster:** Bereiche ordnen sich bei wenig Platz untereinander an. Scrolle nach unten, um weitere Inhalte zu erreichen.
- **Menüs bei großer Schrift:** Der Knopf **„Menü“** bündelt die Programmmenüs.

## Wenn etwas nicht klappt

| Problem | Nächster Schritt |
|---|---|
| **Das Programm öffnet sich nicht.** | Lies die Terminalmeldung vollständig. Prüfe, ob das ZIP komplett entpackt ist und du den Befehl im Ordner mit `STARTEN.sh` ausführst. |
| **Die Ausgabe wird blockiert.** | Prüfe die angegebene Ursache, die ausgewählten Quellen und ob du im Ausgabeordner speichern darfst. |
| **Eine Warnung erscheint.** | Prüfe den genannten Punkt. Richte dich nach dem Meldungstext, nicht nur nach der Farbe. |
| **Du brauchst Unterstützung.** | Halte die vollständige Meldung und den betroffenen Arbeitsschritt fest. Die [Fehleranleitung](docs/manuals/ERROR_HANDLING.md#protokolle-für-eine-fehlermeldung-sammeln) erklärt, welche Protokolle helfen. |

Starte VideoBatch als normaler Benutzer. Versuche Startfehler nicht mit `sudo`, `chmod -R 777` oder pauschalen Besitzänderungen zu umgehen. Nutze die [Anleitung zur sicheren Fehlerbehebung](docs/manuals/ERROR_HANDLING.md).

## Dokumentation

| Du möchtest … | Hier geht es weiter |
|---|---|
| den ersten Start Schritt für Schritt durchführen | [Hier beginnen](docs/start/START_HIER_save_.md) |
| die Installation verstehen | [Installationsanleitung](docs/start/AUTOINSTALLATION_save_.md) |
| alle Bedienfunktionen nachlesen | [Benutzerhandbuch](docs/BENUTZERHANDBUCH.md) |
| einen Fehler beheben | [Fehlerbehebung](docs/manuals/ERROR_HANDLING.md) |
| Updates und Rückkehr zum vorherigen Stand verstehen | [Update-Anleitung](docs/manuals/UPDATE_SYSTEM.md) |
| bestimmte Themen oder Dokumente finden | [Dokumentationsindex](docs/DOKUMENTATIONSINDEX.md) |

**Zu Updates:** Vor der Stable-Freigabe erfolgt die Auslieferung als vollständiges Projekt-ZIP. Teil- und Onlineupdates bleiben bis dahin deaktiviert.

## Für Entwicklung und Prüfung

Die folgenden Informationen richten sich an Mitwirkende. Für den ersten Test genügen die Schritte oben.

- [Entwickler-Einstieg](docs/manuals/DEVELOPER_GUIDE.md)
- [Aktueller Projektstatus](docs/STATUS.md), [offene Aufgaben](docs/TODO.md) und [Änderungen](docs/CHANGELOG.md)
- [Projektordner verstehen](docs/start/PROJEKTORDNERSTRUKTUR_save_.md) und [Dokumentationsübersicht](docs/DOKUMENTATIONSINDEX.md)
- [Standard für flexible Oberflächen](docs/design/PROVOWARE_RESPONSIVE_GRID_V1.md) und [HTML-Layoutreferenz](visual_inspection/provoware_grid_reference.html)
- [GitHub-Prüfläufe](https://github.com/provoware/PROVOWARE_VIDEO_AUTOMATION_2026/actions): Ergebnisse immer anhand des geprüften Commits einordnen.

<details>
<summary>Ordner im Repository</summary>

| Ordner oder Datei | Zweck |
|---|---|
| `STARTEN.sh` | Hauptstarter für die Anwendung |
| `src/` | Anwendungscode |
| `scripts/` | Installation, Prüfungen, Paketbau und Wartung |
| `tests/` | Automatisierte Tests |
| `config/` und `registries/` | Technische Verträge und Verzeichnisse |
| `docs/` | Anleitungen und Projektdokumentation |
| `docs/archive/` | Historische Berichte und frühere Prüfstände |
| `.github/workflows/` | Automatisierte GitHub-Prüfungen |

</details>

### Prüfstand und Freigabe

Erfolgreiche automatisierte Prüfungen erlauben die Integration eines Entwicklungsstands. Eine Stable-Freigabe erfordert zusätzlich die reale Endabnahme auf Kubuntu 26.04 / KDE Plasma / Wayland bei 100, 125, 150 und 200 Prozent sowie die vorgesehenen Medien- und Releaseprüfungen. Die vollständige reale Sicht- und Bedienprüfung bleibt offen.

Die nachstehenden Zahlen gehören zum **historischen RC24-Nachweis**. Sie messen weder den aktuellen `main`-Stand noch spätere Änderungen. Die Bezeichnung **RC** bedeutet „Release Candidate“, also eine Vorabversion vor der endgültigen Freigabe.

<details>
<summary>Historischer RC24-Prüfbericht und offene Freigabepunkte</summary>

<!-- release-status:start -->
# provoware - videoautomation - 2026 · 2.8.3-rc24

**Kanal:** rc
**Kanonische Quelle:** `diagnostics/release_readiness/RELEASE_EVIDENCE.json`
**Freigegebener Qualitätsbericht:** `VideoBatch_Fast_2.8.3-rc24_BUILD_REPORT_save_.json`

- 325/325 automatisierte Tests bestanden
- 82.43 % Zeilenabdeckung
- 67.21 % Zweigabdeckung
- 18/18 visuelle Szenarien bestanden
- Release-Manifest: 496 Dateien
- Kubuntu-CI-Matrix: 1/1 Kombinationen bestanden

### Offene Stable-Gates

- Physische Kubuntu-26.04-Plasma-Wayland-Abnahme: Der reale 125-%-Screenshot vom 06.10.2026 zeigte abgeschnittene und überladene Arbeitsbereiche. Der daraus abgeleitete seitengetrennte Qt-Stand muss vor Stable erneut real auf Kubuntu 26.04 / KDE Plasma / Wayland bei 100 %, 125 %, 150 % und 200 % geprüft werden.
<!-- release-status:end -->

</details>

<details>
<summary>Technischer Dateistatus der Release-Unterlagen</summary>

Die folgende Tabelle wird automatisch aus dem Nachweisbestand erzeugt. „Releasefertig“ bezieht sich auf die jeweilige Unterlage und bedeutet keine Stable-Freigabe der gesamten Anwendung. `_save_` kennzeichnet eigenständige Nutzer- und Release-Unterlagen.

<!-- release-files:start -->
## Release-Dateistatus

Only standalone user and release deliverables receive _save_. Source modules, CI workflows, canonical manifests, entrypoints and README retain stable technical names.

| Releasefertig (`_save_`) | Noch nicht releasefertig |
|---|---|
| `docs/start/START_HIER_save_.md`<br>Schnellstart: Geprüfter Nutzerstart und sichere erste Schritte | `docs/TODO.md`<br>Offene Arbeitsliste: Automatisierte Gates werden für den seitengetrennten Qt-Stand neu geprüft; danach ist die reale 100/125/150/200-%-Sichtabnahme und anschließend die Stable-Promotion offen. |
| `docs/start/AUTOINSTALLATION_save_.md`<br>Installationsanleitung: Benutzerpfade, A/B-Slots und Berechtigungsschutz dokumentiert | `docs/LONG_RENDER_2.8.3-rc24.md`<br>Langzeitrender: Prüfvertrag bleibt als Referenz erhalten; Langzeitrender wurde am 29.09.2026 manuell als in Ordnung bestätigt |
| `docs/start/PROJEKTORDNERSTRUKTUR_save_.md`<br>Projektübersicht: Ordner, Start, Sicherheit und Funktionen beschrieben | `docs/STABLE_ACCEPTANCE_EVIDENCE.md`<br>Stable-Abnahmenachweis: Basisfreigaben bleiben dokumentiert; der reale 125-%-Befund vom 06.10.2026 verlangt eine neue 100/125/150/200-%-Sichtabnahme des korrigierten Qt-Stands. |
| `docs/archive/rc24/RELEASE_NOTES_save_.md`<br>Releasehinweise: Aktueller RC24-Funktionsstand dokumentiert | `config/status/QUALITY_ENVIRONMENT_STATUS.json`<br>Qualitätsumgebung: Maschinenlesbarer Qualitätsstatus; nach der Layoutkorrektur müssen die automatisierten Gates erneut grün sein und die physische 100/125/150/200-%-UI-Abnahme bleibt offen. |
| `docs/archive/rc24/TEST_REPORT_save_.md`<br>Testbericht: Automatisierte und offene Prüfungen getrennt ausgewiesen | `registries/VISUAL_INSPECTION_MANIFEST.json`<br>Visuelles Prüfmanifest: Automatisierte visuelle Verträge bleiben Referenz; die reale 100/125/150/200-%-Sichtabnahme des seitengetrennten Qt-Stands steht noch aus. |
| `docs/archive/rc24/FRESH_PACKAGE_REPORT_save_.md`<br>Paketbericht: Saubere Paketprüfung für RC24 dokumentiert | — |
| `docs/archive/rc24/CODE_QUALITY_REPORT_2.8.3-rc24_save_.md`<br>Codequalitätsbericht: Interne Qualitätsprüfung ohne Befund | — |
| `docs/archive/rc24/IMPLEMENTATION_REPORT_2.8.3-rc24_save_.md`<br>Implementierungsbericht: Umgesetzte Funktions- und Sicherheitsverträge dokumentiert | — |
| `docs/archive/rc24/FINAL_AUDIT_2.8.3-rc24_save_.md`<br>RC-Abschlussaudit: RC-Gates und offene Stable-Gates ehrlich getrennt | — |
| `docs/archive/rc24/VideoBatch_Fast_2.8.3-rc24_BUILD_REPORT_save_.json`<br>Maschinenlesbarer Buildbericht: Aus der kanonischen RELEASE_EVIDENCE.json erzeugt | — |
<!-- release-files:end -->

</details>
