#!/usr/bin/env bash
set -Eeuo pipefail

: "${RUNNER_TEMP:?RUNNER_TEMP is required}"
: "${GITHUB_STEP_SUMMARY:?GITHUB_STEP_SUMMARY is required}"
: "${MATRIX_OS:?MATRIX_OS is required}"
: "${MATRIX_SESSION:?MATRIX_SESSION is required}"
: "${CACHE_WEEK:?CACHE_WEEK is required}"

APT_ARCHIVES="$RUNNER_TEMP/apt-archives"
PIP_CACHE_DIR="$RUNNER_TEMP/pip-cache"
LOG_DIR="matrix-logs"
PACKAGE_FILE=".github/ci/kubuntu-packages.txt"
export PIP_CACHE_DIR

mkdir -p "$APT_ARCHIVES/partial" "$PIP_CACHE_DIR" "$LOG_DIR"
mapfile -t packages < <(
  sed '/^[[:space:]]*#/d; /^[[:space:]]*$/d' "$PACKAGE_FILE"
)
((${#packages[@]} > 0))

apt_before="$(du -sb "$APT_ARCHIVES" | awk '{print $1}')"
pip_before="$(du -sb "$PIP_CACHE_DIR" | awk '{print $1}')"
apt_started="$(date +%s)"

set +e
sudo env DEBIAN_FRONTEND=noninteractive \
  timeout --signal=TERM --kill-after=30s 5m \
  apt-get -o Acquire::Retries=5 update \
  2>&1 | tee "$LOG_DIR/apt-update.log"
update_result="${PIPESTATUS[0]}"
set -e

if ((update_result == 0)); then
  set +e
  timeout --signal=TERM --kill-after=30s 3m \
    apt-get \
      -o Dir::Cache::archives="$APT_ARCHIVES" \
      --simulate install -y --no-install-recommends "${packages[@]}" \
    2>&1 | tee "$LOG_DIR/apt-simulate.log"
  simulate_result="${PIPESTATUS[0]}"
  set -e

  if ((simulate_result == 0)); then
    set +e
    sudo env DEBIAN_FRONTEND=noninteractive \
      timeout --signal=TERM --kill-after=30s 15m \
      apt-get \
        -o Acquire::Retries=5 \
        -o Dpkg::Use-Pty=0 \
        -o Dir::Cache::archives="$APT_ARCHIVES" \
        install -y --no-install-recommends "${packages[@]}" \
      2>&1 | tee "$LOG_DIR/apt-install.log"
    apt_result="${PIPESTATUS[0]}"
    set -e
  else
    apt_result="$simulate_result"
    : > "$LOG_DIR/apt-install.log"
  fi
else
  simulate_result=125
  apt_result="$update_result"
  : > "$LOG_DIR/apt-simulate.log"
  : > "$LOG_DIR/apt-install.log"
fi
apt_finished="$(date +%s)"

pip_started="$(date +%s)"
if ((apt_result == 0)); then
  set +e
  timeout --signal=TERM --kill-after=30s 8m \
    python3 -m pip install \
      --user \
      --requirement requirements-toolchain.lock \
    2>&1 | tee "$LOG_DIR/pip-install.log"
  pip_result="${PIPESTATUS[0]}"
  set -e
else
  pip_result=125
  : > "$LOG_DIR/pip-install.log"
fi
pip_finished="$(date +%s)"

verify_result=0
if ((apt_result == 0 && pip_result == 0)); then
  set +e
  {
    command -v python3
    command -v ffmpeg
    command -v ffprobe
    command -v Xvfb
    command -v weston
    dpkg-query -W plasma-workspace
  } 2>&1 | tee "$LOG_DIR/dependency-verification.log"
  verify_result="${PIPESTATUS[0]}"
  set -e
else
  verify_result=125
  : > "$LOG_DIR/dependency-verification.log"
fi

sudo chown -R "$(id -u):$(id -g)" "$APT_ARCHIVES" "$PIP_CACHE_DIR"
apt_after="$(du -sb "$APT_ARCHIVES" | awk '{print $1}')"
pip_after="$(du -sb "$PIP_CACHE_DIR" | awk '{print $1}')"

export apt_before apt_after pip_before pip_after
export apt_started apt_finished pip_started pip_finished
export apt_result pip_result verify_result update_result simulate_result
export REQUESTED_PACKAGE_COUNT="${#packages[@]}"

python3 - <<'PY'
import json
import os
import re
from pathlib import Path


def read_text(path: str) -> str:
    try:
        return Path(path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def human_size(value: int) -> str:
    size = float(value)
    for unit in ("B", "KiB", "MiB", "GiB"):
        if size < 1024 or unit == "GiB":
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{value} B"


def cache_state(exact: bool, restored: bool) -> str:
    if exact:
        return "aktueller Wochenvorrat"
    if restored:
        return "älterer Vorrat übernommen"
    return "neuer Vorrat aufgebaut"


simulate = read_text("matrix-logs/apt-simulate.log")
install = read_text("matrix-logs/apt-install.log")
planned_match = re.search(r"(\d+)\s+newly installed", simulate)
download_match = re.search(r"Need to get ([^\n]+?) of archives\.", install)

apt_before = int(os.environ["apt_before"])
apt_after = int(os.environ["apt_after"])
pip_before = int(os.environ["pip_before"])
pip_after = int(os.environ["pip_after"])
apt_exact = os.environ.get("APT_CACHE_EXACT_HIT") == "true"
pip_exact = os.environ.get("PIP_CACHE_EXACT_HIT") == "true"
apt_restored = apt_before > 1024 * 1024
pip_restored = pip_before > 1024 * 1024
update_ok = int(os.environ["update_result"]) == 0
simulate_ok = int(os.environ["simulate_result"]) == 0
apt_ok = int(os.environ["apt_result"]) == 0
pip_ok = int(os.environ["pip_result"]) == 0
verify_ok = int(os.environ["verify_result"]) == 0
overall_ok = update_ok and simulate_ok and apt_ok and pip_ok and verify_ok
mode = os.environ.get("CI_PACKAGE_MODE", "matrix")

metrics = {
    "schema_version": 3,
    "mode": mode,
    "os": os.environ["MATRIX_OS"],
    "session": os.environ["MATRIX_SESSION"],
    "cache_week": os.environ["CACHE_WEEK"],
    "apt_cache_exact_hit": apt_exact,
    "apt_cache_restored": apt_restored,
    "pip_cache_exact_hit": pip_exact,
    "pip_cache_restored": pip_restored,
    "requested_packages": int(os.environ["REQUESTED_PACKAGE_COUNT"]),
    "planned_new_packages": (
        int(planned_match.group(1)) if planned_match else None
    ),
    "download_summary": (
        download_match.group(1)
        if download_match
        else "keine Downloadangabe gefunden"
    ),
    "apt_seconds": (
        int(os.environ["apt_finished"]) - int(os.environ["apt_started"])
    ),
    "pip_seconds": (
        int(os.environ["pip_finished"]) - int(os.environ["pip_started"])
    ),
    "apt_cache_before_bytes": apt_before,
    "apt_cache_after_bytes": apt_after,
    "pip_cache_before_bytes": pip_before,
    "pip_cache_after_bytes": pip_after,
    "apt_update_success": update_ok,
    "apt_simulation_success": simulate_ok,
    "apt_success": apt_ok,
    "pip_success": pip_ok,
    "verification_success": verify_ok,
    "verified_tools": [
        "python3",
        "ffmpeg",
        "ffprobe",
        "Xvfb",
        "weston",
        "plasma-workspace",
    ],
}
Path("CI_PACKAGE_METRICS.json").write_text(
    json.dumps(metrics, ensure_ascii=False, indent=2) + "\n",
    encoding="utf-8",
)

light = "🟢" if overall_ok else "🔴"
heading = (
    "Kubuntu-Paketvorrat automatisch vorbereitet"
    if mode == "warmup"
    else "Paketvorbereitung einfach erklärt"
)
state = cache_state(apt_exact, apt_restored)
next_step = (
    "Keine Aktion nötig."
    if overall_ok
    else "Die erste rote Fehlermeldung und die zugehörige Logdatei öffnen."
)
lines = [
    f"# {light} {heading}",
    "",
    f"**System:** {metrics['os']} / {metrics['session']}",
    f"**Ergebnis:** {'erfolgreich' if overall_ok else 'fehlgeschlagen'}",
    f"**Cache-Zustand:** {state}",
    "",
    "## Das Wichtigste",
    "",
    f"- Cache-Woche: **{metrics['cache_week']}**",
    f"- Direkte Paketvorgaben: **{metrics['requested_packages']}**",
    (
        "- Pakete einschließlich Abhängigkeiten: "
        f"**{metrics['planned_new_packages'] if metrics['planned_new_packages'] is not None else 'nicht ermittelt'}**"
    ),
    f"- Noch aus dem Netz benötigte Paketdaten: **{metrics['download_summary']}**",
    f"- APT-Dauer: **{metrics['apt_seconds']} Sekunden**",
    f"- Pip-Dauer: **{metrics['pip_seconds']} Sekunden**",
    f"- APT-Vorrat vorher: **{human_size(apt_before)}**",
    f"- APT-Vorrat nachher: **{human_size(apt_after)}**",
    f"- Python-Vorrat nachher: **{human_size(pip_after)}**",
    (
        "- Paketvorberechnung: "
        f"**{'bestanden' if simulate_ok else 'fehlgeschlagen'}**"
    ),
    f"- Werkzeugprüfung: **{'bestanden' if verify_ok else 'fehlgeschlagen'}**",
    "",
    "## Was bedeutet das?",
    "",
    (
        "Der Paketvorrat enthält bereits heruntergeladene KDE-, Anzeige-, "
        "Python- und FFmpeg-Pakete. GitHub aktualisiert weiterhin die kleine "
        "Paketübersicht, muss die großen Programmpakete bei einem Treffer aber "
        "nicht erneut vom Ubuntu-Spiegel laden."
    ),
    "",
    f"**Nächster Schritt:** {next_step}",
]
with Path(os.environ["GITHUB_STEP_SUMMARY"]).open(
    "a", encoding="utf-8"
) as output:
    output.write("\n".join(lines) + "\n")

notice = (
    f"{metrics['os']} / {metrics['session']}: "
    f"{state}, APT {metrics['apt_seconds']} s, "
    f"Netzdownload {metrics['download_summary']}."
)
print(f"::notice title=CI-Paketstatus::{notice}")
PY

if ((update_result != 0)); then
  echo "::error title=Paketübersicht nicht erreichbar::Die Ubuntu-Paketübersicht konnte trotz Wiederholungen nicht aktualisiert werden. Details: matrix-logs/apt-update.log"
  exit "$update_result"
fi
if ((simulate_result != 0)); then
  echo "::error title=Paketvorberechnung abgebrochen::Die reine APT-Vorberechnung wurde nach spätestens drei Minuten beendet oder ist fehlgeschlagen. Details: matrix-logs/apt-simulate.log"
  exit "$simulate_result"
fi
if ((apt_result != 0)); then
  echo "::error title=APT-Installation fehlgeschlagen::Die Ubuntu-Pakete konnten nicht vollständig installiert werden. Details: matrix-logs/apt-install.log"
  exit "$apt_result"
fi
if ((pip_result != 0)); then
  echo "::error title=Python-Installation fehlgeschlagen::Die Python-Werkzeuge konnten nicht vollständig installiert werden. Details: matrix-logs/pip-install.log"
  exit "$pip_result"
fi
if ((verify_result != 0)); then
  echo "::error title=Werkzeugprüfung fehlgeschlagen::Mindestens ein benötigtes Programm fehlt. Details: matrix-logs/dependency-verification.log"
  exit "$verify_result"
fi
