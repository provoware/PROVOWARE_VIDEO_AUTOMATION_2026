#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
MANIFEST="${KUBUNTU_CI_PACKAGE_MANIFEST:-$ROOT/ci/kubuntu-apt-packages.txt}"
APT_ARCHIVE_CACHE="${APT_ARCHIVE_CACHE:-$HOME/.cache/videobatch/apt/default}"
PIP_CACHE_DIR="${PIP_CACHE_DIR:-$HOME/.cache/pip}"
REPORT_PATH="${CI_DEPENDENCY_REPORT:-$ROOT/CI_DEPENDENCY_REPORT.json}"
APT_CACHE_HIT="${APT_CACHE_HIT:-false}"
PIP_CACHE_HIT="${PIP_CACHE_HIT:-false}"

fatal() {
  printf 'CI dependency setup failed: %s\n' "$1" >&2
  exit "${2:-1}"
}

for command_name in sudo apt-get python3 timeout find awk; do
  command -v "$command_name" >/dev/null 2>&1 || \
    fatal "required command is missing: $command_name" 10
done
[[ -f "$MANIFEST" ]] || fatal "package manifest is missing: $MANIFEST" 11
[[ -f "$ROOT/requirements-toolchain.lock" ]] || \
  fatal "requirements-toolchain.lock is missing" 12

mapfile -t PACKAGES < <(
  sed -e 's/[[:space:]]*#.*$//' -e '/^[[:space:]]*$/d' "$MANIFEST"
)
((${#PACKAGES[@]} > 0)) || fatal "package manifest is empty" 13

for package_name in "${PACKAGES[@]}"; do
  [[ "$package_name" =~ ^[a-z0-9][a-z0-9+.-]*$ ]] || \
    fatal "unsafe package name in manifest: $package_name" 14
done

cache_count() {
  find "$1" -maxdepth 1 -type f -name '*.deb' -printf '.' 2>/dev/null | wc -c | tr -d ' '
}

cache_bytes() {
  find "$1" -maxdepth 1 -type f -name '*.deb' -printf '%s\n' 2>/dev/null |
    awk '{ total += $1 } END { print total + 0 }'
}

mkdir -p "$APT_ARCHIVE_CACHE" "$PIP_CACHE_DIR"
APT_DEB_COUNT_BEFORE="$(cache_count "$APT_ARCHIVE_CACHE")"
APT_BYTES_BEFORE="$(cache_bytes "$APT_ARCHIVE_CACHE")"

sudo install -d -m 0755 "$APT_ARCHIVE_CACHE"
sudo install -d -o _apt -g root -m 0700 "$APT_ARCHIVE_CACHE/partial"

APT_COMMON_OPTIONS=(
  -o Acquire::Retries=5
  -o Acquire::http::Timeout=30
  -o Acquire::https::Timeout=30
  -o Dpkg::Use-Pty=0
)
APT_CACHE_OPTIONS=(
  -o "Dir::Cache::archives=$APT_ARCHIVE_CACHE"
  -o APT::Keep-Downloaded-Packages=true
  -o Binary::apt-get::APT::Keep-Downloaded-Packages=true
)

sudo env DEBIAN_FRONTEND=noninteractive \
  timeout --signal=TERM --kill-after=30s 5m \
  apt-get "${APT_COMMON_OPTIONS[@]}" update

sudo env DEBIAN_FRONTEND=noninteractive \
  timeout --signal=TERM --kill-after=30s 12m \
  apt-get "${APT_COMMON_OPTIONS[@]}" "${APT_CACHE_OPTIONS[@]}" \
  install -y --no-install-recommends "${PACKAGES[@]}"

timeout --signal=TERM --kill-after=30s 8m \
  python3 -m pip install \
  --disable-pip-version-check \
  --cache-dir "$PIP_CACHE_DIR" \
  --user \
  --requirement "$ROOT/requirements-toolchain.lock"

for command_name in ffmpeg ffprobe Xvfb weston dbus-launch; do
  command -v "$command_name" >/dev/null 2>&1 || \
    fatal "installed command is unavailable: $command_name" 20
done
python3 - <<'PY'
import tkinter
import venv

assert tkinter.TkVersion > 0
assert venv.EnvBuilder is not None
PY
python3 -m venv --help >/dev/null
ffmpeg -hide_banner -version >/dev/null
ffprobe -hide_banner -version >/dev/null
weston --version >/dev/null

# The cache action runs as the runner user. Restore readable ownership after apt,
# while the next invocation recreates the apt partial directory for _apt.
sudo chown -R "$(id -u):$(id -g)" "$APT_ARCHIVE_CACHE"
chmod -R u+rwX,go+rX "$APT_ARCHIVE_CACHE"

APT_DEB_COUNT_AFTER="$(cache_count "$APT_ARCHIVE_CACHE")"
APT_BYTES_AFTER="$(cache_bytes "$APT_ARCHIVE_CACHE")"
export ROOT MANIFEST APT_ARCHIVE_CACHE PIP_CACHE_DIR REPORT_PATH
export APT_CACHE_HIT PIP_CACHE_HIT APT_DEB_COUNT_BEFORE APT_BYTES_BEFORE
export APT_DEB_COUNT_AFTER APT_BYTES_AFTER

python3 - <<'PY'
import json
import os
import platform
import subprocess
from pathlib import Path

manifest = Path(os.environ["MANIFEST"])
packages = [
    line.split("#", 1)[0].strip()
    for line in manifest.read_text(encoding="utf-8").splitlines()
]
packages = [item for item in packages if item]
versions = {}
for package in packages:
    result = subprocess.run(
        ["dpkg-query", "-W", "-f=${Version}", package],
        check=True,
        capture_output=True,
        text=True,
    )
    versions[package] = result.stdout.strip()

report = {
    "schema_version": 1,
    "platform": platform.platform(),
    "packages": versions,
    "apt_cache": {
        "path": os.environ["APT_ARCHIVE_CACHE"],
        "restored_exactly": os.environ["APT_CACHE_HIT"] == "true",
        "deb_count_before": int(os.environ["APT_DEB_COUNT_BEFORE"]),
        "bytes_before": int(os.environ["APT_BYTES_BEFORE"]),
        "deb_count_after": int(os.environ["APT_DEB_COUNT_AFTER"]),
        "bytes_after": int(os.environ["APT_BYTES_AFTER"]),
    },
    "pip_cache": {
        "path": os.environ["PIP_CACHE_DIR"],
        "restored_exactly": os.environ["PIP_CACHE_HIT"] == "true",
    },
}
Path(os.environ["REPORT_PATH"]).write_text(
    json.dumps(report, ensure_ascii=False, indent=2) + "\n",
    encoding="utf-8",
)
PY

if [[ -n "${GITHUB_STEP_SUMMARY:-}" ]]; then
  {
    printf '### Kubuntu CI dependencies\n\n'
    printf '| Metric | Value |\n|---|---:|\n'
    printf '| APT exact cache hit | `%s` |\n' "$APT_CACHE_HIT"
    printf '| Cached DEB files before | %s |\n' "$APT_DEB_COUNT_BEFORE"
    printf '| Cached DEB files after | %s |\n' "$APT_DEB_COUNT_AFTER"
    printf '| Cached bytes after | %s |\n' "$APT_BYTES_AFTER"
    printf '| Installed package profile | %s packages |\n' "${#PACKAGES[@]}"
  } >> "$GITHUB_STEP_SUMMARY"
fi
