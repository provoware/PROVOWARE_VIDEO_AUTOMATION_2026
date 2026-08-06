# Checkpoint 3 · Iteration 3.2

## Ziel

Die vier kanonischen KPI-Karten werden von reinen Momentaufnahmen zu nachvollziehbaren, projektbezogen persistenten Zustandsanzeigen erweitert.

## Exakte Basis

- Ausgangs-`main`: `b9a3663a7b229ace00b43f01415ecc4d39adbe14`
- Arbeitsbranch: `agent/checkpoint3-kpi-detail-recovery-20260806`
- PR: `#67`
- Branchanlage und Abschlussdiff: `behind_by = 0`

## Umgesetzt

- persistente Detailzustände im vorhandenen Projekt-Metabereich `meta.canonical_kpi`
- Zeitstempel ändern sich nur bei einer tatsächlichen Zustands- oder Detailänderung
- verständliche Ursachen für fehlende Quellen, unvollständige Zuordnung, Queuefehler und ungültige Effektwerte
- direkte, kontrollierte Wiederherstellungsaktionen ohne automatischen Renderstart
- Entfernen nicht erreichbarer Projektverweise
- kontrolliertes Laden wiederanlaufbarer Queuequellen
- Öffnen der begrenzten Wiederanlaufliste
- Zurücksetzen ungültiger Effektwerte auf `smart_auto`
- stabile Zustände `empty`, `ready`, `loading`, `success`, `warning`, `error`, `disabled`
- konsolidierter Vierfach-Statuscheck `Checkpoint 2 canonical shell matrix`

## Sicherheitsvertrag

- Wiederanlaufeinträge werden nur geladen und niemals automatisch gestartet.
- Originaldateien werden durch KPI-Aktionen nicht verändert oder gelöscht.
- Gesperrte Wiederanlaufeinträge bleiben gesperrt.
- Die Startzeituhr bleibt bis Checkpoint 5 deaktiviert.
- Persistenz ist auf bekannte Karten, bekannte Zustände und begrenzte Textlängen beschränkt.

## Abnahme

Jede Zelle Ubuntu 22.04/24.04 × X11/Wayland führt schnelle Sequenzen aus:

1. gültiger Import
2. simulierter Dateiverlust
3. kontrollierter Queuefehler
4. gültiger und ungültiger Effektwechsel
5. direkte Wiederherstellungsaktionen
6. Persistenz- und Zeitstempelprüfung

Der Abschlussjob akzeptiert ausschließlich vier erfolgreiche Zellen auf exakt demselben PR-Head.

## Abschlussprüfung

- Release-Manifest aus dem vollständigen PR-Baum deterministisch erzeugt
- temporärer Manifestworkflow vollständig entfernt
- sechs reine Zustands- und Persistenztests lokal bestanden
- reale Tk-Wiederherstellungssequenz direkt in jeder der vier Matrixzellen verankert
- abschließender Diagnosecommit verändert den Release-Dateisatz nicht
- sämtliche GitHub-Gates müssen denselben finalen PR-Head prüfen

## Stabile Statuskontexte

Nach vollständig grüner Prüfung können in der `main`-Regel zusätzlich als Required Status Checks verwendet werden:

- `Design manifest contract`
- `Checkpoint 2 read-only preflight`
- `Checkpoint 2 canonical shell matrix`

Die Repository-Regel selbst ist eine administrative GitHub-Einstellung und wird nicht durch Projektcode vorgetäuscht.
