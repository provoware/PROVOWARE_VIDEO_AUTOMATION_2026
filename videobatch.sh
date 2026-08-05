#!/usr/bin/env bash
set -Eeuo pipefail
SELF="${BASH_SOURCE[0]}"
ROOT_DIR="$(cd -- "$(dirname -- "$SELF")" && pwd -P)"
ACTION="${1:-start}"
if [[ $# -gt 0 ]]; then shift; fi
BOOTSTRAP_PYTHON="${VIDEOBATCH_BOOTSTRAP_PYTHON:-python3}"
STATE_ROOT="${XDG_STATE_HOME:-$HOME/.local/state}/VideoBatchFast"

usage() {
  cat <<'EOF'
VideoBatch Fast – automatischer zentraler Einstieg

  ./videobatch.sh                 automatisch prüfen, reparieren und starten
  ./videobatch.sh setup           vollständige Umgebung automatisch vorbereiten
  ./videobatch.sh repair          Paketbasis und Umgebung vollständig erneuern
  ./videobatch.sh doctor          verständliche Systemdiagnose
  ./videobatch.sh check           kompakter System- und Toolchainstatus
  ./videobatch.sh test [--core]   Release- oder Kernprüfung
  ./videobatch.sh quality         Ruff, MyPy, Bandit, pip-audit und Tests
  ./videobatch.sh verify          vollständige Releaseprüfung
  ./videobatch.sh finalize        autonom prüfen und Stable-ZIP erzeugen
  ./videobatch.sh fault-lab       isoliertes Stabilitäts- und Recoverylabor
  ./videobatch.sh retry-status    Wiederanlaufliste vollständig lesend anzeigen
  ./videobatch.sh recovery-check  Wiederanlauf und Journale vollständig lesend vergleichen
  ./videobatch.sh portable-build  portable Offline-Ausgabe erzeugen
  ./videobatch.sh logs            letzten Start- und Toolchainbericht anzeigen
  ./videobatch.sh help            diese Hilfe anzeigen

Option für vollständig offline:
  ./videobatch.sh setup --offline-only
EOF
}

fatal() {
  printf '\n✕ %s\n' "$1" >&2
  printf '  Diagnose wird automatisch ausgeführt.\n\n' >&2
  "$BOOTSTRAP_PYTHON" "$ROOT_DIR/scripts/user_diagnostics.py" --brief 2>/dev/null || true
  exit "${2:-1}"
}

require_project() {
  [[ -f "$ROOT_DIR/VERSION.json" && -f "$ROOT_DIR/scripts/toolchain.py" && -f "$ROOT_DIR/TOOLCHAIN_CONTRACT.json" ]] || \
    fatal "Das Projekt ist unvollständig oder wurde während einer Reparatur beschädigt." 9
  [[ ! -L "$ROOT_DIR" ]] || fatal "Der Projektordner darf kein symbolischer Link sein." 9
}

require_system() {
  command -v "$BOOTSTRAP_PYTHON" >/dev/null 2>&1 || fatal "Python 3 fehlt. Kubuntu: sudo apt install python3 python3-venv python3-pip python3-tk" 10
  "$BOOTSTRAP_PYTHON" - <<'PY' >/dev/null 2>&1 || fatal "Tk fehlt. Kubuntu: sudo apt install python3-tk" 11
import tkinter
PY
  "$BOOTSTRAP_PYTHON" -m venv --help >/dev/null 2>&1 || fatal "python3-venv fehlt. Kubuntu: sudo apt install python3-venv" 12
}

prepare_toolchain() {
  local scope="${1:-runtime}"
  if [[ $# -gt 0 ]]; then shift; fi
  local replace=0 offline=0
  for arg in "$@"; do
    case "$arg" in
      --replace) replace=1 ;;
      --offline-only) offline=1 ;;
      --allow-online) ;;
      *) fatal "Unbekannte Setup-Option: $arg" 2 ;;
    esac
  done
  local args=(prepare --scope "$scope" --auto-repair)
  [[ "$replace" == 1 ]] && args+=(--replace)
  [[ "$offline" == 1 ]] && args+=(--offline-only)
  "$BOOTSTRAP_PYTHON" "$ROOT_DIR/scripts/toolchain.py" "${args[@]}"
}

toolchain_python() {
  local scope="${1:-runtime}"
  "$BOOTSTRAP_PYTHON" "$ROOT_DIR/scripts/toolchain.py" path --scope "$scope" --quiet
}


start_application() {
  require_system
  exec "$BOOTSTRAP_PYTHON" "$ROOT_DIR/scripts/bootstrap.py"
}


