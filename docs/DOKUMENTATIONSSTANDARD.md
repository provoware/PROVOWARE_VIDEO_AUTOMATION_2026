# VideoBatch-Dokumentationsstandard

**Status:** verbindlich für neue und überarbeitete Anleitungen  
**Gültig ab:** 6. August 2026  
**Zielgruppe:** Einsteiger, fortgeschrittene Nutzer, Administratoren und Entwickler

## Zweck

Dieser Standard sorgt dafür, dass jede Anleitung ohne Vorwissen nachvollziehbar ist. Niemand soll raten müssen, wo geklickt wird, welcher Befehl nötig ist, warum ein Schritt erforderlich ist oder woran ein erfolgreicher Abschluss erkennbar ist.

## Verbindlicher Aufbau jeder Anleitung

Jeder praktische Vorgang muss in dieser Reihenfolge beschrieben werden:

1. **Ziel** – Was wird am Ende erreicht?
2. **Pflichtgrad** – Pflicht, empfohlen oder optional.
3. **Voraussetzungen** – Was muss vorher vorhanden oder erledigt sein?
4. **Sicherung und Rückweg** – Wie wird der bisherige Zustand geschützt oder wiederhergestellt?
5. **Schritt-für-Schritt-Anleitung** – Eine konkrete Aktion pro nummeriertem Schritt.
6. **Warum ist das notwendig?** – Begründung direkt beim betreffenden Schritt.
7. **Kann der Schritt entfallen?** – Ja oder nein, einschließlich der Folgen.
8. **Erwartetes Ergebnis** – Was muss sichtbar oder messbar sein?
9. **Fehlerfall** – Was ist bei einer Abweichung zu tun?
10. **Abschlussprüfung** – Wie wird der Erfolg eindeutig nachgewiesen?
11. **Nächster Schritt** – Was folgt logisch danach?

## 3. Pflichtkennzeichnungen

Jeder relevante Schritt erhält genau eine Kennzeichnung:

- **Pflicht:** Ohne diesen Schritt ist der Vorgang unsicher, unvollständig oder nicht funktionsfähig.
- **Empfohlen:** Der Vorgang funktioniert meist auch ohne diesen Schritt, wird aber weniger sicher oder nachvollziehbar.
- **Optional:** Komfortfunktion ohne Einfluss auf den technischen Erfolg.
- **Automatisch erledigt:** VideoBatch führt den Schritt selbst aus.
- **Manuell erforderlich:** Der Schritt kann nicht durch VideoBatch oder die vorhandene Automatisierung ausgeführt werden.

## 4. Schreibregeln

- Eine Handlung pro Schritt.
- Exakte Namen von Schaltflächen, Menüs, Dateien und Befehlen verwenden.
- Keine unaufgelösten Begriffe wie „einfach“, „normal“, „entsprechend“ oder „wie üblich“.
- Befehle immer in einem eigenen Codeblock darstellen.
- Vor gefährlichen Befehlen Auswirkungen und Rückweg nennen.
- Keine Erfolgsbehauptung ohne sichtbares oder automatisiertes Prüfkriterium.
- Abkürzungen beim ersten Auftreten erklären.
- Historische Berichte klar als Archiv kennzeichnen und nicht als aktuelle Anleitung formulieren.
- Noch nicht implementierte Funktionen eindeutig als geplant oder deaktiviert benennen.

## 5. Standardvorlage

```markdown
# Titel

## Ziel

## Pflichtgrad

## Voraussetzungen

## Sicherung und Rückweg

## Schritt-für-Schritt-Anleitung

### Schritt 1: …

**Aktion:** …

**Warum notwendig?** …

**Kann entfallen?** Nein/Ja. Folge: …

**Erwartetes Ergebnis:** …

**Bei einem Fehler:** …

## Abschlussprüfung

## Nächster Schritt
```

## 6. Änderungsvertrag

Bei jeder Funktionsänderung muss geprüft werden, ob mindestens eine Anleitung, Hilfeseite, Fehlermeldung, Release-Notiz oder Entwicklerbeschreibung angepasst werden muss. Eine Codeänderung gilt nicht als vollständig dokumentiert, wenn die dazugehörige Nutzerhandlung oder Fehlerbehebung weiterhin veraltet ist.

## Abnahmekriterien

Eine Anleitung besteht die Dokumentationsprüfung nur, wenn:

- alle erforderlichen Voraussetzungen genannt sind;
- jeder manuelle Schritt eindeutig ausführbar ist;
- der Zweck kritischer Schritte erklärt wird;
- ausgelassene Schritte und ihre Folgen beschrieben sind;
- ein sichtbares Erfolgskriterium vorhanden ist;
- ein sicherer Fehler- oder Rückweg beschrieben ist;
- der logisch folgende Schritt genannt ist.
