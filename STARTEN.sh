#!/usr/bin/env bash
set -Eeuo pipefail
ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
BOOTSTRAP_PYTHON="${VIDEOBATCH_BOOTSTRAP_PYTHON:-python3}"
DEBUG_LAUNCHER="$ROOT_DIR/scripts/debug_launcher.py"

# Der außerhalb des austauschbaren Programmordners liegende Starter bleibt
# verwendbar, auch wenn ein Update scripts/debug_launcher.py beschädigt.
EXTERNAL_STARTER="$(dirname -- "$ROOT_DIR")/.$(basename -- "$ROOT_DIR").independent_start.py"
if [[ -f "$EXTERNAL_STARTER" && ! -L "$EXTERNAL_STARTER" ]]; then
    if ! command -v "$BOOTSTRAP_PYTHON" >/dev/null 2>&1; then
        printf 'Python 3 fehlt: %s\\n' "$BOOTSTRAP_PYTHON" >&2
        exit 127
    fi
    exec "$BOOTSTRAP_PYTHON" "$EXTERNAL_STARTER" "$ROOT_DIR" "$@"
fi

if ! command -v "$BOOTSTRAP_PYTHON" >/dev/null 2>&1; then
    printf '%s\n' \
        'VideoBatch konnte nicht gestartet werden.' \
        '' \
        "Problem: Python 3 ist nicht verfügbar oder nicht ausführbar ($BOOTSTRAP_PYTHON)." \
        'Lösung: Installieren Sie Python 3 und starten Sie STARTEN.sh danach erneut.' >&2
    exit 127
fi

if [[ ! -f "$DEBUG_LAUNCHER" ]]; then
    printf '%s\n' \
        'VideoBatch konnte nicht gestartet werden.' \
        '' \
        'Problem: Eine benötigte Startdatei fehlt.' \
        "Lösung: Entpacken Sie das vollständige VideoBatch-Projekt erneut. Fehlend: $DEBUG_LAUNCHER" >&2
    exit 127
fi

exec "$BOOTSTRAP_PYTHON" "$DEBUG_LAUNCHER" "$@"
