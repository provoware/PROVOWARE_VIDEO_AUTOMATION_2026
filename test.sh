#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
MODE="full"

usage() {
  cat <<'EOF'
Verwendung: ./test.sh [--core | --docs | --help]

  --docs  Schnelle Dokumentationsprüfung ohne Toolchain, Coverage, GUI oder Releasefreigabe.
  --core  Kernprüfung ohne externe Qualitätswerkzeuge; nicht releasefreigebend.
  --help  Diese Hilfe anzeigen.
  ohne Option  Vollständige schreibgeschützte Releaseprüfung.

Es darf höchstens ein Modus angegeben werden.
EOF
}

fail_usage() {
  printf 'FEHLER: %s\n\n' "$1" >&2
  usage >&2
  exit 2
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --docs)
      [[ "$MODE" == "full" ]] || fail_usage "Mehrere Prüfmodi wurden kombiniert."
      MODE="docs"
      ;;
    --core)
      [[ "$MODE" == "full" ]] || fail_usage "Mehrere Prüfmodi wurden kombiniert."
      MODE="core"
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    --)
      shift
      [[ $# -eq 0 ]] || fail_usage "Positionsargumente werden nicht unterstützt: $*"
      break
      ;;
    *)
      fail_usage "Unbekannte Option: $1"
      ;;
  esac
  shift
done

PYTHON_BOOTSTRAP="${PYTHON:-python3}"
if ! command -v "$PYTHON_BOOTSTRAP" >/dev/null 2>&1; then
  printf 'FEHLER: Python wurde nicht gefunden: %s\n' "$PYTHON_BOOTSTRAP" >&2
  exit 127
fi

export PYTHONDONTWRITEBYTECODE=1
export PYTHONUTF8=1
export PYTHONPATH="$ROOT_DIR/src${PYTHONPATH:+:$PYTHONPATH}"

run_docs() {
  local started_at=$SECONDS
  printf 'VideoBatch · schnelle Dokumentationsprüfung\n'
  printf 'Projekt: %s\n\n' "$ROOT_DIR"

  "$PYTHON_BOOTSTRAP" -m py_compile \
    "$ROOT_DIR/scripts/validate_documentation.py" \
    "$ROOT_DIR/tests/test_documentation_contract.py" \
    "$ROOT_DIR/src/videobatch_fast/canonical_shell_workspace.py"

  "$PYTHON_BOOTSTRAP" "$ROOT_DIR/tests/test_documentation_contract.py"
  "$PYTHON_BOOTSTRAP" "$ROOT_DIR/scripts/validate_documentation.py"

  printf '\nDOKUMENTATIONSPRÜFUNG BESTANDEN · Dauer %ss · keine Releasefreigabe\n' \
    "$((SECONDS - started_at))"
}

if [[ "$MODE" == "docs" ]]; then
  run_docs
  exit 0
fi

TMP_ROOT="$(mktemp -d -t videobatch-test-XXXXXX)"
cleanup() {
  local status=$?
  rm -rf -- "$TMP_ROOT"
  exit "$status"
}
trap cleanup EXIT HUP INT TERM

"$PYTHON_BOOTSTRAP" "$ROOT_DIR/scripts/toolchain.py" prepare \
  --scope quality --auto-repair --quiet
ENV_PYTHON="$("$PYTHON_BOOTSTRAP" "$ROOT_DIR/scripts/toolchain.py" path --scope quality --quiet)"
if [[ ! -x "$ENV_PYTHON" ]]; then
  printf 'FEHLER: Qualitäts-Python ist nicht ausführbar: %s\n' "$ENV_PYTHON" >&2
  exit 1
fi

export PATH="$(dirname -- "$ENV_PYTHON"):$PATH"
export XDG_CONFIG_HOME="$TMP_ROOT/config"
export XDG_STATE_HOME="$TMP_ROOT/state"
export XDG_CACHE_HOME="$TMP_ROOT/cache"
export VIDEOBATCH_DIAGNOSTICS_DIR="$TMP_ROOT/diagnostics"
export COVERAGE_FILE="$TMP_ROOT/.coverage"
export MYPY_CACHE_DIR="$TMP_ROOT/mypy-cache"
export RUFF_CACHE_DIR="$TMP_ROOT/ruff-cache"

VERSION="$(
  "$ENV_PYTHON" -c \
    'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8"))["build"])' \
    "$ROOT_DIR/VERSION.json"
)"