show_logs() {
  local start_log tool_log
  start_log="$(find "$STATE_ROOT/logs" -maxdepth 1 -type f -name 'start_*.log' -printf '%T@ %p\n' 2>/dev/null | sort -nr | head -n1 | cut -d' ' -f2-)"
  tool_log="$(find "$STATE_ROOT/toolchain" -maxdepth 1 -type f -name '*.log' -printf '%T@ %p\n' 2>/dev/null | sort -nr | head -n1 | cut -d' ' -f2-)"
  [[ -n "$start_log" ]] && { printf '\nLETZTER STARTBERICHT: %s\n' "$start_log"; tail -n 80 "$start_log"; }
  [[ -n "$tool_log" ]] && { printf '\nLETZTER TOOLCHAINBERICHT: %s\n' "$tool_log"; tail -n 80 "$tool_log"; }
  [[ -n "$start_log$tool_log" ]] || printf 'Noch keine Protokolle vorhanden.\n'
}

require_project
case "$ACTION" in
  start)
    [[ $# -eq 0 ]] || fatal "Unbekannte Startoption: $1" 2
    start_application
    ;;
  setup)
    require_system
    prepare_toolchain runtime "$@"
    ;;
  repair)
    require_system
    prepare_toolchain runtime --replace "$@"
    printf '\n✓ Reparatur abgeschlossen. Anwendung wird gestartet.\n'
    start_application
    ;;
  doctor)
    require_system
    exec "$BOOTSTRAP_PYTHON" "$ROOT_DIR/scripts/user_diagnostics.py" "$@"
    ;;
  check|status)
    require_system
    "$BOOTSTRAP_PYTHON" "$ROOT_DIR/scripts/user_diagnostics.py" --brief
    ;;
  test)
    exec "$ROOT_DIR/test.sh" "$@"
    ;;
  quality)
    [[ $# -eq 0 ]] || fatal "quality akzeptiert keine Zusatzoptionen." 2
    exec "$ROOT_DIR/quality.sh"
    ;;
  verify)
    [[ $# -eq 0 ]] || fatal "verify akzeptiert keine Zusatzoptionen." 2
    exec "$ROOT_DIR/verify_release.sh"
    ;;
  finalize|finalisieren)
    require_system
    prepare_toolchain quality
    ENV_PYTHON="$(toolchain_python quality)"
    export PYTHONPATH="$ROOT_DIR/src${PYTHONPATH:+:$PYTHONPATH}"
    exec "$ENV_PYTHON" "$ROOT_DIR/scripts/finalize_release.py" "$@"
    ;;
  stable)
    exec "$ROOT_DIR/stable_release.sh" "$@"
    ;;
  fault-lab)
    require_system
    RUNTIME_PYTHON="$($BOOTSTRAP_PYTHON "$ROOT_DIR/scripts/toolchain.py" path --scope runtime --quiet 2>/dev/null || true)"
    [[ -x "$RUNTIME_PYTHON" ]] || RUNTIME_PYTHON="$BOOTSTRAP_PYTHON"
    export PYTHONPATH="$ROOT_DIR/src${PYTHONPATH:+:$PYTHONPATH}"
    exec "$RUNTIME_PYTHON" "$ROOT_DIR/scripts/run_fault_lab.py" "$@"
    ;;
  retry-status|wiederanlauf-diagnose)
    export PYTHONPATH="$ROOT_DIR/src${PYTHONPATH:+:$PYTHONPATH}"
    exec "$BOOTSTRAP_PYTHON" -m videobatch_fast.retry_diagnostics "$@"
    ;;
  recovery-check|wiederanlauf-konsistenz)
    export PYTHONPATH="$ROOT_DIR/src${PYTHONPATH:+:$PYTHONPATH}"
    exec "$BOOTSTRAP_PYTHON" -m videobatch_fast.recovery_consistency "$@"
    ;;
  portable-build)
    require_system
    exec "$BOOTSTRAP_PYTHON" "$ROOT_DIR/scripts/build_portable_bundle.py" "$@"
    ;;
  assurance)
    require_system
    prepare_toolchain quality
    ENV_PYTHON="$(toolchain_python quality)"
    export PYTHONPATH="$ROOT_DIR/src${PYTHONPATH:+:$PYTHONPATH}"
    exec "$ENV_PYTHON" "$ROOT_DIR/scripts/run_assurance_lab.py" "$@"
    ;;
  backup-approval-key)
    require_system
    prepare_toolchain quality
    ENV_PYTHON="$(toolchain_python quality)"
    export PYTHONPATH="$ROOT_DIR/src${PYTHONPATH:+:$PYTHONPATH}"
    exec "$ENV_PYTHON" "$ROOT_DIR/scripts/archive_visual_approval_key.py" "$@"
    ;;
  startup-status)
    report="$STATE_ROOT/startup/latest.json"
    if [[ -f "$report" ]]; then cat "$report"; else printf 'Noch kein Startbericht vorhanden.\n'; fi
    ;;
  logs)
    show_logs
    ;;
  help|-h|--help)
    usage
    ;;
  *)
    printf 'Unbekannter Befehl: %s\n\n' "$ACTION" >&2
    usage >&2
    exit 2
    ;;
esac
