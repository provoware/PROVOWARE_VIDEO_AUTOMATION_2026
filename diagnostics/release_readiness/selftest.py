#!/usr/bin/env python3
from __future__ import annotations

import copy
import hashlib
import json
import tempfile
from pathlib import Path

import engine
import generate_from_evidence as canonical


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def manifest_item(path: Path, root: Path) -> dict[str, object]:
    data = path.read_bytes()
    return {
        "path": path.relative_to(root).as_posix(),
        "size": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "mode": oct(path.stat().st_mode & 0o777),
    }


def fixture() -> tuple[tempfile.TemporaryDirectory[str], Path, dict[str, object]]:
    temporary = tempfile.TemporaryDirectory()
    root = Path(temporary.name)
    source = json.loads(canonical.EVIDENCE_PATH.read_text(encoding="utf-8"))
    value = copy.deepcopy(source)
    value["manifest"]["file_count"] = 1
    value["tests"]["passed"] = 10
    value["tests"]["failed"] = 0
    value["tests"]["skipped"] = 0
    value["matrix"]["passed_targets"] = 4
    value["matrix"]["total_targets"] = 4
    value["matrix"]["status"] = "passed"
    value["stable_gates"] = [
        {"id": "external", "label": "Externer Nachweis", "status": "open", "reason": "noch offen"}
    ]
    value["stable_ready"] = False
    value["progress"] = {
        "percent": 90,
        "completed": 9,
        "open": 1,
        "total": 10,
        "current_todo": "Externer Nachweis",
    }
    evidence_path = root / "diagnostics/release_readiness/RELEASE_EVIDENCE.json"
    write_json(evidence_path, value)
    payload = root / "payload.txt"
    payload.write_text("immutable\n", encoding="utf-8")
    write_json(
        root / "RELEASE_MANIFEST.json",
        {
            "build": value["product"]["version"],
            "channel": value["product"]["channel"],
            "file_count": 1,
            "files": [manifest_item(payload, root)],
        },
    )
    readme = (
        "<!-- release-status:start -->\nplaceholder\n<!-- release-status:end -->\n\n"
        "<!-- release-files:start -->\nplaceholder\n<!-- release-files:end -->\n"
    )
    (root / "README.md").write_text(
        canonical.render_readme(value, readme),
        encoding="utf-8",
    )
    write_json(root / "DEVELOPMENT_STATUS.json", canonical.render_development(value))
    write_json(root / "QUALITY_ENVIRONMENT_STATUS.json", canonical.render_quality(value))
    write_json(root / "RELEASE_FILE_STATUS.json", canonical.render_release_files(value))
    write_json(root / str(value["approved_quality_report"]), canonical.render_build(value))
    return temporary, root, value


def run_case(ci_status: str, expected: str, close_gate: bool = False) -> None:
    temporary, root, value = fixture()
    try:
        if close_gate:
            value["stable_gates"][0]["status"] = "passed"
            value["stable_gates"][0]["reason"] = "bestanden"
            value["stable_ready"] = True
            value["progress"] = {
                "percent": 100,
                "completed": 10,
                "open": 0,
                "total": 10,
                "current_todo": "Freigabe",
            }
            write_json(root / "diagnostics/release_readiness/RELEASE_EVIDENCE.json", value)
            (root / "README.md").write_text(
                canonical.render_readme(
                    value,
                    (
                        "<!-- release-status:start -->\nplaceholder\n<!-- release-status:end -->\n\n"
                        "<!-- release-files:start -->\nplaceholder\n<!-- release-files:end -->\n"
                    ),
                ),
                encoding="utf-8",
            )
            write_json(root / "DEVELOPMENT_STATUS.json", canonical.render_development(value))
            write_json(root / "QUALITY_ENVIRONMENT_STATUS.json", canonical.render_quality(value))
            write_json(root / "RELEASE_FILE_STATUS.json", canonical.render_release_files(value))
            write_json(root / str(value["approved_quality_report"]), canonical.render_build(value))
        documents, paths, hashes = engine.load_evidence(root)
        ci = {
            "schema_version": 1,
            "status": ci_status,
            "checks": [{"name": "contract", "status": ci_status}],
            "source": "selftest",
        }
        findings, gates = engine.analyze(root, documents, ci)
        result = engine.result_document(
            documents,
            ci,
            findings,
            gates,
            hashes,
            "0123456789abcdef",
            "2026-08-05T00:00:00+00:00",
        )
        assert result["overall_status"] == expected, result
        assert engine.unchanged_findings(paths, hashes) == []
    finally:
        temporary.cleanup()


def drift_case() -> None:
    temporary, root, _value = fixture()
    try:
        quality_path = root / "QUALITY_ENVIRONMENT_STATUS.json"
        quality = json.loads(quality_path.read_text(encoding="utf-8"))
        quality["internal_gates"]["tests"]["passed"] = 9
        write_json(quality_path, quality)
        documents, _paths, hashes = engine.load_evidence(root)
        findings, gates = engine.analyze(
            root,
            documents,
            {"status": "pass", "checks": [{"name": "ci", "status": "pass"}], "source": "selftest"},
        )
        result = engine.result_document(
            documents,
            {"status": "pass", "checks": [{"name": "ci", "status": "pass"}], "source": "selftest"},
            findings,
            gates,
            hashes,
            "0123456789abcdef",
            "2026-08-05T00:00:00+00:00",
        )
        assert result["overall_status"] == "red", result
        assert any(item["code"] == "TEST_COUNT_DRIFT" for item in result["findings"]), result
    finally:
        temporary.cleanup()


def main() -> int:
    run_case("pass", "yellow")
    run_case("running", "yellow")
    run_case("pass", "green", close_gate=True)
    drift_case()
    print("RELEASE-EVIDENCE SELFTEST PASS · yellow/open · yellow/running · green/complete · red/drift")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
