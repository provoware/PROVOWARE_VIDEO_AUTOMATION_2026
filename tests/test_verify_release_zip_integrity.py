"""Verify genuine compact package records and reject mutated archive contents."""
from __future__ import annotations

import hashlib
import json
import stat
import zipfile
from pathlib import Path

import pytest

from scripts.verify_release_zip import verify_archive


def _write_package(path: Path, schema: int, *, changed: str = "") -> None:
    payload = b"source data"
    records = [{"path": "src/main.py", "size": len(payload),
                "sha256": hashlib.sha256(payload).hexdigest(), "mode": "0o644"}]
    manifest = {"schema_version": schema, "file_count": 1}
    if schema == 3:
        encoded = json.dumps(records, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
        manifest.update(representation="compact", files_sha256=hashlib.sha256(encoded).hexdigest())
    else:
        manifest["files"] = records
    with zipfile.ZipFile(path, "w") as archive:
        for name, data in (("RELEASE_MANIFEST.json", json.dumps(manifest).encode()),
                           ("src/main.py", b"tampered" if changed == "data" else payload)):
            member = zipfile.ZipInfo("project/" + name)
            member.external_attr = (stat.S_IFREG | (0o755 if changed == "mode" else 0o644)) << 16
            archive.writestr(member, data)
        if changed == "traversal":
            archive.writestr("project/../foreign", b"foreign")
        if changed == "extra":
            archive.writestr("other/extra", b"extra")


@pytest.mark.parametrize("schema", [2, 3])
def test_supported_manifests_verify_actual_zip_bytes(tmp_path: Path, schema: int) -> None:
    package = tmp_path / "package.zip"
    _write_package(package, schema)
    with zipfile.ZipFile(package) as archive:
        assert verify_archive(archive) == 1


@pytest.mark.parametrize("schema", [2, 3])
@pytest.mark.parametrize("changed", ["data", "mode", "traversal", "extra"])
def test_package_tampering_is_rejected(tmp_path: Path, schema: int, changed: str) -> None:
    package = tmp_path / "package.zip"
    _write_package(package, schema, changed=changed)
    with zipfile.ZipFile(package) as archive, pytest.raises(ValueError):
        verify_archive(archive)


def test_package_payload_is_read_in_bounded_chunks(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    package = tmp_path / "package.zip"
    _write_package(package, 3)
    with zipfile.ZipFile(package) as archive:
        original_open = archive.open

        class BoundedStream:
            def __init__(self, stream):
                self.stream = stream

            def __enter__(self):
                self.stream.__enter__()
                return self

            def __exit__(self, *args):
                return self.stream.__exit__(*args)

            def read(self, size=-1):
                assert 0 < size <= 1024 * 1024, "ZIP-Nutzdaten dürfen nicht unbegrenzt eingelesen werden"
                return self.stream.read(size)

        def guarded_open(member, *args, **kwargs):
            stream = original_open(member, *args, **kwargs)
            return BoundedStream(stream) if isinstance(member, zipfile.ZipInfo) else stream

        monkeypatch.setattr(archive, "open", guarded_open)
        assert verify_archive(archive) == 1
