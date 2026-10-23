# Release-Fortschritt: Pilotregel

Bestehende AGENTS.md-, Medien-, Sicherheits-, Test- und Release-Regeln haben Vorrang.

Stufe eins: Ziele, Risiken, erwarteten Nutzen, betroffene Dateien, Alternativen und vorhandene Nachweise nur dokumentieren und planen. Keine Produktcodeänderung vor erforderlicher Freigabe.

Stufe zwei: nach gültiger Freigabe kleinsten Patch umsetzen, Ausgangsstand und Schreibzuständigkeit prüfen und das tatsächliche Projekt mit den vorgeschriebenen Tests validieren. Historische Testergebnisse gelten nicht für geänderte Commits.

Nach jeder Iteration tatsächliche Wirkung und verbleibende Release-Blocker belegen. Sparsamer Ressourceneinsatz ersetzt keine Sicherheitsprüfung.

Bei erheblichen Konflikten nur betroffene Änderung stoppen, Alternativen erläutern und Nutzer gezielt fragen. Unabhängige sichere Arbeit fortsetzen.

Zunächst nur beobachtend; keine neue blockierende Automatik.
