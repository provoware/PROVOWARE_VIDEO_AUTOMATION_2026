#!/usr/bin/env bash
set -Eeuo pipefail
ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
TMP_ROOT="$(mktemp -d -t videobatch-build-XXXXXX)"
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

printf 'BUILD-ARTEFAKTE · kontrolliert schreibender Schritt\n'
python3 "$ROOT_DIR/scripts/toolchain.py" gate --scope quality --quiet
"$ENV_PYTHON" "$ROOT_DIR/scripts/validate_version_contract.py"
"$ENV_PYTHON" "$ROOT_DIR/scripts/analyze_design_reference.py"
if ! command -v xvfb-run >/dev/null 2>&1; then
  printf '✕ xvfb-run fehlt. Lösung: sudo apt install xvfb\n'
  exit 1
fi
xvfb-run -a -s '-screen 0 2560x1440x24' "$ENV_PYTHON" "$ROOT_DIR/scripts/capture_visual_scenarios.py"
"$ENV_PYTHON" "$ROOT_DIR/scripts/build_visual_inspection.py"
"$ENV_PYTHON" "$ROOT_DIR/scripts/build_release_manifest.py"
"$ENV_PYTHON" "$ROOT_DIR/scripts/validate_release_manifest.py"
printf 'BUILD-ARTEFAKTE ERZEUGT UND VERIFIZIERT\n'
