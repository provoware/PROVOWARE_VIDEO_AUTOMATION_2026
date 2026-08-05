#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
EVIDENCE_DIR="${VIDEOBATCH_QUALITY_EVIDENCE_DIR:-$ROOT/quality-toolchain-evidence}"
AUDIT_CACHE="${VIDEOBATCH_PIP_AUDIT_CACHE:-$EVIDENCE_DIR/pip-audit-cache}"
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH="$ROOT/src"
export VIDEOBATCH_DIAGNOSTICS_DIR="$EVIDENCE_DIR/diagnostics"
export VIDEOBATCH_PIP_AUDIT_CACHE="$AUDIT_CACHE"

mkdir -p "$EVIDENCE_DIR" "$AUDIT_CACHE"
cd "$ROOT"

./quality-toolchain.sh build \
  2>&1 | tee "$EVIDENCE_DIR/wheelhouse-build.log"
./quality-toolchain.sh verify \
  2>&1 | tee "$EVIDENCE_DIR/wheelhouse-verify.log"
./quality-toolchain.sh prepare --offline-only --replace \
  2>&1 | tee "$EVIDENCE_DIR/offline-install-first.log"
python3 scripts/toolchain.py gate --scope quality \
  2>&1 | tee "$EVIDENCE_DIR/environment-gate.log"

QUALITY_PYTHON="$(python3 scripts/toolchain.py path --scope quality --quiet)"
"$QUALITY_PYTHON" - <<'PY' > "$EVIDENCE_DIR/installed-versions.json"
import importlib.metadata as metadata
import json
import platform
import sys

expected = {
    "ruff": "0.16.1",
    "mypy": "2.3.0",
    "bandit": "1.9.4",
    "pip-audit": "2.10.1",
}
actual = {name: metadata.version(name) for name in expected}
if actual != expected:
    raise SystemExit(f"Exact installed versions mismatch: {actual!r}")
print(json.dumps({
    "python": sys.version,
    "platform": platform.platform(),
    "packages": actual,
}, ensure_ascii=False, indent=2, sort_keys=True))
PY

cp toolchain_wheelhouse/TOOLCHAIN_WHEELHOUSE_MANIFEST.json \
  "$EVIDENCE_DIR/wheelhouse-manifest.json"
cp toolchain_wheelhouse/requirements-toolchain-resolved.lock \
  "$EVIDENCE_DIR/requirements-toolchain-resolved.lock"

set +e
"$QUALITY_PYTHON" -m pip_audit \
  --cache-dir "$AUDIT_CACHE" \
  --no-deps \
  --disable-pip \
  --progress-spinner off \
  -r requirements.lock \
  > "$EVIDENCE_DIR/pip-audit-cache-prime.log" 2>&1
prime_exit=$?
set -e
printf '%s\n' "$prime_exit" > "$EVIDENCE_DIR/pip-audit-cache-prime.exit"
find "$AUDIT_CACHE" -type f -printf '%P\t%s\n' \
  | sort > "$EVIDENCE_DIR/pip-audit-cache-inventory.tsv"
test -s "$EVIDENCE_DIR/pip-audit-cache-inventory.tsv"

# Recreate the environment after every online preparation step. This proves
# that the final installation itself uses only the verified local wheelhouse.
./quality-toolchain.sh prepare --offline-only --replace \
  2>&1 | tee "$EVIDENCE_DIR/offline-install-final.log"
./quality-toolchain.sh verify \
  2>&1 | tee "$EVIDENCE_DIR/wheelhouse-final-verify.log"

QUALITY_PYTHON="$(python3 scripts/toolchain.py path --scope quality --quiet)"
export PATH="$(dirname "$QUALITY_PYTHON"):$PATH"
set +e
"$QUALITY_PYTHON" scripts/run_external_quality.py \
  --mode required \
  --offline \
  2>&1 | tee "$EVIDENCE_DIR/offline-quality-gate.log"
gate_exit=${PIPESTATUS[0]}
set -e
printf '%s\n' "$gate_exit" > "$EVIDENCE_DIR/offline-quality-gate.exit"

"$QUALITY_PYTHON" - <<'PY'
import json
import os
from pathlib import Path

report_path = Path(os.environ["VIDEOBATCH_DIAGNOSTICS_DIR"]) / "external_quality_latest.json"
report = json.loads(report_path.read_text(encoding="utf-8"))
expected = ["ruff", "mypy", "bandit", "pip-audit"]
names = [item.get("tool") for item in report.get("results", [])]
if names != expected:
    raise SystemExit(f"Incomplete tool report: {names!r}")
if report.get("offline") is not True:
    raise SystemExit("Offline network guard was not active")
versions = {item["tool"]: item.get("version") for item in report["results"]}
required = {
    "ruff": "0.16.1",
    "mypy": "2.3.0",
    "bandit": "1.9.4",
    "pip-audit": "2.10.1",
}
if versions != required:
    raise SystemExit(f"Reported tool versions mismatch: {versions!r}")
print(json.dumps({
    "offline": True,
    "results": [
        {
            "tool": item.get("tool"),
            "version": item.get("version"),
            "status": item.get("status"),
            "returncode": item.get("returncode"),
        }
        for item in report["results"]
    ],
}, ensure_ascii=False, indent=2))
PY

exit "$gate_exit"
