# VideoBatch Fast · Videos aus Musik, Bildern und Clips

![Entwicklungsstand](https://img.shields.io/badge/Stand-Entwicklung-orange) ![Lokale Verarbeitung](https://img.shields.io/badge/Verarbeitung-lokal-brightgreen) ![Zielsystem](https://img.shields.io/badge/Ziel-Kubuntu%2026.04%20%7C%20Wayland-blue)

**PROVOWARE Video-Automation 2026** erstellt Videos aus Audiodateien, Bildern und vorhandenen Clips – direkt auf deinem Rechner. Du musst nicht programmieren können. Die wichtigsten Handgriffe sind **Dateien auswählen → Ausgabe festlegen → Videos erstellen**.

> 🟠 **WICHTIG – noch keine Stable-Version:** Das Repository enthält einen aktuellen **Entwicklungsstand** für **Kubuntu 26.04 LTS, KDE Plasma und Wayland**. Automatische GitHub-Prüfungen sind keine persönliche Freigabe des fertigen Programms. Starte mit **Kopien** deiner Medien und einem kurzen Testvideo.

> 🟢 **SICHERHEIT:** Die Originalmedien sollen unverändert bleiben. Lege für fertige Videos trotzdem einen **eigenen, leeren Ausgabeordner** an. Verwende **kein `sudo`** zum Programmstart.

### Inhaltsverzeichnis

- [Ebene 1 – Schnellstart zum Kopieren](#schnellstart)
- [Ebene 2 – ausführliche Anleitung](#ebene-2-ausführliche-anleitung)
  - [Voraussetzungen und Download](#voraussetzungen-und-download)
  - [Erstes Video erstellen](#erstes-video-erstellen)
  - [Bedienung und Vergrößerung](#bedienung-und-vergrößerung)
  - [Projekt und Schnellnotizen](#projekt-und-schnellnotizen)
  - [Sicherung und Rückweg](#sicherung-und-rückweg)
- [Ebene 3 – Hilfe ohne Vorwissen](#ebene-3-hilfe-ohne-vorwissen)
  - [Farben und Begriffe](#farben-und-begriffe)
  - [Wenn etwas nicht klappt](#wenn-etwas-nicht-klappt)
  - [Häufige Fragen](#häufige-fragen)
- [Abschlussprüfung](#abschlussprüfung)
- [Dokumentation](#dokumentation)
- [Für Entwicklung und Prüfung](#für-entwicklung-und-prüfung)
- [Historischer RC24-Nachweis](#historischer-rc24-nachweis)

---

## Schnellstart

**Ebene 1 · Zum direkten Kopieren.** Öffne zuerst den **vollständig entpackten Projektordner** im Dateimanager. Klicke dort mit der rechten Maustaste und wähle **„Terminal hier öffnen“** (Bezeichnung kann abweichen). Führe die Befehle einzeln aus. **Für den normalen Start genügen die Schritte 1–3.**

1. **Ordner prüfen** · Pflicht. Dieser Befehl zeigt die Startdatei an:
   ```bash
   ls -l STARTEN.sh
   ```
2. **Python prüfen** · Pflicht. Die angezeigte Python-Version muss mindestens **3.11** sein:
   ```bash
   python3 --version
   ```
3. **Programm starten** · Pflicht. Dieser Befehl startet die echten Vorprüfungen und danach die Oberfläche:
   ```bash
   bash ./STARTEN.sh
   ```
4. **Anleitung prüfen** · Optional, für Entwicklungsprüfungen. Dieser Befehl kontrolliert die Dokumentation:
   ```bash
   bash ./scripts/dev/test.sh --docs
   ```
5. **Kernfunktionen prüfen** · Optional, für Entwicklungsprüfungen. Dieser Befehl benötigt zusätzliche vorbereitete Prüfwerkzeuge:
   ```bash
   bash ./scripts/dev/test.sh --core
   ```

🟡 **Laien-Tipp:** Wenn Schritt 1 „Datei nicht gefunden“ meldet, bist du sehr wahrscheinlich im falschen Ordner oder das ZIP ist nicht vollständig entpackt. **Nicht** wahllos weitere Befehle ausführen. Die letzten beiden Befehle sind **keine Voraussetzung**, um ein Video zu erstellen.

🔵 **Download ohne Terminal:** Auf GitHub **Code → Download ZIP** wählen, anschließend das ZIP in einen eigenen Ordner entpacken. Das ZIP vom Hauptzweig ist **keine Stable-Freigabe**.

---

## Ebene 2 – ausführliche Anleitung

Dieser Bereich erklärt die Arbeitsschritte mit **Ziel, Voraussetzung, Durchführung, Erfolgskontrolle und sicherem Rückweg**.

### Voraussetzungen und Download

**Ziel:** VideoBatch aus einem vollständig entpackten Paket starten.

**Pflicht:** Ein normaler Benutzerzugang unter Kubuntu 26.04 LTS mit KDE Plasma und Wayland, ein Rechner mit Python 3.11 oder neuer, ausreichend Speicher sowie ein Projektordner mit `STARTEN.sh`, `README.md`, `src/` und `scripts/`.

**Empfohlen:** Eine kurze Audiodatei und ein Bild oder Videoclip **als Kopien**, außerdem ein eigener Ordner für fertige Videos. Benutze zunächst keine wertvollen Originaldateien für den Erstversuch.

**Vorgehen:** Repository-ZIP über GitHub herunterladen und entpacken. Danach im entpackten Ordner ein Terminal öffnen und **`bash ./STARTEN.sh`** ausführen. Der Starter prüft Python und die benötigten Komponenten. Er verwendet den vorgesehenen lokalen Programmstart; ein direkter Aufruf einzelner Python-Module würde Vorprüfungen umgehen.

**Erwartetes Ergebnis:** Die VideoBatch-Oberfläche öffnet sich. Wenn benötigte Bestandteile fehlen, erscheint eine Startmeldung. Folge der dort beschriebenen Lösung und lies die [Installationsanleitung](docs/start/AUTOINSTALLATION_save_.md). **Keine pauschalen Rootrechte oder globalen Dateiberechtigungen vergeben.**

**Alternative für Entwickler mit Git:** Nur wenn Git installiert ist und eine Internetverbindung besteht, kannst du den Quellcode so herunterladen:
```bash
git clone https://github.com/provoware/PROVOWARE_VIDEO_AUTOMATION_2026.git
```
Danach den Ordner `PROVOWARE_VIDEO_AUTOMATION_2026` öffnen und die Schritte aus [Ebene 1](#schnellstart) ausführen. Ein Git-Klon enthält ebenso den Entwicklungsstand und garantiert keine Stable-Freigabe.

### Erstes Video erstellen

**Ziel:** Eine kurze, kontrollierbare Videodatei erzeugen. Für jeden Schritt siehst du, **woran du den Erfolg erkennst**.

| Schritt | Was du anklickst | Erfolgskontrolle |
|---|---|---|
| **1 · Dateien** | **Audio auswählen** und eine kurze Musikdatei wählen; danach **Bilder/Videos auswählen** und ein Bild oder einen Clip ergänzen. | Die ausgewählten Dateien erscheinen in den Listen. |
| **2 · Ausgabe** | Die vorgeschlagenen Einstellungen für den ersten Test belassen und einen **eigenen Ausgabeordner** auswählen. | Der angezeigte Zielordner stimmt mit deiner Auswahl überein. |
| **3 · Produktion** | Quellenzuordnung prüfen; **„Prüfen & Videos erstellen“** wählen. Bei großer Schrift kann der Knopf **„Prüfen & Starten“** heißen. | Nach der Vorprüfung zeigt das Programm Fortschritt und anschließend eine eindeutige Abschlussmeldung. |
| **4 · Nachprüfung** | Die fertige Datei im Ausgabeordner öffnen. | **Anfang, Mitte und Ende** spielen mit richtigem Bild und Ton ab. |

**Warum?** Audio und Bild müssen zum richtigen Auftrag gehören; der Ausgabeordner muss beschreibbar sein. Ein erfolgreicher Programmabschluss allein beweist noch nicht, dass das Video inhaltlich richtig ist.

**Kann etwas entfallen?** Erweiterte Effekte, eigene Blenden und große Dateisammlungen: **ja**. Quellenprüfung, Zielordnerkontrolle und abschließende Wiedergabe: **nein**, wenn du ein zuverlässiges Ergebnis brauchst.

🟢 **Laien-Tipp:** Verwende zunächst eine sehr kurze Audiodatei und genau ein Bild. Wenn das Ergebnis richtig ist, kannst du weitere Medien hinzufügen. So erkennst du Probleme, bevor ein großer Stapel bearbeitet wird.

### Bedienung und Vergrößerung

Die Arbeitsseiten heißen **„1 · Dateien“**, **„2 · Ausgabe“**, **„3 · Produktion“** und **„Dashboard“**. Das Dashboard enthält zusätzliche Werkzeuge und die Schnellnotiz; die genaue Beschriftung kann bei großer Schrift kürzer ausfallen.

- Die Schrift lässt sich über **„Schrift“** zwischen 80 % und 200 % einstellen.
- **Strg + Alt + Pfeil hoch/runter** vergrößert bzw. verkleinert. **Strg + Alt + 0** stellt 110 % wieder her.
- Bei wenig Bildschirmplatz erscheinen kürzere Schaltflächenbeschriftungen; vollständige Hinweise bleiben über Hilfetexte erreichbar. Fehlende Inhalte kannst du durch **senkrechtes Scrollen** erreichen.
- Die Seiten „Ausgabe“ und „Produktion“ besitzen passende äußere Scrollbereiche, damit bei 800 × 600 Pixeln und 200 % keine wichtigen Schritte verborgen bleiben.

**Erwartetes Ergebnis:** Die benötigten Schaltflächen sind auch mit Tastatur und großer Schrift erreichbar. Die automatisierten Qt-/Wayland-Prüfungen ersetzen noch **nicht** die endgültige persönliche Sichtprüfung.

### Projekt und Schnellnotizen

Auf der Seite **„Dashboard“** kannst du eine kurze Notiz eingeben und mit **Enter** oder **„Notiz anhängen“** speichern. Das Programm ergänzt einen lokalen Zeitstempel und zeigt den Speicherstatus sowie den gewählten Dateipfad.

Die Datei heißt **`VideoBatch_Notizen.txt`** und liegt im Ordner des **aktiven** `.vbfast.json`-Projekts. Sie wird nicht für jede Notiz neu erstellt: Weitere Notizen werden an den bisherigen Inhalt angehängt. Nach einem Projektwechsel oder **„Speichern unter“** wird der zugehörige Notizpfad aktualisiert.

🟡 **Wichtig:** Wenn die Notiz nicht gespeichert werden kann, bleibt dein eingegebener Text erhalten. Lies die Fehlermeldung und prüfe den Ordner. Die Speicherfunktion hat Schutzprüfungen gegen unsichere Dateiverknüpfungen und unterbrochene Schreibvorgänge.

### Sicherung und Rückweg

Bewahre eine **Sicherungskopie der Quelldateien und wichtiger Projektdateien** an einem anderen Ort auf. Ein Projekt ist die gespeicherte Arbeitszusammenstellung – nicht automatisch eine Kopie aller verwendeten Medien.

**Bei einem Startfehler:** Terminalmeldung vollständig lesen, Projektordner und Entpackung prüfen und die [Fehlerbehebung](docs/manuals/ERROR_HANDLING.md) verwenden. **Kein `sudo`, kein `chmod -R 777` und keine pauschalen Löschaktionen.**

**Bei einem fehlgeschlagenen Update:** Die [Update-Anleitung](docs/manuals/UPDATE_SYSTEM.md) erklärt die vorhandene Sicherungs- und Rückfallstrategie. Vor einer Stable-Freigabe sind Online-/Teilupdates nicht als normaler Benutzerweg freigegeben.

---

## Ebene 3 – Hilfe ohne Vorwissen

Dieser Abschnitt erklärt die Begriffe bewusst so, als hättest du noch nie mit Linux oder einem Programmprojekt gearbeitet.

### Farben und Begriffe

| Zeichen | Bedeutung | Was du tun solltest |
|---|---|---|
| 🟢 **Grün** | Alles ist für diesen Schritt in Ordnung. | Mit dem nächsten Schritt weitermachen. |
| 🔵 **Blau** | Zusätzliche Information oder Hilfe. | Lesen, wenn du etwas nicht verstehst. |
| 🟡 **Gelb** | Etwas muss kontrolliert werden. | Hinweis lesen und die genannte Sache prüfen. |
| 🔴 **Rot** | Ein Vorgang wurde gestoppt oder ein Fehler erkannt. | Nicht blind wiederholen; zuerst die Ursache lesen. |
| 🟠 **Orange** | Entwicklungsstand, noch keine Veröffentlichung. | Nur vorsichtig und zunächst mit Testdaten verwenden. |

**Terminal:** Ein Fenster, in das du Befehle schreiben oder kopieren kannst. **ZIP:** Ein gepackter Ordner; er muss vor dem Start vollständig ausgepackt werden. **Python:** Ein benötigter Programmbaustein, dessen Version du prüfen kannst. **FFmpeg:** Das Werkzeug, das aus Audio und Bildern tatsächlich eine Videodatei erzeugt. **Wayland:** Die Art, wie Linux die grafische Oberfläche darstellt. **PR:** Ein vorgeschlagener Programmänderungssatz auf GitHub. **`main`:** Der zentrale Entwicklungszweig. **Stable:** Ein endgültig freigegebener Stand – dieser Status liegt noch nicht vor.

> 🟢 **Das Wichtigste:** Für die normale Bedienung musst du **weder programmieren noch Tests schreiben**. Du brauchst vor allem die drei Programmschritte **Dateien → Ausgabe → Produktion**.

### Wenn etwas nicht klappt

| Das siehst du | Das bedeutet es meistens | Sichere nächste Aktion |
|---|---|---|
| 🔴 **`STARTEN.sh` fehlt** | Das Terminal zeigt auf einen anderen Ordner oder das ZIP ist unvollständig. | Im Dateimanager den entpackten Projektordner öffnen; dort das Terminal erneut starten. |
| 🔴 **`python3: command not found`** | Python 3 ist nicht verfügbar. | Die [Installationshilfe](docs/start/AUTOINSTALLATION_save_.md) öffnen. Keine Befehle unbekannter Herkunft kopieren. |
| 🟡 **Dateien fehlen im Programm** | Eine Quelle wurde verschoben oder nicht ausgewählt. | In „1 · Dateien“ die Liste prüfen und die richtige Datei neu auswählen. |
| 🔴 **Ausgabe nicht möglich** | Der Zielordner ist nicht verfügbar oder nicht beschreibbar. | In „2 · Ausgabe“ einen anderen **eigenen** Ordner auswählen und erneut prüfen. |
| 🟡 **Notiz nicht gespeichert** | Die Datei oder der Projektordner ist nicht zugänglich. | Notiz im Eingabefeld belassen, Speicherpfad lesen, Zugang prüfen, dann erneut speichern. |
| 🔵 **Bedienelement nicht sichtbar** | Fenster oder Schrift sind sehr groß. | Nach unten scrollen oder über „Schrift“ vorübergehend eine kleinere Größe wählen. |

🔴 **Laien-Tipp bei Fehlern:** Schreibe die **ganze Fehlermeldung** auf, nicht nur „funktioniert nicht“. Notiere außerdem, welchen Knopf du zuletzt benutzt hast. Damit lässt sich die Ursache oft eindeutig finden. [So sammelst du Diagnoseinformationen](docs/manuals/ERROR_HANDLING.md#protokolle-für-eine-fehlermeldung-sammeln).

### Häufige Fragen

<details>
<summary><strong>„Muss ich Befehle auswendig lernen?“</strong></summary>

Nein. Öffne den Programmordner und kopiere zum Start **`bash ./STARTEN.sh`** aus dem Schnellstart. Alle weiteren Prüf-Befehle sind nur für Entwicklung und Fehlersuche nötig.

</details>

<details>
<summary><strong>„Löscht VideoBatch meine Musik oder Bilder?“</strong></summary>

Die Anwendung soll die Originalmedien nicht überschreiben. Verwende trotzdem ein **getrenntes Ausgabeziel** und für den ersten Versuch Kopien deiner Dateien. Das schützt zusätzlich vor Fehlern bei der Auswahl von Ordnern.

</details>

<details>
<summary><strong>„Ist die grüne GitHub-Prüfung schon eine fertige Version?“</strong></summary>

Nein. 🟢 Ein grüner automatischer Test bedeutet nur, dass **dieser Test für diesen bestimmten Programmstand** bestanden wurde. Die endgültige reale Bedien-, Video- und Langzeitprüfung des fertigen Kandidaten steht separat aus.

</details>

<details>
<summary><strong>„Wofür brauche ich das Dashboard?“</strong></summary>

Dort findest du zusätzliche Werkzeuge und die **Schnellnotiz**. Sie ist praktisch, um dir zu merken, was du am aktuellen Videoprojekt noch ändern oder prüfen möchtest.

</details>

---

## Abschlussprüfung

**Pflicht für dein erstes Testvideo:** Die Anwendung öffnet sich ohne blockierenden Fehler; Audio und Bild stehen in den Quellenlisten; der Ausgabeordner stimmt; der Auftrag endet mit einem verständlichen Ergebnis; **Anfang, Mitte und Ende** des fertigen Videos wurden abgespielt. Bei einer Abweichung zuerst [die sichere Fehleranleitung](docs/manuals/ERROR_HANDLING.md) verwenden.

**Nicht damit verwechseln:** Ein fertiges Testvideo ist **keine Stable-Freigabe** des gesamten Programms. Vor einer offiziellen Veröffentlichung ist die vollständige reale Zielsystem-, FFmpeg- und Langzeitabnahme am eingefrorenen Kandidaten erforderlich.

## Dokumentation

| Was möchtest du? | Passende Anleitung |
|---|---|
| Ohne Vorkenntnisse beginnen | [Startanleitung](docs/start/START_HIER_save_.md) |
| Installation und Voraussetzungen verstehen | [Installationsanleitung](docs/start/AUTOINSTALLATION_save_.md) |
| Alle Funktionen genauer kennenlernen | [Benutzerhandbuch](docs/BENUTZERHANDBUCH.md) |
| Probleme und Fehlermeldungen lösen | [Fehlerbehebung](docs/manuals/ERROR_HANDLING.md) |
| Update und Rückweg verstehen | [Update-Anleitung](docs/manuals/UPDATE_SYSTEM.md) |
| Dokumente nach Thema finden | [Dokumentationsindex](docs/DOKUMENTATIONSINDEX.md) |

## Für Entwicklung und Prüfung

**Nur für Mitwirkende; für das erste Video nicht notwendig.** Die tatsächlichen Entwicklungsskripte befinden sich **unter `scripts/dev/`**, nicht im Projekt-Hauptordner:

| Zweck | Kopierbarer Befehl im Projektordner |
|---|---|
| Schnell die Dokumentation prüfen | `bash ./scripts/dev/test.sh --docs` |
| Kernfunktionen prüfen | `bash ./scripts/dev/test.sh --core` |
| Lokale Qualitätsprüfung | `bash ./scripts/dev/verify_release.sh` |
| Strenge Prüfung des finalen Kandidaten | `bash ./scripts/dev/verify_release.sh --strict` |

**Hinweis:** Entwicklungstests können eine vorbereitete Prüf-Umgebung benötigen. Keine Testausführung und kein grünes GitHub-Signal ersetzt die finale persönliche Abnahme. Für das Vorgehen gelten [AGENTS.md](AGENTS.md), der [Entwicklerleitfaden](docs/manuals/DEVELOPER_GUIDE.md), der [Projektstatus](docs/STATUS.md), [offene Aufgaben](docs/TODO.md) und die [Änderungen](docs/CHANGELOG.md). Die [GitHub-Prüfungen](https://github.com/provoware/PROVOWARE_VIDEO_AUTOMATION_2026/actions) zeigen, **welcher Commit** tatsächlich getestet wurde.

<details>
<summary><strong>Technische Projektordner anzeigen</strong></summary>

| Pfad | Inhalt |
|---|---|
| `STARTEN.sh` | einziger sichtbarer Benutzerstarter |
| `src/` | Programmcode |
| `scripts/dev/` | Tests und Entwicklung |
| `scripts/cli/` und `scripts/install/` | interne Start- und Installationswerkzeuge |
| `tests/` | automatisierte Tests |
| `docs/` | Anleitungen und Berichte |
| `docs/archive/` | historische Nachweise, nicht der aktuelle Freigabestatus |
| `config/` und `registries/` | technische Verträge und Verzeichnisse |

</details>

### Prüfstand und Freigabe

🟠 **Aktuell:** Die Entwicklungsintegration kann durch die für den jeweiligen Commit grünen Pflichtprüfungen abgesichert sein; eine **Stable-Freigabe** liegt nicht vor. Für die abschließende Freigabe werden echte Kubuntu-26.04/KDE/Wayland-Prüfungen bei **100 %, 125 %, 150 % und 200 %**, ein realer FFmpeg-Auftrag, ein Langzeitrender und die vollständige Sichtabnahme verlangt.

### Historischer RC24-Nachweis

Die folgenden beiden aufklappbaren Bereiche werden aus **historischen RC24-Belegen** erzeugt. Ihre Zahlen gelten **nicht** als Testergebnis des aktuellen `main`-Zweigs. Die markierten Abschnitte werden bewusst nicht manuell geändert.

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
