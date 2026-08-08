#!/usr/bin/env bash
set -Eeuo pipefail
ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
OUTPUT_DIR="${1:-$ROOT_DIR/dist}"
VERSION="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8"))["version"])' "$ROOT_DIR/VERSION.json")"
CHANNEL="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8"))["channel"])' "$ROOT_DIR/VERSION.json")"
if [[ "$CHANNEL" != "stable" ]]; then
  printf 'STABLE BLOCKIERT: Ursache: Der Kanal ist %s statt stable. Auswirkung: Das Stable-Paket wird nicht erzeugt. Automatische Schutzmaßnahme: Die Paketierung stoppt vor dem Schreiben. Lösung: Den Kandidaten vollständig prüfen und danach in einer getrennten Arbeitskopie auf stable setzen. Alternative: Den Stand als Release Candidate paketieren.\n' "$CHANNEL" >&2
  exit 12
fi
EVIDENCE_DIR="${VIDEOBATCH_ACCEPTANCE_EVIDENCE:-}"
if [[ -z "$EVIDENCE_DIR" ]]; then
  printf '%s\n' 'STABLE BLOCKIERT: Ursache: Der externe Abnahmeordner wurde nicht angegeben. Auswirkung: Das Stable-Paket wird nicht erzeugt. Automatische Schutzmaßnahme: Die Freigabe stoppt, ohne Nachweise zu ändern oder zu erzeugen. Lösung: Über finalize mit --acceptance-evidence einen vollständigen Nachweisordner angeben. Alternative: Den Kandidaten als Release Candidate belassen.' >&2
  exit 14
fi
CANDIDATE="${VIDEOBATCH_ACCEPTANCE_CANDIDATE:-$VERSION}"
MANIFEST_SHA256="${VIDEOBATCH_ACCEPTANCE_MANIFEST_SHA256:-$(sha256sum "$ROOT_DIR/RELEASE_MANIFEST.json" | cut -d' ' -f1)}"
SOURCE_SHA256="${VIDEOBATCH_ACCEPTANCE_SOURCE_SHA256:-$(python3 "$ROOT_DIR/scripts/release_identity.py" --json | python3 -c 'import json,sys; print(json.load(sys.stdin)["source_sha256"])')}"
python3 "$ROOT_DIR/scripts/validate_stable_acceptance.py" --evidence-dir "$EVIDENCE_DIR" --candidate "$CANDIDATE" --manifest-sha256 "$MANIFEST_SHA256" --source-sha256 "$SOURCE_SHA256"
TMP_DIR="$(mktemp -d -t videobatch-stable-XXXXXX)"
trap 'rm -rf "$TMP_DIR"' EXIT
QUALITY_EVIDENCE_DIR="$TMP_DIR/quality-evidence"
mkdir -p "$QUALITY_EVIDENCE_DIR/diagnostics"
export VIDEOBATCH_DIAGNOSTICS_DIR="$QUALITY_EVIDENCE_DIR/diagnostics"
python3 "$ROOT_DIR/scripts/toolchain.py" prepare --scope quality --auto-repair --quiet
python3 "$ROOT_DIR/scripts/toolchain.py" gate --scope quality --run-external --quiet
ENV_PYTHON="$(python3 "$ROOT_DIR/scripts/toolchain.py" path --scope quality --quiet)"
cp "$ROOT_DIR/toolchain_wheelhouse/TOOLCHAIN_WHEELHOUSE_MANIFEST.json" "$QUALITY_EVIDENCE_DIR/wheelhouse-manifest.json"
cp "$ROOT_DIR/toolchain_wheelhouse/requirements-toolchain-resolved.lock" "$QUALITY_EVIDENCE_DIR/requirements-toolchain-resolved.lock"
"$ENV_PYTHON" - <<'PYVERS' > "$QUALITY_EVIDENCE_DIR/installed-versions.json"
import importlib.metadata as metadata, json, platform, sys
names = ["ruff", "mypy", "bandit", "pip-audit"]
print(json.dumps({"python": sys.version, "platform": platform.platform(), "packages": {name: metadata.version(name) for name in names}}, ensure_ascii=False, indent=2, sort_keys=True))
PYVERS
python3 "$ROOT_DIR/scripts/quality_evidence.py" build --evidence-dir "$QUALITY_EVIDENCE_DIR"
python3 "$ROOT_DIR/scripts/quality_evidence.py" verify --evidence-dir "$QUALITY_EVIDENCE_DIR"
export VIDEOBATCH_QUALITY_ALREADY_VERIFIED=1
"$ROOT_DIR/test.sh"
"$ENV_PYTHON" "$ROOT_DIR/scripts/check_visual_approval.py" --require
"$ENV_PYTHON" "$ROOT_DIR/scripts/build_release_manifest.py"
"$ENV_PYTHON" "$ROOT_DIR/scripts/validate_release_manifest.py"
mkdir -p "$OUTPUT_DIR"
A="$TMP_DIR/VideoBatch_Fast_${VERSION}-a.zip"
B="$TMP_DIR/VideoBatch_Fast_${VERSION}-b.zip"
"$ENV_PYTHON" "$ROOT_DIR/scripts/package_release.py" --output "$A"
"$ENV_PYTHON" "$ROOT_DIR/scripts/package_release.py" --output "$B"
cmp --silent "$A" "$B" || { printf '%s\n' 'STABLE BLOCKIERT: Ursache: Die Doppelpaketierung ist nicht byteidentisch. Auswirkung: Es gibt kein verlässlich reproduzierbares Stable-Paket. Automatische Schutzmaßnahme: Beide temporären Pakete werden verworfen. Lösung: Die Quelle reproduzierbar machen und alle Gates erneut ausführen. Alternative: Den Kandidaten als Release Candidate belassen.' >&2; exit 13; }
FINAL="$OUTPUT_DIR/VideoBatch_Fast_${VERSION}.zip"
cp "$A" "$FINAL"
sha256sum "$FINAL" > "$FINAL.sha256"
QUALITY_BUNDLE="$OUTPUT_DIR/VideoBatch_Fast_${VERSION}_QUALITY_EVIDENCE.zip"
python3 "$ROOT_DIR/scripts/quality_evidence.py" bundle --evidence-dir "$QUALITY_EVIDENCE_DIR" --output "$QUALITY_BUNDLE"
sha256sum "$QUALITY_BUNDLE" > "$QUALITY_BUNDLE.sha256"
printf 'STABLE ERZEUGT: %s\n' "$FINAL"
printf 'QUALITY-EVIDENCE ERZEUGT: %s\n' "$QUALITY_BUNDLE"
cat "$FINAL.sha256"
cat "$QUALITY_BUNDLE.sha256"
