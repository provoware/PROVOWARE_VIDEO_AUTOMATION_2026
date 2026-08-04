#!/usr/bin/env python3
from __future__ import annotations

import argparse
import gzip
import importlib.metadata
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from portable_runtime import runtime_smoke_test, sha256_file, write_manifest

RUNTIME_DISTRIBUTIONS = ("cryptography", "Pillow", "cffi", "pycparser")
EXCLUDE_PROJECT = {
    ".coverage", ".git", ".github", ".pytest_cache", ".mypy_cache", ".ruff_cache", "diagnostics",
    "dist", "toolchain_wheelhouse", "visual_inspection/captures", "tests/baselines",
}


def run(command: list[str], *, timeout: int = 600) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                          timeout=timeout, check=False, errors="replace")


def copy_tree(source: Path, destination: Path, *, ignore=None) -> None:
    shutil.copytree(source, destination, symlinks=False, dirs_exist_ok=True, ignore=ignore)


def project_ignore(directory: str, names: list[str]) -> set[str]:
    base = Path(directory)
    ignored: set[str] = set()
    for name in names:
        path = base / name
        try:
            relative = path.resolve().relative_to(ROOT.resolve()).as_posix()
        except (OSError, ValueError):
            relative = name
        if relative in EXCLUDE_PROJECT or name in {"__pycache__", ".DS_Store"} or name.endswith(".pyc"):
            ignored.add(name)
    return ignored


def copy_distribution(name: str, destination_site: Path) -> str:
    distribution = importlib.metadata.distribution(name)
    source_root = Path(distribution.locate_file(""))
    for item in distribution.files or ():
        source = Path(distribution.locate_file(item))
        try:
            relative = source.relative_to(source_root)
        except ValueError:
            continue
        target = destination_site / relative
        if source.is_file():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
    return distribution.version


def ldd_paths(binary: Path) -> dict[str, Path]:
    completed = run(["ldd", str(binary)], timeout=60)
    if completed.returncode:
        return {}
    found: dict[str, Path] = {}
    for raw in completed.stdout.splitlines():
        line = raw.strip()
        if not line or "not found" in line or line.startswith("linux-vdso"):
            continue
        match = re.match(r"([^\s]+)\s+=>\s+(/[^\s]+)", line)
        if match:
            found[match.group(1)] = Path(match.group(2)).resolve()
            continue
        match = re.match(r"(/[^\s]+)", line)
        if match:
            path = Path(match.group(1)).resolve()
            found[path.name] = path
    return found


def collect_dynamic_libraries(objects: Iterable[Path]) -> dict[str, Path]:
    pending = list(objects)
    scanned: set[Path] = set()
    libraries: dict[str, Path] = {}
    while pending:
        current = pending.pop()
        try:
            current = current.resolve()
        except OSError:
            continue
        if current in scanned or not current.is_file():
            continue
        scanned.add(current)
        for soname, path in ldd_paths(current).items():
            previous = libraries.get(soname)
            if previous is not None and previous != path:
                raise RuntimeError(f"Bibliothekskonflikt {soname}: {previous} / {path}")
            if previous is None:
                libraries[soname] = path
                pending.append(path)
    return libraries


def executable_objects(root: Path) -> list[Path]:
    return [p for p in root.rglob("*") if p.is_file() and (p.suffix == ".so" or ".so." in p.name)]


def make_media_wrapper(path: Path, binary_name: str) -> None:
    """Resolve media tools without ever injecting the bundled Python glibc.

    RC12 executed FFmpeg through a foreign bundled loader and LD_LIBRARY_PATH. That
    can mix glibc/stack-protector state and abort on another distribution. RC13
    launches a verified host/static binary in a scrubbed environment instead.
    """
    candidates = "$ROOT/usr/media/static/{0} /usr/bin/{0} /usr/local/bin/{0} /snap/bin/{0}".format(binary_name)
    override = "VIDEOBATCH_HOST_" + binary_name.upper()
    path.write_text(
        "#!/usr/bin/env bash\nset -Eeuo pipefail\n"
        f"OVERRIDE=\"${{{override}:-}}\"\n"
        "ROOT=\"$(cd -- \"$(dirname -- \"${BASH_SOURCE[0]}\")/../../..\" && pwd -P)\"\n"
        "SELF=\"$(readlink -f \"$0\")\"\n"
        "choose() {\n"
        "  local candidate\n"
        "  for candidate in \"$OVERRIDE\" " + candidates + "; do\n"
        "    [[ -n \"$candidate\" && -x \"$candidate\" ]] || continue\n"
        "    [[ \"$(readlink -f \"$candidate\")\" != \"$SELF\" ]] || continue\n"
        "    printf '%s\\n' \"$candidate\"; return 0\n"
        "  done\n"
        "  return 127\n"
        "}\n"
        "BINARY=\"$(choose)\" || { echo 'VideoBatch: kompatibles Medienwerkzeug fehlt.' >&2; exit 127; }\n"
        "exec env -u LD_LIBRARY_PATH -u PYTHONHOME -u PYTHONPATH -u TCL_LIBRARY -u TK_LIBRARY \"$BINARY\" \"$@\"\n",
        encoding="utf-8",
    )
    path.chmod(0o755)