if [[ "$MODE" == "full" && "${VIDEOBATCH_QUALITY_ALREADY_VERIFIED:-0}" != "1" ]]; then
  "$PYTHON_BOOTSTRAP" "$ROOT_DIR/scripts/toolchain.py" gate \
    --scope quality --run-external --quiet
fi

if [[ "$MODE" == "core" ]]; then
  printf 'provoware - videoautomation - 2026 · %s – KERNPRÜFUNG, NICHT RELEASEFREIGEBEND\n\n' \
    "$VERSION"
else
  printf 'provoware - videoautomation - 2026 · %s – schreibgeschützte Releaseprüfung\n\n' \
    "$VERSION"
fi

# Der schnelle Dokumentationsvertrag läuft früh, bevor teure Prüfungen beginnen.
"$ENV_PYTHON" "$ROOT_DIR/tests/test_documentation_contract.py"
"$ENV_PYTHON" "$ROOT_DIR/scripts/validate_documentation.py"
"$ENV_PYTHON" "$ROOT_DIR/scripts/validate_release_manifest.py"
"$ENV_PYTHON" "$ROOT_DIR/scripts/validate_version_contract.py"
"$ENV_PYTHON" "$ROOT_DIR/scripts/render_release_docs.py" --check
"$ENV_PYTHON" "$ROOT_DIR/scripts/verify_compile_isolated.py"
"$ENV_PYTHON" "$ROOT_DIR/scripts/validate_registries.py"
"$ENV_PYTHON" "$ROOT_DIR/scripts/architecture_audit.py"
"$ENV_PYTHON" "$ROOT_DIR/scripts/internal_quality_gate.py"
"$ENV_PYTHON" "$ROOT_DIR/scripts/check_event_architecture.py"
"$ENV_PYTHON" "$ROOT_DIR/scripts/check_event_registry.py"
"$ENV_PYTHON" "$ROOT_DIR/scripts/validate_text_resources.py"
"$ENV_PYTHON" "$ROOT_DIR/scripts/validate_quick_modes.py"
"$ENV_PYTHON" "$ROOT_DIR/scripts/verify_plugins.py"
"$ENV_PYTHON" "$ROOT_DIR/scripts/run_assurance_lab.py"
"$ENV_PYTHON" -m pytest -q -p no:cacheprovider \
  --cov=videobatch_fast \
  --cov-config="$ROOT_DIR/pyproject.toml" \
  --cov-report=term-missing:skip-covered \
  --cov-report=json:"$TMP_ROOT/coverage.json" \
  --cov-fail-under=0 \
  "$ROOT_DIR/tests"
"$ENV_PYTHON" "$ROOT_DIR/scripts/coverage_policy.py" "$TMP_ROOT/coverage.json" 80 65

if command -v xvfb-run >/dev/null 2>&1; then
  xvfb-run -a -s '-screen 0 1920x1080x24' \
    "$ENV_PYTHON" "$ROOT_DIR/scripts/test_workspace_layout_profiles_gui.py"
elif [[ -n "${DISPLAY:-}${WAYLAND_DISPLAY:-}" ]]; then
  printf '! xvfb-run fehlt · GUI-Rundtrip läuft in der aktiven Desktop-Sitzung\n'
  "$ENV_PYTHON" "$ROOT_DIR/scripts/test_workspace_layout_profiles_gui.py"
else
  printf '✕ GUI-RUNDTRIP BLOCKIERT · weder xvfb-run noch Desktop-Sitzung verfügbar\n'
  exit 1
fi

"$ENV_PYTHON" "$ROOT_DIR/scripts/verify_visual_isolated.py"
"$ENV_PYTHON" "$ROOT_DIR/scripts/check_visual_approval.py"
"$ENV_PYTHON" "$ROOT_DIR/scripts/validate_release_manifest.py"

if [[ "$MODE" == "core" ]]; then
  printf '\nKERNPRÜFUNG BESTANDEN · keine Releasefreigabe ohne externe Qualitätsgates\n'
else
  printf '\nALLE RELEASEPRÜFUNGEN BESTANDEN · Paketdateien blieben unverändert\n'
fi
