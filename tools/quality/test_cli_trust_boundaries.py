"""Exercise the process boundary reported by Sonar without restricting CLI paths."""

import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("cloud_prepare", ROOT / "tools/icu-probe/cloud/prepare.py")
prepare = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(prepare)


class CliTrustBoundaries(unittest.TestCase):
    def test_command_arguments_are_literal_and_never_evaluated_by_a_shell(self):
        with tempfile.TemporaryDirectory() as directory:
            working = Path(directory)
            marker = working / "unexpected-shell-execution"
            argument = f"; touch '{marker}' ; $(touch '{marker}')"
            log = working / "literal-arguments.log"
            prepare.run_logged(
                [sys.executable, "-c", "import sys; print(repr(sys.argv[1]))", argument],
                cwd=working, log=log,
            )
            self.assertFalse(marker.exists())
            self.assertEqual(log.read_text(encoding="utf-8").splitlines()[1], repr(argument))

    def test_explicit_output_paths_can_be_outside_the_checkout(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "chosen directory; literal" / "report.json"
            prepare.write_json(output, {"value": "caller-selected destination"})
            self.assertEqual(json.loads(output.read_text(encoding="utf-8")),
                             {"value": "caller-selected destination"})

    def test_failed_process_keeps_its_log_and_is_not_reported_as_success(self):
        with tempfile.TemporaryDirectory() as directory:
            working = Path(directory)
            log = working / "failure.log"
            with self.assertRaisesRegex(RuntimeError, "Command failed \\(7\\)"):
                prepare.run_logged([sys.executable, "-c", "print('failure evidence'); raise SystemExit(7)"],
                                   cwd=working, log=log)
            self.assertIn("failure evidence", log.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