def build_appdir(output: Path, python: Path, static_media_dir: Path | None = None) -> dict[str, object]:
    if output.exists():
        shutil.rmtree(output)
    (output / "usr/app").mkdir(parents=True)
    (output / "usr/runtime/bin").mkdir(parents=True)
    (output / "usr/runtime/lib").mkdir(parents=True)
    (output / "usr/media/bin").mkdir(parents=True)
    (output / "usr/share/applications").mkdir(parents=True)
    copy_tree(ROOT, output / "usr/app", ignore=project_ignore)

    python = python.resolve()
    shutil.copy2(python, output / "usr/runtime/bin/python3")
    (output / "usr/runtime/bin/python3").chmod(0o755)
    version = run([str(python), "-c", "import sys;print(f'{sys.version_info.major}.{sys.version_info.minor}')"], timeout=30).stdout.strip()
    stdlib = Path(run([str(python), "-c", "import sysconfig;print(sysconfig.get_path('stdlib'))"], timeout=30).stdout.strip())
    if not version or not stdlib.is_dir():
        raise RuntimeError("Python-Standardbibliothek konnte nicht bestimmt werden.")
    copy_tree(stdlib, output / f"usr/runtime/lib/python{version}", ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "test", "tests"))
    site = output / f"usr/runtime/lib/python{version}/site-packages"
    site.mkdir(parents=True, exist_ok=True)
    distribution_versions = {name: copy_distribution(name, site) for name in RUNTIME_DISTRIBUTIONS}

    for source in (Path("/usr/share/tcltk"), Path("/usr/lib/tcl8.6"), Path("/usr/lib/tk8.6")):
        if source.exists():
            copy_tree(source, output / "usr/runtime/share" / source.name)

    static_media = False
    if static_media_dir is not None:
        static_media_dir = static_media_dir.expanduser().resolve()
        ffmpeg_static = static_media_dir / "ffmpeg"
        ffprobe_static = static_media_dir / "ffprobe"
        if not ffmpeg_static.is_file() or not ffprobe_static.is_file():
            raise RuntimeError("Statischer Medienordner enthält ffmpeg/ffprobe nicht.")
        target_static = output / "usr/media/static"
        target_static.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ffmpeg_static, target_static / "ffmpeg")
        shutil.copy2(ffprobe_static, target_static / "ffprobe")
        (target_static / "ffmpeg").chmod(0o755); (target_static / "ffprobe").chmod(0o755)
        static_media = True
    make_media_wrapper(output / "usr/media/bin/ffmpeg", "ffmpeg")
    make_media_wrapper(output / "usr/media/bin/ffprobe", "ffprobe")

    # Only Python/Tk native objects share the embedded loader. Media programs are
    # intentionally excluded and use the host/static runtime in a scrubbed env.
    objects = [output / "usr/runtime/bin/python3"]
    objects.extend(executable_objects(output / f"usr/runtime/lib/python{version}"))
    libraries = collect_dynamic_libraries(objects)
    for soname, source in sorted(libraries.items()):
        target = output / "usr/runtime/lib" / soname
        shutil.copy2(source, target)
        target.chmod(0o755 if os.access(source, os.X_OK) else 0o644)
    loader = libraries.get("ld-linux-x86-64.so.2") or Path("/lib64/ld-linux-x86-64.so.2")
    if not loader.is_file():
        raise RuntimeError("Dynamischer Linux-Lader wurde nicht gefunden.")
    shutil.copy2(loader.resolve(), output / "usr/runtime/lib/ld-linux-x86-64.so.2")
    (output / "usr/runtime/lib/ld-linux-x86-64.so.2").chmod(0o755)

    app_run = output / "AppRun"
    app_run.write_text(
        "#!/usr/bin/env bash\nset -Eeuo pipefail\n"
        "APPDIR=\"$(cd -- \"$(dirname -- \"${BASH_SOURCE[0]}\")\" && pwd -P)\"\n"
        "export VIDEOBATCH_PORTABLE=1 VIDEOBATCH_PORTABLE_ROOT=\"$APPDIR\"\n"
        "export VIDEOBATCH_FFMPEG=\"$APPDIR/usr/media/bin/ffmpeg\" VIDEOBATCH_FFPROBE=\"$APPDIR/usr/media/bin/ffprobe\"\n"
        "export PATH=\"$APPDIR/usr/media/bin:$PATH\" PYTHONDONTWRITEBYTECODE=1\n"
        "LOADER=\"$APPDIR/usr/runtime/lib/ld-linux-x86-64.so.2\" PYTHON=\"$APPDIR/usr/runtime/bin/python3\"\n"
        "run_python() {\n"
        "  exec env -u LD_LIBRARY_PATH PYTHONHOME=\"$APPDIR/usr/runtime\" \\\n"
        f"    PYTHONPATH=\"$APPDIR/usr/app/src:$APPDIR/usr/runtime/lib/python{version}/site-packages\" \\\n"
        "    TCL_LIBRARY=\"$APPDIR/usr/runtime/share/tcltk/tcl8.6\" \\\n"
        "    TK_LIBRARY=\"$APPDIR/usr/runtime/share/tcltk/tk8.6\" \\\n"
        "    PYTHONDONTWRITEBYTECODE=1 \\\n"
        "    \"$LOADER\" --library-path \"$APPDIR/usr/runtime/lib\" \"$PYTHON\" \"$@\"\n"
        "}\n"
        "run_media() {\n"
        "  env -u LD_LIBRARY_PATH -u PYTHONHOME -u PYTHONPATH -u TCL_LIBRARY -u TK_LIBRARY \"$@\"\n"
        "}\n"
        "if [[ ${1:-} == --portable-verify ]]; then run_python \"$APPDIR/usr/app/scripts/portable_runtime.py\" --verify \"$APPDIR\"; fi\n"
        "if [[ ${1:-} == --portable-smoke-test ]]; then\n"
        "  run_media \"$APPDIR/usr/media/bin/ffmpeg\" -version >/dev/null 2>&1\n"
        "  run_media \"$APPDIR/usr/media/bin/ffprobe\" -version >/dev/null 2>&1\n"
        "  run_python -c \"import tkinter,cryptography,cffi,pycparser; from PIL import Image; print('PORTABLE_RUNTIME_OK')\"\n"
        "fi\n"
        "run_python \"$APPDIR/usr/app/scripts/bootstrap.py\" \"$@\"\n",
        encoding="utf-8",
    )
    app_run.chmod(0o755)
    desktop = (
        "[Desktop Entry]\nType=Application\nName=VideoBatch Fast Portable\n"
        "Comment=Offline-Videoautomatisierung mit distributionssicherer Medienruntime\n"
        "Exec=AppRun\nIcon=videobatch-fast\nTerminal=false\nCategories=AudioVideo;Video;\n"
    )
    (output / "videobatch-fast.desktop").write_text(desktop, encoding="utf-8")
    (output / "usr/share/applications/videobatch-fast.desktop").write_text(desktop, encoding="utf-8")
    svg = """<svg xmlns='http://www.w3.org/2000/svg' width='256' height='256' viewBox='0 0 256 256'><rect rx='48' width='256' height='256' fill='#171923'/><path d='M57 62h142v132H57z' fill='#00d4ff'/><path d='M105 94l62 34-62 34z' fill='#171923'/><path d='M42 48h24v160H42zm148 0h24v160h-24z' fill='#ffea00'/></svg>"""
    (output / "videobatch-fast.svg").write_text(svg, encoding="utf-8")
    (output / ".DirIcon").write_text(svg, encoding="utf-8")
    host_ffmpeg = shutil.which("ffmpeg") or ""
    metadata: dict[str, object] = {
        "release_target": json.loads((ROOT / "VERSION.json").read_text(encoding="utf-8"))["build"],
        "python_version": run([str(python), "--version"], timeout=30).stdout.strip(),
        "media_runtime_mode": "pinned-static-preferred-clean-environment" if static_media else "host-compatible-clean-environment",
        "build_host_ffmpeg": run([host_ffmpeg, "-version"], timeout=30).stdout.splitlines()[0] if host_ffmpeg else "not-found",
        "runtime_distributions": distribution_versions,
        "python_library_count": len(libraries),
        "static_media_embedded": static_media,
        "glibc_injection_into_media": False,
    }
    write_manifest(output, metadata=metadata)
    return metadata


