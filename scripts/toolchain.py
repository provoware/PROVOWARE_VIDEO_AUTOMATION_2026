#!/usr/bin/env python3
from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import venv
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterable, Iterator

from toolchain_common import (
    RESOLVED_LOCK_NAME,
    RUNTIME_RESOLVED_LOCK_NAME,
    ROOT,
    atomic_write_text,
    build_manifest,
    expected_packages,
    load_contract,
    publish_directory,
    rebuild_wheelhouse_metadata,
    runtime_identity,
    safe_remove_tree,
    toolchain_cache_key,
    verify_wheelhouse,
    write_manifest,
    write_resolved_lock,
)

EXIT_CONTRACT = 40
EXIT_WHEELHOUSE = 41
EXIT_INSTALL = 42
EXIT_GATE = 43
QUIET = False


def progress(step: int, total: int, message: str) -> None:
    if not QUIET:
        print(f"[{step}/{total}] {message}", flush=True)


def info(message: str) -> None:
    if not QUIET:
        print(message, flush=True)


def run(
    command: list[str],
    *,
    timeout: int = 1800,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            command,
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
            check=False,
            env=env,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"Zeitüberschreitung: {' '.join(command)}") from exc
    except OSError as exc:
        raise RuntimeError(f"Prozessstart fehlgeschlagen: {exc}") from exc


def required_file(relative: str) -> Path:
    path = ROOT / relative
    if not path.is_file() or path.is_symlink():
        raise RuntimeError(f"Erforderliche Projektdatei fehlt oder ist ein Link: {relative}")
    return path


def effective_scope(scope: str) -> str:
    return "runtime" if scope == "runtime" else "quality"


def package_scope(scope: str) -> str:
    return "runtime" if scope == "runtime" else "all"


def data_root() -> Path:
    return Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share")) / "VideoBatchFast"


def state_root() -> Path:
    return Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local/state")) / "VideoBatchFast"


def environment_key(contract: dict[str, Any], scope: str) -> str:
    selected = expected_packages(contract, package_scope(scope))
    payload = {
        "schema": 2,
        "scope": effective_scope(scope),
        "packages": selected,
        "runtime": runtime_identity(),
    }
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()[:20]
    python_tag = runtime_identity()["python"].replace(".", "")
    return f"{effective_scope(scope)}-py{python_tag}-{digest}"


def environment_path(contract: dict[str, Any], scope: str = "all") -> Path:
    return data_root() / "environments" / environment_key(contract, scope)


def venv_python(contract: dict[str, Any], scope: str = "all") -> Path:
    specific = "VIDEOBATCH_RUNTIME_PYTHON" if effective_scope(scope) == "runtime" else "VIDEOBATCH_QUALITY_PYTHON"
    override = os.environ.get(specific, "").strip() or os.environ.get("VIDEOBATCH_TOOLCHAIN_PYTHON", "").strip()
    if override:
        return Path(override).expanduser().resolve(strict=False)
    return environment_path(contract, scope) / "bin" / "python"


def wheelhouse_path(contract: dict[str, Any]) -> Path:
    return ROOT / contract["paths"]["wheelhouse"]


