#!/usr/bin/env bash
set -euo pipefail

REPO_SLUG="provoware/PROVOWARE_VIDEO_AUTOMATION_2026"
TARGET_BRANCH="agent/welle25-ui-phase4-canonical-baseline"
EXPECTED_SHA256="539bcd6ecaed009f02658637038138905495f75ee3da751bf5fc9b27a438a208"
EXPECTED_ZIP="PROVOWARE_VIDEO_AUTOMATION_2026_WELLE25_UI_PHASE4_FINAL_GEFIXT.zip"

usage() {
  cat <<'EOF'
Usage:
  scripts/import_phase4_artifact.sh /path/to/PROVOWARE_VIDEO_AUTOMATION_2026_WELLE25_UI_PHASE4_FINAL_GEFIXT.zip --push

The importer:
  1. verifies the exact Phase-4 ZIP SHA-256,
  2. requires the canonical Phase-4 baseline branch,
  3. synchronizes the complete artifact tree into the checkout,
  4. preserves the GitHub baseline contract and this importer,
  5. runs ZIP CRC, git diff --check and focused Python syntax checks,
  6. commits the exact synchronized tree and pushes only with --push.
EOF
}

[[ $# -eq 2 && "$2" == "--push" ]] || { usage >&2; exit 64; }
ZIP_PATH="$(readlink -f "$1")"
[[ -f "$ZIP_PATH" ]] || { echo "ERROR: ZIP not found: $ZIP_PATH" >&2; exit 66; }
[[ "$(basename "$ZIP_PATH")" == "$EXPECTED_ZIP" ]] || {
  echo "ERROR: expected file name $EXPECTED_ZIP" >&2
  exit 65
}

for cmd in git unzip sha256sum rsync python3; do
  command -v "$cmd" >/dev/null 2>&1 || { echo "ERROR: missing command: $cmd" >&2; exit 69; }
done

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || true)"
[[ -n "$ROOT" ]] || { echo "ERROR: run inside the Git checkout" >&2; exit 69; }
cd "$ROOT"

CURRENT_BRANCH="$(git branch --show-current)"
[[ "$CURRENT_BRANCH" == "$TARGET_BRANCH" ]] || {
  echo "ERROR: current branch is '$CURRENT_BRANCH', expected '$TARGET_BRANCH'" >&2
  exit 65
}

ORIGIN="$(git remote get-url origin 2>/dev/null || true)"
case "$ORIGIN" in
  *github.com/provoware/PROVOWARE_VIDEO_AUTOMATION_2026*|*github.com:provoware/PROVOWARE_VIDEO_AUTOMATION_2026*) ;;
  *) echo "ERROR: unexpected origin: $ORIGIN" >&2; exit 65 ;;
esac

if [[ -n "$(git status --porcelain)" ]]; then
  echo "ERROR: working tree is not clean before import" >&2
  git status --short >&2
  exit 73
fi

ACTUAL_SHA256="$(sha256sum "$ZIP_PATH" | awk '{print $1}')"
[[ "$ACTUAL_SHA256" == "$EXPECTED_SHA256" ]] || {
  echo "ERROR: artifact SHA-256 mismatch" >&2
  echo "expected: $EXPECTED_SHA256" >&2
  echo "actual:   $ACTUAL_SHA256" >&2
  exit 65
}

unzip -tq "$ZIP_PATH" >/dev/null

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
unzip -q "$ZIP_PATH" -d "$TMP"
mapfile -t ROOTS < <(find "$TMP" -mindepth 1 -maxdepth 1 -type d -print)
[[ ${#ROOTS[@]} -eq 1 ]] || { echo "ERROR: ZIP must contain exactly one project root" >&2; exit 65; }
SOURCE_ROOT="${ROOTS[0]}"

rsync -a --delete \
  --exclude='.git/' \
  --exclude='ARTIFACT_BASELINE_PHASE4.json' \
  --exclude='scripts/import_phase4_artifact.sh' \
  "$SOURCE_ROOT/" "$ROOT/"

git diff --check

python3 -m py_compile \
  src/videobatch_fast/project_home_dashboard.py \
  tests/test_project_home_dashboard_wave25.py \
  tests/test_project_home_sources_wave25_phase2.py \
  tests/test_project_home_workflow_wave25_phase3.py \
  tests/test_project_home_render_wave25_phase4.py

git add -A

if git diff --cached --quiet; then
  echo "Phase-4 artifact already matches the branch; nothing to commit."
else
  git commit -m "chore: import canonical Welle25 UI phase4 tree"
fi

git push origin "$TARGET_BRANCH"

HEAD_SHA="$(git rev-parse HEAD)"
echo "PHASE4_BASELINE_PUSH_OK"
echo "branch=$TARGET_BRANCH"
echo "commit=$HEAD_SHA"
echo "artifact_sha256=$ACTUAL_SHA256"
echo "Next: open PR against main and require CI before Phase 5."
