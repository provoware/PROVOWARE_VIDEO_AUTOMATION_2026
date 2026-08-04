#!/usr/bin/env python3
from __future__ import annotations

import argparse
import filecmp
import hashlib
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence


@dataclass(frozen=True)
class BuildArtifacts:
    output_dir: Path
    appdir: Path
    portable_tar: Path
    portable_run: Path
    portable_tar_sha256: str
    portable_run_sha256: str


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_report(output_dir: Path) -> dict[str, Any]:
    report_path = output_dir / "PORTABLE_BUILD_REPORT.json"
    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Build-Bericht unlesbar: {report_path}: {exc}") from exc
    if not isinstance(report, dict) or report.get("status") != "passed":
        raise ValueError(f"Build-Bericht ist nicht freigegeben: {report_path}")
    return report


def _contained_path(output_dir: Path, raw_path: object, label: str) -> Path:
    if not isinstance(raw_path, str) or not raw_path.strip():
        raise ValueError(f"{label}: Pfad fehlt im Build-Bericht.")
    candidate = Path(raw_path).expanduser()
    if not candidate.is_absolute():
        candidate = output_dir / candidate
    resolved = candidate.resolve()
    root = output_dir.resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"{label}: Pfad liegt außerhalb des Ausgabeordners: {resolved}") from exc
    if not resolved.exists():
        raise ValueError(f"{label}: Datei oder Ordner fehlt: {resolved}")
    return resolved


def _artifact(
    output_dir: Path,
    report: dict[str, Any],
    key: str,
) -> tuple[Path, str]:
    entry = report.get(key)
    if not isinstance(entry, dict):
        raise ValueError(f"{key}: Artefaktnachweis fehlt.")
    path = _contained_path(output_dir, entry.get("path"), key)
    if not path.is_file():
        raise ValueError(f"{key}: Artefakt ist keine Datei: {path}")
    expected_size = entry.get("size")
    if not isinstance(expected_size, int) or expected_size != path.stat().st_size:
        raise ValueError(f"{key}: Dateigröße stimmt nicht mit dem Build-Bericht überein.")
    expected_sha = entry.get("sha256")
    if not isinstance(expected_sha, str) or len(expected_sha) != 64:
        raise ValueError(f"{key}: SHA-256 fehlt oder ist ungültig.")
    actual_sha = sha256_file(path)
    if actual_sha != expected_sha:
        raise ValueError(f"{key}: SHA-256 stimmt nicht mit dem Build-Bericht überein.")
    return path, actual_sha


def inspect_build(output_dir: Path) -> BuildArtifacts:
    output_dir = output_dir.expanduser().resolve()
    report = _read_report(output_dir)
    appdir = _contained_path(output_dir, report.get("appdir"), "appdir")
    if not appdir.is_dir() or not (appdir / "AppRun").is_file():
        raise ValueError(f"appdir: AppRun fehlt: {appdir}")
    portable_tar, portable_tar_sha = _artifact(output_dir, report, "portable_tar")
    portable_run, portable_run_sha = _artifact(output_dir, report, "portable_run")
    return BuildArtifacts(
        output_dir=output_dir,
        appdir=appdir,
        portable_tar=portable_tar,
        portable_run=portable_run,
        portable_tar_sha256=portable_tar_sha,
        portable_run_sha256=portable_run_sha,
    )


def _run_checked(command: list[str], timeout: int = 300) -> None:
    completed = subprocess.run(
        command,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=timeout,
        check=False,
        errors="replace",
    )
    if completed.returncode:
        output = completed.stdout.strip()
        raise ValueError(
            f"Laufzeitprüfung fehlgeschlagen ({completed.returncode}): {' '.join(command)}"
            + (f"\n{output}" if output else "")
        )


def verify(first_dir: Path, second_dir: Path, report_path: Path) -> dict[str, Any]:
    first = inspect_build(first_dir)
    second = inspect_build(second_dir)

    comparisons = (
        ("portable_tar", first.portable_tar, second.portable_tar),
        ("portable_run", first.portable_run, second.portable_run),
    )
    for label, first_path, second_path in comparisons:
        if not filecmp.cmp(first_path, second_path, shallow=False):
            raise ValueError(f"{label}: Die beiden Builds sind nicht byteidentisch.")

    app_run = first.appdir / "AppRun"
    _run_checked([str(app_run), "--portable-verify"])
    _run_checked([str(app_run), "--portable-smoke-test"])

    result: dict[str, Any] = {
        "schema_version": 1,
        "status": "passed",
        "first_output": str(first.output_dir),
        "second_output": str(second.output_dir),
        "portable_tar_sha256": first.portable_tar_sha256,
        "portable_run_sha256": first.portable_run_sha256,
        "byte_identical": True,
        "portable_verify": "passed",
        "portable_smoke_test": "passed",
    }
    report_path = report_path.expanduser().resolve()
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Prüft zwei portable Builds versionsunabhängig auf Integrität und Reproduzierbarkeit."
    )
    parser.add_argument("--first", type=Path, required=True)
    parser.add_argument("--second", type=Path, required=True)
    parser.add_argument(
        "--report",
        type=Path,
        default=Path("KUBUNTU_REPRODUCIBILITY.json"),
    )
    args = parser.parse_args(argv)
    result = verify(args.first, args.second, args.report)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
