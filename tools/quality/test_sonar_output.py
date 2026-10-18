"""Preserve each observation and refuse reused destinations before HTTP work."""

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import collect_sonar_evidence as collector


class SonarOutputTests(unittest.TestCase):
    def setUp(self):
        self.temporary = TemporaryDirectory(dir=collector.ROOT.parent)
        self.addCleanup(self.temporary.cleanup)
        self.output = Path(self.temporary.name) / "observation"

    def test_existing_observation_is_unchanged_and_never_contacts_server(self):
        self.output.mkdir()
        original = b'{"status": 403, "body": "original evidence"}\n'
        response_path = self.output / "github-check-runs.json"
        response_path.write_bytes(original)
        with patch.object(collector, "fetch") as fetch:
            with self.assertRaises(FileExistsError):
                collector.collect("a" * 40, 1, self.output)
        fetch.assert_not_called()
        self.assertEqual(response_path.read_bytes(), original)
        self.assertEqual(list(self.output.iterdir()), [response_path])

    def test_existing_empty_directory_is_also_refused_before_network(self):
        self.output.mkdir()
        with patch.object(collector, "fetch") as fetch:
            with self.assertRaises(FileExistsError):
                collector.collect("a" * 40, 1, self.output)
        fetch.assert_not_called()
        self.assertEqual(list(self.output.iterdir()), [])

    def test_new_external_output_retains_a_failed_first_response(self):
        self.assertFalse(self.output.is_relative_to(collector.ROOT))
        failed = {"url": "https://api.github.com/synthetic", "status": 503,
                  "payload": {"message": "synthetic unavailable"}}
        with patch.object(collector, "fetch", return_value=failed) as fetch:
            with self.assertRaisesRegex(RuntimeError, "response was preserved"):
                collector.collect("a" * 40, 1, self.output)
        fetch.assert_called_once()
        response_path = self.output / "github-check-runs.json"
        self.assertEqual(json.loads(response_path.read_text(encoding="utf-8")), failed)
        self.assertEqual(list(self.output.iterdir()), [response_path])


if __name__ == "__main__":
    unittest.main()
