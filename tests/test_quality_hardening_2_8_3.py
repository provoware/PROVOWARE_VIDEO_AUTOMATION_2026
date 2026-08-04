from __future__ import annotations

import io
import json
import queue
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

from videobatch_fast.models import MediaInfo, PairJob
from videobatch_fast.runner_process import ProcessExecution, _ProgressState
from videobatch_fast.sandbox_seccomp import SeccompInstaller, SeccompUnavailable, find_seccomp_library
from videobatch_fast.update_validation import UpdatePackageValidator, UpdatePolicy, safe_member


def _job(root: Path, *, fast_path: bool = False) -> PairJob:
    audio = root / "audio.wav"
    media = root / "image.png"
    output = root / "out.mp4"
    audio.write_bytes(b"audio")
    media.write_bytes(b"image")
    return PairJob(
        1,
        audio,
        media,
        output,
        MediaInfo(audio, "audio", duration=10.0),
        MediaInfo(media, "image"),
        fast_path,
        "test",
    )


class RunnerProcessErrorPathTests(unittest.TestCase):
    def setUp(self) -> None:
        self.events: list[tuple[str, dict]] = []
        self.processes = []
        self.cancelled = False
        self.execution = ProcessExecution(
            emit=lambda name, **payload: self.events.append((name, payload)),
            cancelled=lambda: self.cancelled,
            set_process=self.processes.append,
            terminate=lambda process: 143,
            cpu_ticks=lambda pid: 5,
        )

    def test_spawn_error_returns_failed_result(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch(
            "videobatch_fast.runner_process.subprocess.Popen", side_effect=OSError("fehlt")
        ):
            result = self.execution.run(["missing"], _job(Path(tmp)), 1, 1)
        self.assertFalse(result.success)
        self.assertEqual(result.returncode, 127)
        self.assertIn("fehlt", result.message)

    def test_progress_parser_tolerates_malformed_values(self):
        state = _ProgressState(started=1.0, duration=10.0)
        self.assertFalse(self.execution._apply_progress_line("ohne-gleich", state))
        self.assertFalse(self.execution._apply_progress_line("frame=nicht-int", state))
        self.assertFalse(self.execution._apply_progress_line("fps=nicht-float", state))
        self.assertFalse(self.execution._apply_progress_line("out_time_us=kaputt", state))
        self.assertTrue(self.execution._apply_progress_line("out_time_us=2000000", state))
        self.assertFalse(self.execution._apply_progress_line("out_time_us=1000000", state))
        self.execution._apply_progress_line("speed=1.25x", state)
        self.assertEqual(state.out_time, 2.0)
        self.assertEqual(state.speed, "1.25x")

    def test_drain_progress_and_stall_warning(self):
        state = _ProgressState(started=0.0, duration=10.0, last_progress=0.0)
        values: queue.Queue[str] = queue.Queue()
        values.put("out_time_ms=1000000")
        values.put("progress=continue")
        self.assertTrue(self.execution._drain_progress(values, state))
        with tempfile.TemporaryDirectory() as tmp, mock.patch(
            "videobatch_fast.runner_process.time.monotonic", return_value=30.0
        ):
            self.execution._emit_progress(state, ["ffmpeg"], _job(Path(tmp)), 1, 2)
        names = [name for name, _ in self.events]
        self.assertIn("log", names)
        self.assertIn("progress", names)

    def test_result_variants(self):
        with tempfile.TemporaryDirectory() as tmp:
            job = _job(Path(tmp))
            self.cancelled = True
            cancelled = self.execution._result(["ffmpeg"], job, 1, 1, 143, [], 0.0)
            self.assertIn("abgebrochen", cancelled.message)
            self.cancelled = False
            failed = self.execution._result(["ffmpeg"], job, 1, 1, 9, ["", "letzter Fehler"], 0.0)
            self.assertEqual(failed.message, "letzter Fehler")
            success = self.execution._result(["ffmpeg"], job, 1, 1, 0, [], 0.0)
            self.assertTrue(success.success)

    def test_output_size_and_close_errors_are_safe(self):
        class Broken:
            def close(self):
                raise OSError("kaputt")

        class Thread:
            def __init__(self):
                self.joined = False

            def join(self, timeout=None):
                self.joined = True

        process = type("P", (), {"stdout": Broken(), "stderr": Broken()})()
        first, second = Thread(), Thread()
        self.execution._close_process_streams(process, (first, second))
        self.assertTrue(first.joined and second.joined)
        self.assertEqual(self.execution._output_size(Path("/nicht/vorhanden")), 0)


class _Callable:
    def __init__(self, result=0):
        self.result = result
        self.calls = []
        self.argtypes = None
        self.restype = None

    def __call__(self, *args):
        self.calls.append(args)
        return self.result


class _FakeSeccomp:
    def __init__(self, *, context=123, resolved=1, rule=0, load=0):
        self.seccomp_init = _Callable(context)
        self.seccomp_release = _Callable(0)
        self.seccomp_syscall_resolve_name = _Callable(resolved)
        self.seccomp_rule_add = _Callable(rule)
        self.seccomp_load = _Callable(load)


class SeccompErrorPathTests(unittest.TestCase):
    def test_context_failure(self):
        with self.assertRaisesRegex(SeccompUnavailable, "Kontext"):
            SeccompInstaller(_FakeSeccomp(context=0)).install()

    def test_rule_failure_releases_context(self):
        lib = _FakeSeccomp(rule=-1)
        with self.assertRaisesRegex(SeccompUnavailable, "Regel"):
            SeccompInstaller(lib).install()
        self.assertTrue(lib.seccomp_release.calls)

    def test_load_failure_and_success(self):
        with self.assertRaisesRegex(SeccompUnavailable, "Filter"):
            SeccompInstaller(_FakeSeccomp(load=-1)).install()
        lib = _FakeSeccomp(resolved=-1)
        SeccompInstaller(lib).install()
        self.assertFalse(lib.seccomp_rule_add.calls)
        self.assertTrue(lib.seccomp_load.calls)

    def test_find_library_skips_broken_candidates(self):
        with mock.patch("videobatch_fast.sandbox_seccomp.ctypes.util.find_library", return_value="bad"), mock.patch(
            "videobatch_fast.sandbox_seccomp._library_works", side_effect=lambda value: value.endswith("libseccomp.so.2") and "x86_64" in value
        ):
            self.assertIn("x86_64", find_seccomp_library())
        with mock.patch("videobatch_fast.sandbox_seccomp.ctypes.util.find_library", return_value=None), mock.patch(
            "videobatch_fast.sandbox_seccomp._library_works", return_value=False
        ):
            with self.assertRaises(SeccompUnavailable):
                find_seccomp_library()


class UpdateValidationErrorPathTests(unittest.TestCase):
    def setUp(self) -> None:
        self.policy = UpdatePolicy(20, 100_000, 100.0, True, frozenset({"add", "replace", "delete"}))

    def _package(self, root: Path, manifest, extra: dict[str, bytes] | None = None) -> Path:
        package = root / "update.zip"
        with zipfile.ZipFile(package, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("update_manifest.json", json.dumps(manifest))
            for name, data in (extra or {}).items():
                archive.writestr(name, data)
        return package

    def test_safe_member_rejects_traversal_and_absolute_paths(self):
        self.assertFalse(safe_member("../x"))
        self.assertFalse(safe_member("/x"))
        self.assertFalse(safe_member("~x"))
        self.assertTrue(safe_member("src/x.py"))

    def test_invalid_manifest_entries(self):
        cases = [
            ({"version": "x", "compatible_from": ["old"], "files": []}, "Dateiliste"),
            ({"version": "x", "compatible_from": ["other"], "files": [{}]}, "kompatibel"),
            ({"version": "x", "compatible_from": ["old"], "files": ["bad"]}, "Dateieintrag"),
            ({"version": "x", "compatible_from": ["old"], "files": [{"path": "x", "operation": "run"}]}, "Operation"),
            ({"version": "x", "compatible_from": ["old"], "files": [{"path": "x", "operation": "add", "sha256": "0" * 64}]}, "fehlt"),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for index, (manifest, text) in enumerate(cases):
                package = self._package(root, manifest)
                result = UpdatePackageValidator("old", self.policy).validate(package)
                self.assertFalse(result.valid, index)
                self.assertIn(text, result.message)

    def test_bad_hash_and_undeclared_extra(self):
        manifest = {
            "version": "x",
            "compatible_from": ["old"],
            "files": [{"path": "x.txt", "operation": "add", "sha256": "0" * 64}],
        }
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = UpdatePackageValidator("old", self.policy).validate(self._package(root, manifest, {"x.txt": b"x"}))
            self.assertIn("Prüfsumme", result.message)
            digest = __import__("hashlib").sha256(b"x").hexdigest()
            manifest["files"][0]["sha256"] = digest
            result = UpdatePackageValidator("old", self.policy).validate(
                self._package(root, manifest, {"x.txt": b"x", "extra.txt": b"extra"})
            )
            self.assertIn("Nicht deklarierte", result.message)

    def test_delete_payload_and_stable_binding_fail_closed(self):
        delete = {
            "version": "x",
            "compatible_from": ["old"],
            "files": [{"path": "x.txt", "operation": "delete"}],
        }
        stable = {"version": "x", "compatible_from": ["old"], "channel": "stable", "files": [{"path": "x.txt", "operation": "delete"}]}
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = UpdatePackageValidator("old", self.policy).validate(self._package(root, delete, {"x.txt": b"x"}))
            self.assertIn("Löschoperation", result.message)
            result = UpdatePackageValidator("old", self.policy).validate(self._package(root, stable))
            self.assertIn("visuelle Freigabe", result.message)


if __name__ == "__main__":
    unittest.main()
