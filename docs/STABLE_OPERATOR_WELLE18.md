# Welle 18 – Real Stable-Gate Operator

Dieses Kit schließt **keinen** physischen Nachweis automatisch. Es erzwingt nur die Reihenfolge und bindet jeden erfolgreich erzeugten Nachweis an denselben unveränderten RC-Kandidaten.

## Voraussetzungen

- Kubuntu/KDE-Plasma-Zielsystem mit Python 3, FFmpeg/FFprobe und Internetzugang nur für den initialen Wheelhouse-Aufbau.
- Für die Desktop-Abnahme ist ausschließlich eine echte KDE-X11-Sitzung erforderlich. Wayland gehört nicht zum Zielsystem und ist kein Stable-Gate. Xvfb/CI gilt nicht als physischer Nachweis.
- Für den Langzeitrender: 96 Audiodateien, 192 Bilder, separater schreibgeschützter Eingabe-Mount und realer langsamer externer USB-ext4-Datenträger gemäß `docs/LONG_RENDER_2.8.3-rc24.md`.
- Ein persistenter Operator-Sitzungsordner, der zwischen Desktop-Abnahme und Langzeitrender erhalten bleibt.

## Feste Reihenfolge

```bash
SESSION="$HOME/VideoBatch-W18-Evidence"

./RUN_OPERATOR.sh --session-dir "$SESSION" status
./RUN_OPERATOR.sh --session-dir "$SESSION" toolchain
./RUN_OPERATOR.sh --session-dir "$SESSION" quality
```

Danach in einer **realen KDE-X11-Sitzung**:

```bash
./RUN_OPERATOR.sh --session-dir "$SESSION" desktop --session x11
```


Langzeitrender-Vertrag erzeugen:

```bash
PYTHONPATH=src python3 scripts/build_long_render_contract.py \
  --audio-dir /mnt/eingaben-ro/audio \
  --image-dir /mnt/eingaben-ro/bilder \
  --package /pfad/VideoBatch_Fast_2.8.3-rc24.zip \
  --target-dir /mnt/langsames-usb/provoware-rc24-langzeitrender \
  --output "$SESSION/long-render-contract.json"
```

Realer Lauf:

```bash
./RUN_OPERATOR.sh --session-dir "$SESSION" long-render \
  --contract "$SESSION/long-render-contract.json"
```

Bei kontrolliertem Timeout/Abbruch denselben Vertrag wiederaufnehmen:

```bash
./RUN_OPERATOR.sh --session-dir "$SESSION" long-render \
  --contract "$SESSION/long-render-contract.json" --resume
```

Erst wenn Toolchain, externe Qualität, X11 und 96-Job-Langzeitrender für **dieselbe Candidate Identity** grün sind:

```bash
./RUN_OPERATOR.sh --session-dir "$SESSION" promotion-rehearsal
```

Die Rehearsal veröffentlicht **kein Stable-Artefakt**. Sie verifiziert Quality- und Physical-Evidence, erzeugt temporär eine Stable-Arbeitskopie und verlangt zwei byteidentische deterministische Pakete. Der Bericht liegt anschließend als `PROMOTION_REHEARSAL.json` im Sitzungsordner.

## Schutzregeln

- Jede Phase prüft `candidate_id`, `manifest_sha256` und `source_sha256` erneut.
- Nach einer Quell- oder Manifeständerung wird die vorhandene Sitzung als **stale** blockiert.
- Das Wheelhouse wird online aufgebaut. Direkt danach wird ein dedizierter pip-audit-Advisory-HTTP-Cache online vorgewärmt und gehasht; der eigentliche freigaberelevante Lauf aller vier externen Qualitätswerkzeuge erfolgt anschließend mit aktivierter Netzwerksperre gegen diesen eingefrorenen Cache.
- Source Distributions sind verboten; der Wheelhouse-/Installationsvertrag bleibt auf `--only-binary=:all:` und Hashprüfung begrenzt. Das folgt der pip-Empfehlung für sichere, reproduzierbare Installationen.
- X11 ist das einzige verpflichtende physische Desktop-Gate dieses Zielsystems; Wayland ist ausdrücklich nicht freigaberelevant.
- Ein Rehearsal-/internes Renderziel kann niemals `long_render.json` für Stable erzeugen.
