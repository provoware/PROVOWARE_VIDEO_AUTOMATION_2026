#!/usr/bin/env bash
set -Eeuo pipefail

REPO="provoware/PROVOWARE_VIDEO_AUTOMATION_2026"
SOURCE_TAG="videobatch-fast-2.8.3-rc24-source"
FINAL_TAG="videobatch-fast-2.8.3-rc24"
WORKFLOW="install-videobatch-rc24.yml"
EXPECTED_SHA256="c54c19141f4d08fbb19f6f38e40ce06c589a86725b988864ad8e22f28ad7501a"
EXPECTED_SIZE="4013380"
ASSET_NAME="VideoBatch_Fast_2.8.3-rc24.zip"
ISSUE_NUMBER="11"

die() {
  printf '\n🔴 FEHLER: %s\n' "$*" >&2
  exit 1
}

green() { printf '🟢 %s\n' "$*"; }
yellow() { printf '🟡 %s\n' "$*"; }

ZIP_PATH="${1:-}"
if [[ -z "$ZIP_PATH" ]]; then
  for candidate in \
    "./VideoBatch_Fast_2.8.3-rc24.zip" \
    "./VideoBatch_Fast_2.8.3-rc24(3)(1).zip"; do
    if [[ -f "$candidate" ]]; then
      ZIP_PATH="$candidate"
      break
    fi
  done
fi

[[ -n "$ZIP_PATH" ]] || die "ZIP-Pfad fehlt. Aufruf: bash $0 /pfad/VideoBatch_Fast_2.8.3-rc24.zip"
[[ -f "$ZIP_PATH" ]] || die "ZIP nicht gefunden: $ZIP_PATH"

command -v sha256sum >/dev/null || die "sha256sum fehlt."
command -v stat >/dev/null || die "stat fehlt."
command -v unzip >/dev/null || die "unzip fehlt."

ACTUAL_SIZE="$(stat -c '%s' "$ZIP_PATH")"
[[ "$ACTUAL_SIZE" == "$EXPECTED_SIZE" ]] || die "Falsche Dateigröße: $ACTUAL_SIZE statt $EXPECTED_SIZE Bytes."

ACTUAL_SHA256="$(sha256sum "$ZIP_PATH" | awk '{print $1}')"
[[ "$ACTUAL_SHA256" == "$EXPECTED_SHA256" ]] || die "SHA-256 stimmt nicht: $ACTUAL_SHA256"

unzip -t "$ZIP_PATH" >/dev/null || die "ZIP-Struktur ist beschädigt."
green "Lokale ZIP vollständig verifiziert."

if ! command -v gh >/dev/null; then
  yellow "GitHub-CLI fehlt. Installationsversuch über apt."
  command -v sudo >/dev/null || die "sudo fehlt. Installiere GitHub CLI manuell: https://cli.github.com/"
  sudo apt-get update
  sudo apt-get install -y gh
fi

gh auth status -h github.com >/dev/null 2>&1 || {
  yellow "GitHub-Anmeldung erforderlich. Der Browser-Login wird geöffnet."
  gh auth login -h github.com -p https -w
}
gh auth status -h github.com >/dev/null 2>&1 || die "GitHub-Anmeldung nicht bestätigt."

gh repo view "$REPO" >/dev/null || die "Repository nicht erreichbar: $REPO"
green "GitHub-Zugriff bestätigt."

TMP_ASSET="$(mktemp --suffix=.zip)"
trap 'rm -f "$TMP_ASSET"' EXIT
cp -- "$ZIP_PATH" "$TMP_ASSET"

if gh release view "$SOURCE_TAG" -R "$REPO" >/dev/null 2>&1; then
  yellow "Quellrelease existiert bereits; Asset wird kontrolliert ersetzt."
  gh release upload "$SOURCE_TAG" "$TMP_ASSET#$ASSET_NAME" -R "$REPO" --clobber
else
  gh release create "$SOURCE_TAG" "$TMP_ASSET#$ASSET_NAME" \
    -R "$REPO" \
    --title "VideoBatch Fast 2.8.3-rc24 – geprüfte Quelle" \
    --notes "Dauerhaftes, vorab validiertes Quellarchiv. SHA-256: $EXPECTED_SHA256"
fi

