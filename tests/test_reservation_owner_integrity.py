"""Isolierte Ausgabe-Reservierungsregressionen, keine echten Medien."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from videobatch_fast import naming


class ReservationIntegrityTests(unittest.TestCase):
    def test_live_owner_is_not_displaced_by_age(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "out.mp4"
            first = naming.reserve_output_targets([target])[0]
            payload = json.loads(first.marker.read_text())
            payload["created_unix"] = time.time() - 90000
            first.marker.write_text(json.dumps(payload))
            with self.assertRaises(FileExistsError):
                naming.reserve_output_targets([target])
            first.release()

    def test_release_does_not_remove_replacement_owner(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "out.mp4"
            first = naming.reserve_output_targets([target])[0]
            first.marker.unlink()
            second = naming.reserve_output_targets([target])[0]
            first.release()
            self.assertTrue(second.marker.exists())
            second.release()
            self.assertFalse(second.marker.exists())

    def test_other_process_cannot_acquire_a_live_target(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "out.mp4"
            first = naming.reserve_output_targets([target])[0]
            code = (
                "import sys; from pathlib import Path; "
                "from videobatch_fast.naming import reserve_output_targets; "
                "reserve_output_targets([Path(sys.argv[1])])"
            )
            try:
                result = subprocess.run(
                    [sys.executable, "-c", code, str(target)],
                    capture_output=True, text=True, timeout=10,
                )
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("FileExistsError", result.stderr)
                self.assertTrue(first.marker.exists())
            finally:
                first.release()

    def test_dead_owner_can_be_recovered(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "out.mp4"
            marker = naming.reservation_marker(target)
            marker.write_text(json.dumps({"pid": 123456, "created_unix": time.time()}))
            with patch.object(naming, "_pid_is_alive", return_value=False):
                reservation = naming.reserve_output_targets([target])[0]
            self.assertEqual(json.loads(marker.read_text())["pid"], os.getpid())
            reservation.release()

    def test_recent_incomplete_marker_is_not_stolen(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "out.mp4"
            naming.reservation_marker(target).write_bytes(b"")
            with self.assertRaises(FileExistsError):
                naming.reserve_output_targets([target])


    def test_release_cannot_delete_inode_replaced_under_same_token(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "out.mp4"
            old = naming.reserve_output_targets([target])[0]
            marker = old.marker
            data = marker.read_bytes()
            marker.unlink()
            marker.write_bytes(data)
            old.release()
            self.assertEqual(marker.read_bytes(), data)
            marker.unlink()

    def test_reclaim_does_not_follow_symlink_to_foreign_data(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            foreign = root / "foreign.json"
            foreign.write_bytes(b"important")
            target = root / "out.mp4"
            naming.reservation_marker(target).symlink_to(foreign)
            with self.assertRaises(FileExistsError):
                naming.reserve_output_targets([target])
            self.assertEqual(foreign.read_bytes(), b"important")

    def test_release_does_not_remove_foreign_marker_after_json_corruption(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "out.mp4"
            reservation = naming.reserve_output_targets([target])[0]
            reservation.marker.write_text("not-json")
            reservation.release()
            self.assertTrue(naming.reservation_marker(target).exists())


if __name__ == "__main__":
    unittest.main()