def _portable_tar_filter(info: tarfile.TarInfo) -> tarfile.TarInfo:
    info.uid = info.gid = 0; info.uname = info.gname = ""; info.mtime = 1767225600
    return info


def make_tar(appdir: Path, output: Path) -> None:
    with output.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, compresslevel=1, mtime=0) as compressed:
            with tarfile.open(fileobj=compressed, mode="w") as archive:
                archive.add(appdir, arcname="AppDir", recursive=True, filter=_portable_tar_filter)


def make_self_extracting(payload_path: Path, output: Path) -> None:
    payload = payload_path.read_bytes(); payload_sha = sha256_file(payload_path)
    marker = "__VIDEOBATCH_PAYLOAD_BELOW__\n"
    stub = f'''#!/usr/bin/env bash
set -Eeuo pipefail
SELF="$(readlink -f "$0")"
CACHE="${{XDG_CACHE_HOME:-$HOME/.cache}}/VideoBatchFast/portable/{payload_sha[:24]}"
APPDIR="$CACHE/AppDir"
extract_and_verify() {{
  local stage="$CACHE.stage-$$" line actual
  rm -rf -- "$stage"; mkdir -p -- "$stage"
  line=$(awk '/^{marker.strip()}$/ {{print NR + 1; exit}}' "$SELF")
  actual=$(tail -n +"$line" "$SELF" | sha256sum | awk '{{print $1}}')
  [[ "$actual" == "{payload_sha}" ]] || {{ echo 'VideoBatch: Portable Nutzlast wurde verändert.' >&2; exit 70; }}
  tail -n +"$line" "$SELF" | tar -xz -C "$stage"
  "$stage/AppDir/AppRun" --portable-verify >/dev/null
  "$stage/AppDir/AppRun" --portable-smoke-test >/dev/null
  mkdir -p -- "$(dirname -- "$CACHE")"; rm -rf -- "$CACHE"; mv -- "$stage" "$CACHE"
}}
[[ -x "$APPDIR/AppRun" ]] || extract_and_verify
"$APPDIR/AppRun" --portable-verify >/dev/null || {{ rm -rf -- "$CACHE"; extract_and_verify; }}
export VIDEOBATCH_PORTABLE_LAUNCHER="$SELF"
exec "$APPDIR/AppRun" "$@"
{marker}'''.encode("utf-8")
    output.write_bytes(stub + payload); output.chmod(0o755)


