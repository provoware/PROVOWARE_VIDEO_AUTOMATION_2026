#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import tempfile
from typing import Any, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "RELEASE_MANIFEST.json"


class EvidenceExportError(RuntimeError):
    pass


def _reject_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise EvidenceExportError(f"Doppelter JSON-Schlüssel: {key!r}")
        result[key] = value
    return result


def _load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_reject_duplicate_pairs,
        )
    except (OSError, UnicodeError, json.JSONDecodeError, EvidenceExportError) as exc:
        raise EvidenceExportError(f"Ungültige JSON-Datei {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise EvidenceExportError(f"JSON-Wurzel muss ein Objekt sein: {path}")
    return value


def _manifest_binding() -> tuple[str, str]:
    manifest = _load(MANIFEST)
    candidate = str(manifest.get("version") or "").strip()
    if not candidate:
        raise EvidenceExportError("RELEASE_MANIFEST.json enthält keine Version.")
    digest = hashlib.sha256(MANIFEST.read_bytes()).hexdigest()
    return candidate, digest


def _utc_timestamp(value: object | None = None) -> str:
    if value:
        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            if parsed.tzinfo is not None:
                return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
        except ValueError:
            pass
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _atomic_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise


def _evidence_dir(root: Path, candidate: str) -> Path:
    return root.expanduser().resolve(strict=False) / candidate


def _check_named(report: Mapping[str, Any], name: str) -> bool:
    checks = report.get("checks")
    if not isinstance(checks, list):
        return False
    return any(
        isinstance(item, Mapping)
        and str(item.get("name") or "") == name
        and item.get("ok") is True
        for item in checks
    )


def export_kubuntu(source: Path, evidence_root: Path) -> Path:
    report = _load(source)
    candidate, digest = _manifest_binding()
    automated = report.get("automated") if isinstance(report.get("automated"), Mapping) else {}
    manual = report.get("manual_approval") if isinstance(report.get("manual_approval"), Mapping) else {}
    qt = report.get("qt") if isinstance(report.get("qt"), Mapping) else {}
    start = report.get("start_chain") if isinstance(report.get("start_chain"), Mapping) else {}
    platform = report.get("platform") if isinstance(report.get("platform"), Mapping) else {}
    screenshots = report.get("screenshots") if isinstance(report.get("screenshots"), list) else []

    checks = {
        "physical_session": report.get("overall") == "green" and automated.get("platform") == "green",
        "application_started": start.get("ok") is True,
        "native_wayland_backend": str(qt.get("backend") or "").lower().startswith("wayland"),
        "preview_rendered": automated.get("layout") == "green"
        and any(Path(str(item)).name == "preview.png" for item in screenshots),
        "window_scaling_checked": automated.get("layout") == "green"
        and _check_named(report, "Nutzbare Bildschirmfläche"),
    }
    if manual.get("approved") is not True or not all(checks.values()):
        missing = ", ".join(key for key, ok in checks.items() if not ok) or "manuelle Sichtfreigabe"
        raise EvidenceExportError(
            "Kubuntu-Stable-Nachweis nicht exportiert: Abnahme ist nicht vollständig grün "
            f"({missing})."
        )

    payload = {
        "schema_version": 1,
        "evidence_type": "kubuntu_26_04_wayland",
        "candidate_id": candidate,
        "manifest_sha256": digest,
        "result": "passed",
        "timestamp": _utc_timestamp(manual.get("approved_at") or report.get("generated_at")),
        "environment": {
            "target": report.get("target"),
            "platform": dict(platform),
            "qt": dict(qt),
            "reviewer": str(manual.get("reviewer") or ""),
        },
        "checks": checks,
    }
    target = _evidence_dir(evidence_root, candidate) / "kubuntu_26_04_wayland.json"
    _atomic_json(target, payload)
    return target


def _sha256_value(value: object) -> bool:
    text = str(value or "")
    return len(text) == 64 and all(char in "0123456789abcdefABCDEF" for char in text)


def export_long_render(source: Path, evidence_root: Path) -> Path | None:
    state = _load(source)
    if bool(state.get("rehearsal_only")):
        return None
    candidate, digest = _manifest_binding()
    if str(state.get("candidate") or "") != candidate:
        raise EvidenceExportError(
            "Langzeitrender gehört nicht zum aktuellen Release-Kandidaten: "
            f"{state.get('candidate')!r} != {candidate!r}."
        )

    jobs = state.get("jobs") if isinstance(state.get("jobs"), list) else []
    target_info = state.get("target") if isinstance(state.get("target"), Mapping) else {}
    output_manifest = state.get("output_manifest") if isinstance(state.get("output_manifest"), Mapping) else {}
    outputs = output_manifest.get("entries") if isinstance(output_manifest.get("entries"), list) else []
    completed_jobs = [item for item in jobs if isinstance(item, Mapping) and item.get("state") == "completed"]

    checks = {
        "large_media_selection": len(jobs) == 96 and len(completed_jobs) == 96,
        "slow_external_target": target_info.get("external_usb") is True
        and str(target_info.get("filesystem") or "").lower() == "ext4"
        and isinstance(target_info.get("write_mib_s"), (int, float))
        and float(target_info["write_mib_s"]) <= 35.0,
        "render_completed": state.get("state") == "completed"
        and state.get("terminal_event") == "run_completed",
        "output_hash_verified": len(outputs) == 96
        and all(
            isinstance(item, Mapping)
            and _sha256_value(item.get("sha256"))
            and int(item.get("size") or 0) > 0
            for item in outputs
        )
        and _sha256_value(output_manifest.get("digest")),
    }
    if not all(checks.values()):
        missing = ", ".join(key for key, ok in checks.items() if not ok)
        raise EvidenceExportError(f"Langzeitrender-Stable-Nachweis nicht exportiert: {missing}.")

    payload = {
        "schema_version": 1,
        "evidence_type": "long_render",
        "candidate_id": candidate,
        "manifest_sha256": digest,
        "result": "passed",
        "timestamp": _utc_timestamp(state.get("finished_at")),
        "environment": {
            "target": dict(target_info),
            "run_id": state.get("run_id"),
            "resource_mode": state.get("resource_mode"),
            "output_count": len(outputs),
        },
        "checks": checks,
    }
    target = _evidence_dir(evidence_root, candidate) / "long_render.json"
    _atomic_json(target, payload)
    return target


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        description="Exportiert reale Stable-Abnahmen in das strikt validierte Nachweisformat."
    )
    result.add_argument(
        "--evidence-root",
        type=Path,
        required=True,
        help="Basisordner; je Release-Kandidat wird automatisch ein Unterordner erzeugt.",
    )
    sub = result.add_subparsers(dest="kind", required=True)
    kubuntu = sub.add_parser("kubuntu")
    kubuntu.add_argument("--acceptance", type=Path, required=True)
    long_render = sub.add_parser("long-render")
    long_render.add_argument("--state", type=Path, required=True)
    return result


def main(argv: Sequence[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.kind == "kubuntu":
            target = export_kubuntu(args.acceptance, args.evidence_root)
        else:
            target = export_long_render(args.state, args.evidence_root)
    except EvidenceExportError as exc:
        print(f"STABLE-NACHWEIS BLOCKIERT: {exc}", file=os.sys.stderr)
        return 14
    if target is None:
        print("STABLE-NACHWEIS: Probelauf erkannt; kein physischer Stable-Nachweis erzeugt.")
    else:
        print(f"STABLE-NACHWEIS ERZEUGT: {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
