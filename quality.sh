#!/usr/bin/env bash
set -Eeuo pipefail
ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
TMP_ROOT="$(mktemp -d -t videobatch-quality-XXXXXX)"
trap 'rm -rf "$TMP_ROOT"' EXIT
python3 "$ROOT_DIR/scripts/toolchain.py" prepare --scope quality --auto-repair --quiet
ENV_PYTHON="$(python3 "$ROOT_DIR/scripts/toolchain.py" path --scope quality --quiet)"
export PATH="$(dirname "$ENV_PYTHON"):$PATH"
export PYTHONPATH="$ROOT_DIR/src${PYTHONPATH:+:$PYTHONPATH}"
export PYTHONDONTWRITEBYTECODE=1
export VIDEOBATCH_DIAGNOSTICS_DIR="$TMP_ROOT/diagnostics"
export COVERAGE_FILE="$TMP_ROOT/.coverage"
export MYPY_CACHE_DIR="$TMP_ROOT/mypy-cache"
export RUFF_CACHE_DIR="$TMP_ROOT/ruff-cache"

python3 "$ROOT_DIR/scripts/toolchain.py" gate --scope quality --run-external --quiet
"$ENV_PYTHON" "$ROOT_DIR/scripts/validate_version_contract.py"
"$ENV_PYTHON" "$ROOT_DIR/scripts/render_release_docs.py" --check
"$ENV_PYTHON" "$ROOT_DIR/scripts/internal_quality_gate.py"
"$ENV_PYTHON" "$ROOT_DIR/scripts/validate_text_resources.py"
"$ENV_PYTHON" -m pytest -q -p no:cacheprovider \
  --cov=videobatch_fast \
  --cov-config="$ROOT_DIR/pyproject.toml" \
  --cov-report=term-missing:skip-covered \
  --cov-report=json:"$TMP_ROOT/coverage.json" \
  --cov-fail-under=0 \
  "$ROOT_DIR/tests"
"$ENV_PYTHON" "$ROOT_DIR/scripts/coverage_policy.py" "$TMP_ROOT/coverage.json" 80 65
"$ENV_PYTHON" "$ROOT_DIR/scripts/run_fault_lab.py" --output "$TMP_ROOT/fault_lab.json"
printf 'VERBINDLICHE CODEQUALITÄTSSTRECKE BESTANDEN\n'