def main() -> int:
    parser = argparse.ArgumentParser(description="Baut die portable, distributionssichere VideoBatch-Laufzeit.")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "dist")
    parser.add_argument("--python", type=Path, default=Path(sys.executable))
    parser.add_argument("--static-media-dir", type=Path)
    args = parser.parse_args()
    if not args.python.is_file(): raise SystemExit("Python fehlt.")
    args.output_dir = args.output_dir.expanduser().resolve()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    release = json.loads((ROOT / "VERSION.json").read_text(encoding="utf-8"))["build"]
    appdir = args.output_dir / f"VideoBatch_Fast_{release}.AppDir"
    metadata = build_appdir(appdir, args.python, args.static_media_dir)
    ok, detail = runtime_smoke_test(appdir)
    if not ok: raise SystemExit("Portable Laufzeitprüfung fehlgeschlagen:\n" + detail)
    tar_path = args.output_dir / f"VideoBatch_Fast_{release}-portable.tar.gz"
    run_path = args.output_dir / f"VideoBatch_Fast_{release}-portable.run"
    make_tar(appdir, tar_path); make_self_extracting(tar_path, run_path)
    report = {"schema_version": 2, "status": "passed", "appdir": str(appdir),
              "portable_tar": {"path": str(tar_path), "sha256": sha256_file(tar_path), "size": tar_path.stat().st_size},
              "portable_run": {"path": str(run_path), "sha256": sha256_file(run_path), "size": run_path.stat().st_size},
              "metadata": metadata}
    (args.output_dir / "PORTABLE_BUILD_REPORT.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2)); return 0

if __name__ == "__main__": raise SystemExit(main())