REMOTE_SIZE="$(
  gh release view "$SOURCE_TAG" -R "$REPO" \
    --json assets \
    --jq ".assets[] | select(.name == \"$ASSET_NAME\") | .size"
)"
[[ "$REMOTE_SIZE" == "$EXPECTED_SIZE" ]] || die "Release-Asset fehlt oder hat falsche Größe: ${REMOTE_SIZE:-nicht gefunden}"
green "Dauerhaftes GitHub-Release-Asset vorhanden."

BEFORE_RUN="$(
  gh run list -R "$REPO" --workflow "$WORKFLOW" --limit 1 \
    --json databaseId --jq '.[0].databaseId // 0' 2>/dev/null || printf '0'
)"

gh workflow run "$WORKFLOW" -R "$REPO" --ref main -f report_issue="$ISSUE_NUMBER"
green "Installationsworkflow auf main gestartet."

RUN_ID=""
for _ in $(seq 1 30); do
  RUN_ID="$(
    gh run list -R "$REPO" --workflow "$WORKFLOW" --limit 5 \
      --json databaseId,event,status \
      --jq "[.[] | select(.event == \"workflow_dispatch\" and .databaseId != $BEFORE_RUN)][0].databaseId // empty"
  )"
  [[ -n "$RUN_ID" ]] && break
  sleep 2
done
[[ -n "$RUN_ID" ]] || die "Der neue Workflow-Lauf wurde nicht gefunden."

green "Workflow-Lauf erkannt: $RUN_ID"
if ! gh run watch "$RUN_ID" -R "$REPO" --exit-status; then
  gh run view "$RUN_ID" -R "$REPO" --log-failed || true
  die "GitHub Actions meldet einen Fehler. Fehlprotokoll wurde ausgegeben."
fi

VERSION_JSON="$(
  gh api "repos/$REPO/contents/VERSION.json?ref=main" --jq .content | tr -d '\n' | base64 -d
)"
python3 - "$VERSION_JSON" <<'PY'
import json
import sys
data = json.loads(sys.argv[1])
assert data.get("version") == "2.8.3-rc24", data
print("🟢 VERSION.json bestätigt 2.8.3-rc24.")
PY

VALIDATION_JSON="$(
  gh api "repos/$REPO/contents/BOOTSTRAP_VALIDATION.json?ref=main" --jq .content | tr -d '\n' | base64 -d
)"
python3 - "$VALIDATION_JSON" <<'PY'
import json
import sys
data = json.loads(sys.argv[1])
assert data.get("version") == "2.8.3-rc24", data
assert data.get("source_archive_sha256") == "c54c19141f4d08fbb19f6f38e40ce06c589a86725b988864ad8e22f28ad7501a", data
assert data.get("github_actions_validation") == "passed", data
print("🟢 BOOTSTRAP_VALIDATION.json vollständig bestätigt.")
PY

gh api "repos/$REPO/git/ref/tags/$FINAL_TAG" >/dev/null \
  || die "Finaler Release-Tag fehlt: $FINAL_TAG"
green "Finaler unveränderlicher Tag bestätigt: $FINAL_TAG"

if gh api "repos/$REPO/contents/.github/workflows/$WORKFLOW?ref=main" >/dev/null 2>&1; then
  die "Bootstrap-Workflow ist nach Installation noch vorhanden."
else
  green "Temporärer Bootstrap-Workflow wurde entfernt."
fi

FINAL_ASSET_SIZE="$(
  gh release view "$FINAL_TAG" -R "$REPO" \
    --json assets \
    --jq ".assets[] | select(.name == \"$ASSET_NAME\") | .size" 2>/dev/null || true
)"
[[ "$FINAL_ASSET_SIZE" == "$EXPECTED_SIZE" ]] \
  || die "Finales Release-Asset fehlt oder hat falsche Größe."

gh issue close "$ISSUE_NUMBER" -R "$REPO" \
  --reason completed \
  --comment "RC24 erfolgreich installiert und validiert. Quelle und finales Release-Asset sind vorhanden; VERSION.json, BOOTSTRAP_VALIDATION.json, finaler Tag und Bootstrap-Entfernung wurden geprüft." \
  >/dev/null
green "Issue #$ISSUE_NUMBER geschlossen."

printf '\n✅ RC24-FINALISIERUNG VOLLSTÄNDIG ERFOLGREICH\n'
printf 'Repository: %s\n' "$REPO"
printf 'Workflow-Lauf: %s\n' "$RUN_ID"
printf 'Quell-Tag: %s\n' "$SOURCE_TAG"
printf 'Finaler Tag: %s\n' "$FINAL_TAG"
