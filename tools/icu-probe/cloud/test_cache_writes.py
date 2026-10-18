"""Concurrent cache writers publish complete records without sharing a temporary."""

from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from prepare import write_json


class CacheWriteTests(unittest.TestCase):
    def test_concurrent_writers_keep_independent_temporary_files(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "manifest.json"
            values = [{"writer": index, "payload": "Unicode 数据" * 1024} for index in range(2)]
            ready_to_publish = threading.Barrier(2, timeout=5)
            replace = Path.replace

            def publish_together(source, target):
                ready_to_publish.wait()
                return replace(source, target)

            with patch.object(Path, "replace", publish_together):
                with ThreadPoolExecutor(max_workers=2) as pool:
                    futures = [pool.submit(write_json, destination, value) for value in values]
                    for future in futures:
                        future.result(timeout=6)
            self.assertIn(json.loads(destination.read_text(encoding="utf-8")), values)
            self.assertEqual(list(Path(directory).iterdir()), [destination])

    def test_serialization_failure_preserves_previous_record(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "manifest.json"
            write_json(destination, {"original": True})
            before = destination.read_bytes()
            with self.assertRaises(TypeError):
                write_json(destination, {"unsupported": object()})
            self.assertEqual(destination.read_bytes(), before)
            self.assertEqual(list(Path(directory).iterdir()), [destination])

    def test_publish_failure_removes_only_its_own_temporary_file(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "manifest.json"
            write_json(destination, {"original": True})
            before = destination.read_bytes()
            with patch.object(Path, "replace", side_effect=PermissionError("publish denied")):
                with self.assertRaises(PermissionError):
                    write_json(destination, {"new": True})
            self.assertEqual(destination.read_bytes(), before)
            self.assertEqual(list(Path(directory).iterdir()), [destination])


if __name__ == "__main__":
    unittest.main()
