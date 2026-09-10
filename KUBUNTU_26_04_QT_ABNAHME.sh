#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
PYTHON_BOOTSTRAP="${VIDEOBATCH_BOOTSTRAP_PYTHON:-python3}"
STATE_BASE="${XDG_STATE_HOME:-$HOME/.local/state}/VideoBatchFast/acceptance"
LOG_DIR="$STATE_BASE"
mkdir -p "$LOG_DIR"
LOG="$LOG_DIR/letzter-ein-klick-start.log"

show_error() {
    local message="$1"
    printf '%s\n' "$message" >&2
    if [[ -n "${WAYLAND_DISPLAY:-}" ]] && command -v kdialog >/dev/null 2>&1; then
        kdialog --title "VideoBatch · Qt-Abnahme" --error "$message" >/dev/null 2>&1 || true
    fi
}

if ! command -v "$PYTHON_BOOTSTRAP" >/dev/null 2>&1; then
    show_error "Qt-Abnahme blockiert: Python 3 wurde nicht gefunden."
    exit 127
fi

cd "$ROOT_DIR"
export PYTHONPATH="$ROOT_DIR/src${PYTHONPATH:+:$PYTHONPATH}"
export QT_QPA_PLATFORM=wayland

{
    printf '%s\n' "VideoBatch Qt-Abnahme gestartet: $(date --iso-8601=seconds)"
    printf '%s\n' "[1/4] Echtes Kubuntu-26.04-Wayland-System prüfen"
} >"$LOG"

if ! "$PYTHON_BOOTSTRAP" "$ROOT_DIR/scripts/kubuntu_26_04_wayland_check.py" >>"$LOG" 2>&1; then
    show_error "Qt-Abnahme blockiert: Dieser Test benötigt echtes Kubuntu 26.04 mit KDE Plasma in einer Wayland-Sitzung. Details: $LOG"
    exit 2
fi

printf '%s\n' "[2/4] Verifizierte Qt-Laufzeit vorbereiten" >>"$LOG"
if ! "$PYTHON_BOOTSTRAP" "$ROOT_DIR/scripts/toolchain.py" prepare --scope runtime --auto-repair --quiet >>"$LOG" 2>&1; then
    show_error "Qt-Laufzeit konnte nicht vorbereitet werden. Falls lokale Pakete fehlen, darf eine Online-Reparatur nur nach Ihrer grafischen Bestätigung erfolgen. Details: $LOG"
    exit 3
fi

RUNTIME_PY="$("$PYTHON_BOOTSTRAP" "$ROOT_DIR/scripts/toolchain.py" path --scope runtime --quiet | tail -n 1)"
if [[ ! -x "$RUNTIME_PY" ]]; then
    show_error "Qt-Abnahme blockiert: Die geprüfte Python-Laufzeit wurde nicht gefunden. Details: $LOG"
    exit 4
fi

printf '%s\n' "[3/4] Laufzeitabschlussprüfung" >>"$LOG"
if ! "$RUNTIME_PY" "$ROOT_DIR/scripts/toolchain.py" gate --scope runtime --quiet >>"$LOG" 2>&1; then
    show_error "Qt-Abnahme blockiert: Die Qt-Laufzeit hat ihre Abschlussprüfung nicht bestanden. Details: $LOG"
    exit 5
fi

printf '%s\n' "[4/4] Echte Qt-Oberfläche, Screenshots und Ampelkarte öffnen" >>"$LOG"
set +e
"$RUNTIME_PY" "$ROOT_DIR/scripts/qt_desktop_acceptance.py" 2>&1 | tee -a "$LOG"
RESULT=${PIPESTATUS[0]}
set -e

case "$RESULT" in
    0)
        if command -v kdialog >/dev/null 2>&1; then
            kdialog --title "VideoBatch · Qt-Abnahme" --passivepopup "🟢 Qt-Abnahme vollständig bestanden." 4 >/dev/null 2>&1 || true
        fi
        ;;
    3)
        if command -v kdialog >/dev/null 2>&1; then
            kdialog --title "VideoBatch · Qt-Abnahme" --passivepopup "🟡 Technik bestanden; manuelle Sichtfreigabe noch offen." 5 >/dev/null 2>&1 || true
        fi
        ;;
    *)
        show_error "Qt-Abnahme ist noch nicht freigegeben. Es wurden keine Projekt- oder Mediendateien verändert. Details: $LOG"
        ;;
esac

exit "$RESULT"
