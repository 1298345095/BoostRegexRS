"""Runner deadlines reject invalid budgets before any process or output work."""

import argparse
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SPEC = importlib.util.spec_from_file_location(
    "byte_regex_runner", Path(__file__).with_name("run.py"))
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


INVALID_TIMEOUTS = ("nan", "inf", "-inf", "1e309", "0", "-0.5")


class RunnerTimeouts(unittest.TestCase):
    def test_cli_rejects_invalid_timeouts_before_reading_inputs(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            output = directory / "evidence"
            for value in INVALID_TIMEOUTS:
                with self.subTest(timeout=value):
                    result = subprocess.run(
                        [sys.executable, "-B", runner.__file__,
                         "--program", str(directory / "missing-program"),
                         "--role", "reference", "--cases", str(directory / "missing-cases.tsv"),
                         "--output", str(output), "--timeout=" + value],
                        capture_output=True, text=True, timeout=5, check=False,
                    )
                    self.assertEqual(result.returncode, 2, result.stderr)
                    self.assertIn("Timeout must be finite and positive", result.stderr)
                    self.assertFalse(output.exists())

    def test_imported_runner_rejects_the_same_invalid_budgets(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            output = directory / "evidence"
            for value in INVALID_TIMEOUTS:
                with self.subTest(timeout=value):
                    with self.assertRaisesRegex(argparse.ArgumentTypeError, "finite and positive"):
                        runner.run(directory / "missing-program", "reference",
                                   directory / "missing-cases.tsv", output, 1, float(value))
                    self.assertFalse(output.exists())

    def test_finite_budget_terminates_and_preserves_a_hung_process(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            command = [sys.executable, "-B", "-c", "import time; time.sleep(30)"]
            result = runner.run_process(command, directory, 0.2)
            self.assertTrue(result["timed_out"])
            self.assertIsNone(result["returncode"])
            self.assertIsNone(result["launch_error"])
            self.assertEqual(result["command"], command)
            self.assertEqual(result, json.loads((directory / "process.json").read_text()))
            self.assertTrue((directory / "stdout.tsv").is_file())
            self.assertTrue((directory / "stderr.txt").is_file())


if __name__ == "__main__":
    unittest.main()
