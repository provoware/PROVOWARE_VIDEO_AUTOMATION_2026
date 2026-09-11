#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
PYTHON_BOOTSTRAP="${VIDEOBATCH_BOOTSTRAP_PYTHON:-python3}"
REAL_HOME="${HOME:?HOME ist nicht gesetzt}"
REAL_STATE_ROOT="${XDG_STATE_HOME:-$REAL_HOME/.local/state}/VideoBatchFast"
STATE_BASE="$REAL_STATE_ROOT/acceptance"
EVIDENCE_ROOT="$REAL_STATE_ROOT/stable-evidence"
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

# Die Abnahme bekommt eine frische, eigene Benutzer-Heimat. Damit bleiben die
# normale Launcherpflege und alle persistenten XDG-Schreibpfade vollständig
# vom echten Benutzerkonto getrennt. XDG_RUNTIME_DIR wird absichtlich nicht
# verändert, weil Wayland/DBus die echte Sitzung darüber bereitstellen.
umask 077
TEST_HOME="$(mktemp -d "$STATE_BASE/test-home.XXXXXX")"
printf '%s\n' "$TEST_HOME" >"$STATE_BASE/letzte-test-heimat.txt"
export VIDEOBATCH_ACCEPTANCE_TEST_HOME="$TEST_HOME"
export HOME="$TEST_HOME"
export XDG_DATA_HOME="$TEST_HOME/.local/share"
export XDG_CONFIG_HOME="$TEST_HOME/.config"
export XDG_STATE_HOME="$TEST_HOME/.local/state"
export XDG_CACHE_HOME="$TEST_HOME/.cache"
mkdir -p "$XDG_DATA_HOME" "$XDG_CONFIG_HOME" "$XDG_STATE_HOME" "$XDG_CACHE_HOME"
unset VIDEOBATCH_INSTALL_ROOT \
      VIDEOBATCH_PORTABLE_LAUNCHER \
      VIDEOBATCH_PORTABLE \
      VIDEOBATCH_RUNTIME_PYTHON \
      VIDEOBATCH_QUALITY_PYTHON \
      VIDEOBATCH_TOOLCHAIN_PYTHON

cd "$ROOT_DIR"
export PYTHONPATH="$ROOT_DIR/src${PYTHONPATH:+:$PYTHONPATH}"
export QT_QPA_PLATFORM=wayland

{
    printf '%s\n' "VideoBatch Qt-Abnahme gestartet: $(date --iso-8601=seconds)"
    printf '%s\n' "Isolierte Test-Heimat: $TEST_HOME"
    printf '%s\n' "XDG_RUNTIME_DIR bleibt Sitzungspfad: ${XDG_RUNTIME_DIR:-<nicht gesetzt>}"
    printf '%s\n' "[1/4] Echtes Kubuntu-26.04-Wayland-System prüfen"
} >"$LOG"

if ! "$PYTHON_BOOTSTRAP" "$ROOT_DIR/scripts/kubuntu_26_04_wayland_check.py" >>"$LOG" 2>&1; then
    show_error "Qt-Abnahme blockiert: Dieser Test benötigt echtes Kubuntu 26.04 mit KDE Plasma in einer Wayland-Sitzung. Details: $LOG"
    exit 2
fi

printf '%s\n' "[2/4] Verifizierte Qt-Laufzeit in der Test-Heimat vorbereiten" >>"$LOG"
if ! "$PYTHON_BOOTSTRAP" "$ROOT_DIR/scripts/toolchain.py" prepare --scope runtime --auto-repair --quiet >>"$LOG" 2>&1; then
    show_error "Qt-Laufzeit konnte nicht vorbereitet werden. Falls lokale Pakete fehlen, darf eine Online-Reparatur nur nach Ihrer grafischen Bestätigung erfolgen. Details: $LOG"
    exit 3
fi

RUNTIME_PY="$("$PYTHON_BOOTSTRAP" "$ROOT_DIR/scripts/toolchain.py" path --scope runtime --quiet | tail -n 1)"
if [[ ! -x "$RUNTIME_PY" ]]; then
    show_error "Qt-Abnahme blockiert: Die geprüfte Python-Laufzeit wurde in der Test-Heimat nicht gefunden. Details: $LOG"
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

printf '%s\n' "[SICHERHEIT] Launcher-/Desktop-Isolation fail-closed prüfen" >>"$LOG"
set +e
"$RUNTIME_PY" "$ROOT_DIR/scripts/validate_acceptance_isolation.py" \
    --test-home "$TEST_HOME" \
    --report-root "$XDG_STATE_HOME/VideoBatchFast/acceptance" >>"$LOG" 2>&1
ISOLATION_RESULT=$?
set -e
if [[ "$ISOLATION_RESULT" -ne 0 && ( "$RESULT" -eq 0 || "$RESULT" -eq 3 ) ]]; then
    RESULT=6
fi

# Nur eine vollständig grüne reale Abnahme darf den maschinenlesbaren Stable-Nachweis
# erzeugen. Der Nachweis wird außerhalb der isolierten Test-Heimat in einem festen,
# kandidatengebundenen Ordner abgelegt; fehlende oder widersprüchliche Daten blockieren.
if [[ "$RESULT" -eq 0 ]]; then
    ACCEPTANCE_JSON="$(find "$XDG_STATE_HOME/VideoBatchFast/acceptance" -type f -name acceptance.json -printf '%T@ %p\n' 2>/dev/null | sort -nr | head -n 1 | cut -d' ' -f2-)"
    if [[ -z "$ACCEPTANCE_JSON" || ! -f "$ACCEPTANCE_JSON" ]]; then
        printf '%s\n' "[STABLE] acceptance.json wurde nach grüner Abnahme nicht gefunden." >>"$LOG"
        RESULT=7
    elif ! "$RUNTIME_PY" "$ROOT_DIR/scripts/export_stable_acceptance_evidence.py" \
        --evidence-root "$EVIDENCE_ROOT" \
        kubuntu --acceptance "$ACCEPTANCE_JSON" >>"$LOG" 2>&1; then
        RESULT=7
    else
        printf '%s\n' "[STABLE] Kubuntu-Nachweis automatisch unter $EVIDENCE_ROOT erzeugt." >>"$LOG"
    fi
fi

case "$RESULT" in
    0)
        if command -v kdialog >/dev/null 2>&1; then
            kdialog --title "VideoBatch · Qt-Abnahme" --passivepopup "🟢 Qt-Abnahme vollständig bestanden · Stable-Nachweis erzeugt." 5 >/dev/null 2>&1 || true
        fi
        ;;
    3)
        if command -v kdialog >/dev/null 2>&1; then
            kdialog --title "VideoBatch · Qt-Abnahme" --passivepopup "🟡 Technik bestanden; manuelle Sichtfreigabe noch offen · Test-Heimat isoliert." 5 >/dev/null 2>&1 || true
        fi
        ;;
    6)
        show_error "Qt-Abnahme blockiert: Die Launcher-/Desktop-Isolation konnte nicht sicher nachgewiesen werden. Details: $LOG"
        ;;
    7)
        show_error "Qt-Abnahme selbst war grün, aber der kandidatengebundene Stable-Nachweis konnte nicht sicher erzeugt werden. Stable bleibt blockiert. Details: $LOG"
        ;;
    *)
        show_error "Qt-Abnahme ist noch nicht freigegeben. Es wurden keine Projekt- oder Mediendateien verändert. Details: $LOG"
        ;;
esac

exit "$RESULT"