@contextmanager
def toolchain_lock() -> Iterator[None]:
    lock_dir = state_root() / "locks"
    lock_dir.mkdir(parents=True, exist_ok=True)
    path = lock_dir / "toolchain.lock"
    with path.open("a+", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def verify(contract: dict[str, Any], scope: str = "all") -> dict[str, Any]:
    wheelhouse = wheelhouse_path(contract)
    errors = verify_wheelhouse(wheelhouse, contract, scope=package_scope(scope))
    if errors:
        raise RuntimeError("Einheits-Wheelhouse ungültig: " + " | ".join(errors))
    return json.loads((wheelhouse / "TOOLCHAIN_WHEELHOUSE_MANIFEST.json").read_text(encoding="utf-8"))


def installed_versions(python: Path, contract: dict[str, Any], scope: str) -> dict[str, str]:
    if not python.is_file() or not os.access(python, os.X_OK):
        raise RuntimeError("Toolchain-Umgebung fehlt.")
    expected = expected_packages(contract, package_scope(scope))
    code = (
        "import importlib.metadata as m,json;"
        f"names={list(expected)!r};"
        "result={};missing=[];"
        "\nfor n in names:\n"
        " try: result[n]=m.version(n)\n"
        " except m.PackageNotFoundError: missing.append(n)\n"
        "print(json.dumps({'versions':result,'missing':missing},sort_keys=True))"
    )
    completed = run([str(python), "-c", code], timeout=60)
    if completed.returncode:
        raise RuntimeError("Installierte Paketversionen konnten nicht gelesen werden:\n" + completed.stdout[-4000:])
    try:
        payload = json.loads(completed.stdout.strip().splitlines()[-1])
    except (json.JSONDecodeError, IndexError) as exc:
        raise RuntimeError("Paketversionsprüfung lieferte keine gültigen Daten.") from exc
    missing = payload.get("missing", [])
    actual = payload.get("versions", {})
    if missing:
        raise RuntimeError("Pflichtpakete fehlen: " + ", ".join(sorted(missing)))
    if actual != expected:
        raise RuntimeError(f"Installierte Versionen weichen ab: {actual}; erwartet {expected}")
    return actual


def runtime_import_gate(python: Path) -> None:
    code = "import tkinter,cryptography,cffi,pycparser; from PIL import Image; print('RUNTIME_IMPORTS_OK')"
    completed = run([str(python), "-c", code], timeout=60)
    if completed.returncode or "RUNTIME_IMPORTS_OK" not in completed.stdout:
        raise RuntimeError("Runtime-Importprüfung fehlgeschlagen:\n" + completed.stdout[-4000:])


def quality_executable_gate(python: Path) -> None:
    missing = [name for name in ("ruff", "mypy", "bandit", "pip-audit", "pytest", "coverage") if not (python.parent / name).is_file()]
    if missing:
        raise RuntimeError("Qualitätskommandos fehlen: " + ", ".join(missing))


def marker_path(contract: dict[str, Any], scope: str) -> Path:
    return environment_path(contract, scope) / ".videobatch-ready.json"


def write_ready_marker(contract: dict[str, Any], scope: str, python: Path) -> None:
    payload = {
        "schema_version": 1,
        "environment_key": environment_key(contract, scope),
        "scope": effective_scope(scope),
        "python": str(python),
        "packages": expected_packages(contract, package_scope(scope)),
    }
    atomic_write_text(marker_path(contract, scope), json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


def environment_ready(contract: dict[str, Any], scope: str = "all") -> Path:
    python = venv_python(contract, scope)
    marker = marker_path(contract, scope)
    if not marker.is_file() or marker.is_symlink():
        raise RuntimeError("Bereitschaftsmarke der Umgebung fehlt.")
    try:
        data = json.loads(marker.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Bereitschaftsmarke ist beschädigt: {exc}") from exc
    if data.get("environment_key") != environment_key(contract, scope):
        raise RuntimeError("Bereitschaftsmarke gehört zu einer anderen Umgebung.")
    installed_versions(python, contract, scope)
    runtime_import_gate(python)
    if effective_scope(scope) == "quality":
        quality_executable_gate(python)
    return python


def repair_environment_state(contract: dict[str, Any], scope: str = "all") -> Path | None:
    """Recover a valid environment whose readiness marker was lost or damaged."""
    target = environment_path(contract, scope)
    python = venv_python(contract, scope)
    if target.is_symlink() or not target.is_dir() or not python.is_file() or not os.access(python, os.X_OK):
        return None
    try:
        installed_versions(python, contract, scope)
        runtime_import_gate(python)
        if effective_scope(scope) == "quality":
            quality_executable_gate(python)
        write_ready_marker(contract, scope, python)
    except RuntimeError:
        return None
    info(f"✓ {effective_scope(scope).capitalize()}-Umgebung repariert und erneut bestätigt")
    return python


def cache_path() -> Path:
    base = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))
    return base / "VideoBatchFast" / "toolchains" / toolchain_cache_key()


def candidate_wheelhouses(contract: dict[str, Any]) -> Iterable[Path]:
    current = wheelhouse_path(contract)
    yield current
    yield cache_path()
    parent = ROOT.parent
    projects = sorted(
        parent.glob("VideoBatch_Fast_2.8.3-rc*"),
        key=lambda path: path.stat().st_mtime if path.exists() else 0.0,
        reverse=True,
    )
    for project in projects:
        candidate = project / contract["paths"]["wheelhouse"]
        if candidate != current:
            yield candidate


def repair_current_metadata(contract: dict[str, Any], scope: str = "all") -> bool:
    current = wheelhouse_path(contract)
    if current.is_dir() and not current.is_symlink() and any(current.glob("*.whl")):
        progress(1, 5, "Vorhandene Pakete prüfen und Metadaten reparieren")
        try:
            manifest = rebuild_wheelhouse_metadata(current, contract)
            errors = verify_wheelhouse(current, contract, scope=package_scope(scope))
            if errors:
                raise ValueError(" | ".join(errors))
        except (OSError, ValueError) as exc:
            info(f"Lokale Paketbasis ist nicht ausreichend: {exc}")
            return False
        info(f"✓ Paketmetadaten bereit: {manifest['wheel_count']} Wheels")
        return True
    return False


def import_local_wheelhouse(source: Path, contract: dict[str, Any], scope: str = "all") -> bool:
    if source == wheelhouse_path(contract) or source.is_symlink() or not source.is_dir():
        return False
    wheels = sorted(source.glob("*.whl"))
    if not wheels:
        return False
    output = wheelhouse_path(contract)
    output.parent.mkdir(parents=True, exist_ok=True)
    staging: Path | None = Path(tempfile.mkdtemp(prefix=f".{output.name}.import-", dir=output.parent))
    try:
        for wheel in wheels:
            if wheel.is_symlink() or not wheel.is_file():
                continue
            shutil.copy2(wheel, staging / wheel.name)
        manifest = build_manifest(staging)
        write_manifest(staging, manifest)
        write_resolved_lock(staging, manifest, contract)
        errors = verify_wheelhouse(staging, contract, scope=package_scope(scope))
        if errors:
            return False
        publish_directory(staging, output)
        staging = None
        info(f"✓ Lokaler Paketbestand übernommen: {source}")
        return True
    finally:
        if staging is not None and staging.exists():
            safe_remove_tree(staging, allowed_parent=output.parent)


def recover_local_wheelhouse(contract: dict[str, Any], scope: str = "all") -> bool:
    if repair_current_metadata(contract, scope):
        return True
    progress(2, 5, "Frühere Versionen und lokalen Cache durchsuchen")
    seen: set[Path] = set()
    for source in candidate_wheelhouses(contract):
        resolved = source.resolve(strict=False)
        if resolved in seen:
            continue
        seen.add(resolved)
        try:
            if import_local_wheelhouse(source, contract, scope):
                return True
        except (OSError, ValueError, RuntimeError) as exc:
            info(f"Lokaler Bestand übersprungen: {source} · {exc}")
    return False


def store_cache(contract: dict[str, Any]) -> None:
    source = wheelhouse_path(contract)
    target = cache_path()
    if target.resolve(strict=False) == source.resolve(strict=False):
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    staging: Path | None = Path(tempfile.mkdtemp(prefix=f".{target.name}.cache-", dir=target.parent))
    try:
        for path in source.iterdir():
            if path.is_file() and not path.is_symlink():
                shutil.copy2(path, staging / path.name)
        publish_directory(staging, target)
        staging = None
    except (OSError, ValueError):
        pass
    finally:
        if staging is not None and staging.exists():
            safe_remove_tree(staging, allowed_parent=target.parent)


def build(contract: dict[str, Any], *, allow_online: bool, scope: str = "all") -> None:
    if not allow_online:
        raise RuntimeError("Online-Bezug ist für diesen automatischen Reparaturdurchlauf nicht freigegeben.")
    script = required_file("scripts/build_toolchain_wheelhouse.py")
    env = {**os.environ, "VIDEOBATCH_ALLOW_PUBLIC_PYPI": "1"}
    completed = run([
        sys.executable,
        str(script),
        "--scope",
        package_scope(scope),
        "--index-url",
        str(contract["policy"]["public_index"]),
    ], env=env)
    if not QUIET:
        print(completed.stdout, end="")
    if completed.returncode:
        raise RuntimeError("Paketbasis konnte nicht aufgebaut werden. Details stehen im Toolchain-Protokoll.")
    verify(contract, scope)
    store_cache(contract)


def install(contract: dict[str, Any], *, replace: bool, scope: str = "all") -> Path:
    verify(contract, scope)
    target = environment_path(contract, scope)
    python = venv_python(contract, scope)
    if target.exists() and not replace:
        return environment_ready(contract, scope)
    if target.is_symlink():
        raise RuntimeError("Toolchain-Umgebung darf kein symbolischer Link sein.")
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        safe_remove_tree(target, allowed_parent=target.parent)
    try:
        progress(4, 5, f"{effective_scope(scope).capitalize()}-Umgebung offline installieren")
        # Build directly at its immutable final, content-addressed path.  Moving a
        # venv after creation breaks absolute console-script shebangs.
        venv.EnvBuilder(with_pip=True, clear=True, symlinks=True).create(target)
        python = target / "bin" / "python"
        wheelhouse = wheelhouse_path(contract)
        lock_name = RUNTIME_RESOLVED_LOCK_NAME if effective_scope(scope) == "runtime" else RESOLVED_LOCK_NAME
        command = [
            str(python), "-m", "pip", "install",
            "--disable-pip-version-check", "--no-index", "--find-links", str(wheelhouse),
            "--only-binary=:all:", "--require-hashes",
            "--requirement", str(wheelhouse / lock_name),
        ]
        completed = run(command)
        if completed.returncode:
            raise RuntimeError("Offlineinstallation fehlgeschlagen:\n" + completed.stdout[-8000:])
        installed_versions(python, contract, scope)
        runtime_import_gate(python)
        if effective_scope(scope) == "quality":
            quality_executable_gate(python)
        write_ready_marker(contract, scope, python)
        return python
    except BaseException:
        if target.exists():
            safe_remove_tree(target, allowed_parent=target.parent)
        raise


def prepare(
    contract: dict[str, Any],
    *,
    auto_repair: bool,
    replace: bool,
    offline_only: bool,
    scope: str = "all",
) -> Path:
    with toolchain_lock():
        progress(1, 5, "Vorhandene Installation und Paketbasis prüfen")
        if not replace:
            try:
                python = environment_ready(contract, scope)
                info(f"✓ {effective_scope(scope).capitalize()}-Umgebung ist startbereit")
                return python
            except RuntimeError:
                repaired = repair_environment_state(contract, scope)
                if repaired is not None:
                    return repaired

        try:
            verify(contract, scope)
        except RuntimeError:
            if not recover_local_wheelhouse(contract, scope):
                if offline_only:
                    raise RuntimeError("Kein passender lokaler Paketbestand verfügbar.")
                if not auto_repair:
                    raise RuntimeError("Automatische Reparatur ist nicht freigegeben.")
                progress(3, 5, "Fehlende Pakete automatisch beziehen")
                build(contract, allow_online=True, scope=scope)
        else:
            progress(2, 5, "Wheelhouse, Manifest und Hashbindungen sind gültig")

        python = install(contract, replace=True, scope=scope)
        progress(5, 5, "Installierte Umgebung vollständig verifizieren")
        environment_ready(contract, scope)
        info(f"✓ {effective_scope(scope).capitalize()}-Umgebung vollständig vorbereitet")
        return python


def gate(contract: dict[str, Any], scope: str, *, run_external: bool) -> None:
    # A verified, immutable runtime environment remains launchable even when the
    # source project was moved or its installation wheel cache was cleaned.
    # Release-quality gates still require the complete reproducible wheelhouse.
    python = environment_ready(contract, scope)
    if effective_scope(scope) == "quality":
        verify(contract, scope)
    if effective_scope(scope) == "quality" and run_external:
        runner = required_file(str(contract["paths"]["external_runner"]))
        env = {**os.environ, "PATH": f"{python.parent}:{os.environ.get('PATH', '')}", "PYTHONPATH": str(ROOT / "src")}
        completed = run([str(python), str(runner), "--mode", "required", "--offline"], env=env)
        print(completed.stdout, end="")
        if completed.returncode:
            raise RuntimeError("Mindestens eines der externen Qualitätsgates ist rot.")


def status(contract: dict[str, Any]) -> int:
    report: dict[str, object] = {"build": contract["release_target"], "environments": {}}
    for scope in ("runtime", "quality"):
        item: dict[str, object] = {"path": str(environment_path(contract, scope))}
        try:
            manifest = verify(contract, scope)
            item["wheelhouse"] = {"status": "ready", "wheel_count": manifest["wheel_count"]}
        except Exception as exc:
            item["wheelhouse"] = {"status": "missing", "message": str(exc)}
        try:
            python = environment_ready(contract, scope)
            item["environment"] = {"status": "ready", "python": str(python)}
        except Exception as exc:
            item["environment"] = {"status": "missing", "message": str(exc)}
        report["environments"][scope] = item  # type: ignore[index]
    runtime_ready = report["environments"]["runtime"]["environment"]["status"] == "ready"  # type: ignore[index]
    report["ready_for_start"] = runtime_ready
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if runtime_ready else 1


def main() -> int:
    global QUIET
    parser = argparse.ArgumentParser(description="VideoBatch Laufzeit- und Qualitätsumgebungen.")
    parser.add_argument("action", choices=("contract", "build", "verify", "install", "prepare", "gate", "status", "path"))
    parser.add_argument("--scope", choices=("runtime", "quality", "all"), default="all")
    parser.add_argument("--allow-online", action="store_true")
    parser.add_argument("--auto-repair", action="store_true")
    parser.add_argument("--offline-only", action="store_true")
    parser.add_argument("--replace", action="store_true")
    parser.add_argument("--run-external", action="store_true")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()
    QUIET = args.quiet
    try:
        contract = load_contract()
        if args.action == "contract":
            print(json.dumps({"status": "passed", "contract": contract}, ensure_ascii=False, indent=2))
        elif args.action == "path":
            print(venv_python(contract, args.scope))
        elif args.action == "build":
            build(contract, allow_online=args.allow_online or args.auto_repair, scope=args.scope)
            print("TOOLCHAIN_WHEELHOUSE_BUILT")
        elif args.action == "verify":
            manifest = verify(contract, args.scope)
            print(f"TOOLCHAIN_WHEELHOUSE_VERIFIED={manifest['wheel_count']}")
        elif args.action == "install":
            python = install(contract, replace=args.replace, scope=args.scope)
            print(f"TOOLCHAIN_ENV_READY={python}")
        elif args.action == "prepare":
            python = prepare(
                contract,
                auto_repair=args.auto_repair or args.allow_online,
                replace=args.replace,
                offline_only=args.offline_only,
                scope=args.scope,
            )
            print(f"TOOLCHAIN_READY={python}")
        elif args.action == "gate":
            gate(contract, args.scope, run_external=args.run_external)
            print(f"TOOLCHAIN_GATE_PASSED={args.scope}")
        else:
            return status(contract)
        return 0
    except Exception as exc:
        code = {
            "contract": EXIT_CONTRACT,
            "build": EXIT_WHEELHOUSE,
            "verify": EXIT_WHEELHOUSE,
            "install": EXIT_INSTALL,
            "prepare": EXIT_INSTALL,
            "gate": EXIT_GATE,
            "status": EXIT_GATE,
            "path": EXIT_CONTRACT,
        }[args.action]
        print(f"TOOLCHAIN_BLOCKED[{code}]: {type(exc).__name__}: {exc}", file=sys.stderr)
        return code


if __name__ == "__main__":
    raise SystemExit(main())
