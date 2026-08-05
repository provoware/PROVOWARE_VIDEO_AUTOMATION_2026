# Implementierungsbericht 2.8.0 Stable

## 1. Volatile Prüfwerte normalisiert

Die Signatur bindet jetzt ausschließlich deterministische UI-Verträge:

- Szenario-ID und Gruppe
- Seite und Zustand
- Auflösung und Schriftzoom
- Pflichttexte und semantische Farben
- Pass-/Fail-Status
- Richtlinien und Vertragsfehler
- Baseline-Bundle-Hash
- normalisierter Reportstatus

Ausgeschlossen sind:

- Erzeugungszeit
- absolute und aktuelle Pfade
- aktuelle Screenshot- und Differenzpfade
- Pixelmittelwert
- dHash-Abstand
- Laufzeitmeldungen

Damit bleibt eine identische Neuprüfung signaturstabil, während echte UI- oder Baselineänderungen weiter blockieren.

## 2. Freigabeschlüssel verschlüsselt archiviert

Neu:

- `src/videobatch_fast/key_archive.py`
- `scripts/archive_visual_approval_key.py`

Verfahren:

```text
Kennwort
→ Scrypt-Schlüsselableitung
→ AES-256-GCM-Verschlüsselung
→ atomisches Schreiben mit 0600
→ sofortige Entschlüsselungs- und Schlüsselpaarprüfung
```

Private Schlüssel oder Kennwörter sind nicht Bestandteil des Release-ZIPs.

## 3. Stable-Update gebunden

Das Stable-Update enthält verbindlich:

- Build-ID
- normalisierten visuellen Vertragshash
- Baseline-Bundle-Hash
- Hash des signierten Abnahmevermerks
- Schlüssel-ID, Prüfer und Abnahmezeit

Das Update wird blockiert, wenn diese Werte nicht zum enthaltenen visuellen Manifest passen.

## 4. Erscheinungsbild modernisiert

- Blau-Anthrazit statt olivlastigem Grund
- klarere Ebenen und reduzierte Rahmen
- Cyan für Information, Fokus und aktive Auswahl
- Gold nur für Hauptaktionen und Freigabepunkte
- modernere Tabellenköpfe, Tabs und Fortschrittsbalken
- stärker sichtbarer Versionsbadge
- übersichtlicheres HTML-Prüfdashboard

## 5. Validierung

- 90 Tests bestanden
- 12/12 Anwendungssimulationen
- 16/16 visuelle Szenarien
- 49 Module, 307 Funktionen, 48 Klassen
- größte Quelldatei: 616 Zeilen
- 0 Architekturbefunde
- Stable-Update real installiert und Kandidatentest bestanden
