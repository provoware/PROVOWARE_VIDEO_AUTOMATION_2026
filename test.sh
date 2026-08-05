#!/usr/bin/env bash
set -Eeuo pipefail
ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
CORE_ONLY=0
if [[ "${1:-}" == "--core" ]]; then CORE_ONLY=1; shift; fi
if [[ $# -gt 0 ]]; then printf 'Unbekannte Option: %s\n' "$1" >&2; exit 2; fi
TMP_ROOT="$(mktemp -d -t videobatch-test-XXXXXX)"
trap 'rm -rf "$TMP_ROOT"' EXIT
python3 "$ROOT_DIR/scripts/toolchain.py" prepare --scope quality --auto-repair --quiet
ENV_PYTHON="$(python3 "$ROOT_DIR/scripts/toolchain.py" path --scope quality --quiet)"
export PATH="$(dirname "$ENV_PYTHON"):$PATH"
export PYTHONPATH="$ROOT_DIR/src${PYTHONPATH:+:$PYTHONPATH}"
export PYTHONDONTWRITEBYTECODE=1
export XDG_CONFIG_HOME="$TMP_ROOT/config"
export XDG_STATE_HOME="$TMP_ROOT/state"
export XDG_CACHE_HOME="$TMP_ROOT/cache"
export VIDEOBATCH_DIAGNOSTICS_DIR="$TMP_ROOT/diagnostics"
export COVERAGE_FILE="$TMP_ROOT/.coverage"
export MYPY_CACHE_DIR="$TMP_ROOT/mypy-cache"
export RUFF_CACHE_DIR="$TMP_ROOT/ruff-cache"
VERSION="$("$ENV_PYTHON" -c 'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8"))["build"])' "$ROOT_DIR/VERSION.json")"

if [[ "$CORE_ONLY" == "0" && "${VIDEOBATCH_QUALITY_ALREADY_VERIFIED:-0}" != "1" ]]; then
  python3 "$ROOT_DIR/scripts/toolchain.py" gate --scope quality --run-external --quiet
fi

if [[ "$CORE_ONLY" == "1" ]]; then
  printf 'provoware - videoautomation - 2026 · %s – KERNPRÜFUNG, NICHT RELEASEFREIGEBEND\n\n' "$VERSION"
else
  printf 'provoware - videoautomation - 2026 · %s – schreibgeschützte Releaseprüfung\n\n' "$VERSION"
fi
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
  xvfb-run -a -s '-screen 0 1920x1080x24' "$ENV_PYTHON" "$ROOT_DIR/scripts/test_workspace_layout_profiles_gui.py"
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
if [[ "$CORE_ONLY" == "1" ]]; then
  printf '\nKERNPRÜFUNG BESTANDEN · keine Releasefreigabe ohne externe Qualitätsgates\n'
else
  printf '\nALLE RELEASEPRÜFUNGEN BESTANDEN · Paketdateien blieben unverändert\n'
fi
