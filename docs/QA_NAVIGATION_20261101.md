# Navigation und 800x600 - 01.11.2026

Basis: main@b298ca4facc98b381b877c66e0cf4777ed956860. Auftrag: verständliche, gleichbleibende Navigation und Hauptabläufe bei 100/150/200 Prozent.

## Soll/Ist vor Änderung
- Struktur, Proportionen, Abstände, Farben und Typografie bleiben unverändert.
- Die vierte Seite wechselte bei 150 Prozent von Dashboard zu Notizen; sie heißt nun durchgehend Übersicht.
- Alt+2 fokussierte ein Feld auf einer anderen Seite. Zusätzlich setzte die asynchrone Seitennavigation die Scrollposition nach dem Fokussieren zurück.
- Nachweis: native Qt-Aufnahmen bei 800x600; Prüfung der tatsächlichen Fenster- und Feldkoordinaten. Keine erfundenen Pixelvorgaben und kein optischer Musterumbau.

## Ergebnis
Drei neue echte Qt-Tests: Alt+2 aus Dateien, Produktion und Übersicht; Ausgabeseite, Tastaturfokus und Feldgrenzen innerhalb des Fensters bei 100/150/200 Prozent geprüft. Alle drei PASS. Zwölf Seitenwechsel (vier Seiten mal drei Größen), passende Bildschirmaufnahmen und bestehender tests/qt_phase3_smoke.py PASS. Testumgebung: Python 3.12, PySide6 6.9.1, offscreen. Dies ersetzt keine reale Kubuntu-/Wayland-Abnahme.

Die Sammelprüfung aus test_qt_responsive_20261020.py, test_qt_ui_contract.py und test_documentation_contract.py hatte zunächst 39 PASS und sieben FAIL. Auf unverändertem Ausgangscode hat test_qt_ui_contract.py acht FAIL; der achte ist der durch diesen Patch behobene Alt+2-Vertrag. Die sieben verbleibenden Quelltextverträge erwarten unter anderem verschobene Dateien, alte Funktionsnamen und eine inzwischen entfernte zweite Scrollfläche. Sie sind bestehende Testschulden, keine nachgewiesene neue Laufzeitregression. Keine Grünfreigabe der gesamten historischen Testsuite.

## Rückweg
Isolierten Änderungscommit zurücknehmen. Keine Datenformatänderung, keine Medien- oder Speicheränderung. Nächster Schritt: aktuelle GitHub-Pflichtprüfungen auf dem PR-HEAD auswerten; historische Testverträge gesondert mit den echten aktuellen Verantwortlichkeiten abgleichen.
