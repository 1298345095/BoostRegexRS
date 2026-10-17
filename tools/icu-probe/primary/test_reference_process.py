"""Integration regressions for preserving coverage after an oracle signal."""

import json
import os
from pathlib import Path
import sys
import tempfile
import textwrap
import unittest

from compare import compare
from reference_process import ReferenceExecutionError, run_reference


@unittest.skipUnless(os.name == "posix", "POSIX subprocess signal return codes are required")
class ReferenceProcessTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.source = self.directory / "cases.tsv"
        self.output = self.directory / "reference.tsv"
        self.candidate = self.directory / "candidate.tsv"
        self.calls = self.directory / "calls.jsonl"
        self.oracle = self.directory / "fake_oracle.py"
        self.oracle.write_text(textwrap.dedent("""\
            import json
            import os
            from pathlib import Path
            import resource
            import signal
            import sys

            resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
            lines = sys.stdin.read().splitlines()
            rows = [line.split('\\t') for line in lines[1:]]
            ids = [row[0] for row in rows]
            with Path(os.environ['ORACLE_CALLS']).open('a') as stream:
                stream.write(json.dumps(ids) + '\\n')
            print('original batch: ' + ','.join(ids), file=sys.stderr, flush=True)
            print('case_id\\traw_icu_hex\\tboost_u32_hex', flush=True)
            mode = os.environ['ORACLE_MODE']
            if mode.startswith('exit_'):
                sys.exit(int(mode.split('_')[1]))
            if mode == 'batch_signal' and len(rows) == 3:
                os.kill(os.getpid(), signal.SIGSEGV)
            for identity, value in rows:
                if mode == 'signal' and identity == 'boom':
                    os.kill(os.getpid(), signal.SIGSEGV)
                if mode == 'protocol_error' and identity == 'after':
                    continue
                print(f'{identity}\\t{value},00\\t000000{value}', flush=True)
            """), encoding="utf-8")
        self.source.write_text("case_id\tutf8_hex\nbefore\t61\nboom\t62\nafter\t63\n", encoding="utf-8")
        self.good = (
            "case_id\traw_icu_hex\tboost_u32_hex\n"
            "before\t61,00\t00000061\nboom\t62,00\t00000062\nafter\t63,00\t00000063\n"
        )
        self.candidate.write_text(self.good, encoding="utf-8")

    def run_oracle(self, mode):
        env = dict(os.environ, ORACLE_MODE=mode, ORACLE_CALLS=str(self.calls))
        return run_reference([sys.executable, self.oracle], self.source, self.output, env, self.directory)

    def recorded_calls(self):
        return [json.loads(line) for line in self.calls.read_text().splitlines()]

    def test_normal_corpus_runs_once_and_preserves_complete_keys(self):
        metadata = self.run_oracle("normal")
        self.assertEqual(self.output.read_text(), self.good)
        self.assertEqual(metadata["subprocess_runs"], 1)
        self.assertEqual(metadata["successful_batches"], 1)
        self.assertEqual(metadata["reference_error_count"], 0)
        self.assertFalse(metadata["isolation_used"])
        self.assertTrue(metadata["reference_error_free"])
        self.assertEqual(self.recorded_calls(), [["before", "boom", "after"]])
        self.assertEqual(compare(self.source, self.output, self.candidate)["totals"]["passed"], 3)

    def test_signal_isolates_one_row_and_keeps_neighbor_keys_and_original_evidence(self):
        metadata = self.run_oracle("signal")
        self.assertTrue(metadata["isolation_used"])
        self.assertEqual(metadata["subprocess_runs"], 5)
        self.assertEqual(metadata["signal_failures"], 3)
        self.assertEqual(metadata["reference_error_count"], 1)
        self.assertFalse(metadata["reference_error_free"])
        self.assertEqual(metadata["unresolved_signal_ranges"], [])
        self.assertEqual(metadata["output_rows"], 3)
        expected = self.good.replace("boom\t62,00\t00000062", "boom\tERROR:SIGNAL_11\tERROR:SIGNAL_11")
        self.assertEqual(self.output.read_text(), expected)
        result = compare(self.source, self.output, self.candidate)
        self.assertEqual(result["totals"]["passed"], 2)
        self.assertEqual(result["totals"]["reference_error"], 1)
        self.assertEqual(result["totals"]["mismatched"], 0)
        self.assertEqual(result["status"], "differences_or_incomplete")
        first = metadata["attempts"][0]
        self.assertEqual(first["returncode"], -11)
        self.assertEqual(Path(first["stdout"]).read_text(), self.good.split("boom\t")[0])
        original_stderr = "original batch: before,boom,after\n"
        self.assertEqual(Path(first["stderr"]).read_text(), original_stderr)
        self.assertEqual(self.output.with_suffix(".stderr.log").read_text(), original_stderr)
        self.assertEqual(self.recorded_calls(), [["before", "boom", "after"], ["before"],
                                                 ["boom", "after"], ["boom"], ["after"]])
        saved = json.loads(Path(metadata["metadata_path"]).read_text())
        self.assertEqual(saved, metadata)

    def test_batch_only_signal_is_not_erased_by_successful_smaller_calls(self):
        metadata = self.run_oracle("batch_signal")
        self.assertEqual(self.output.read_text(), self.good)
        self.assertEqual(metadata["subprocess_runs"], 3)
        self.assertEqual(metadata["signal_failures"], 1)
        self.assertEqual(metadata["reference_error_count"], 0)
        self.assertFalse(metadata["reference_error_free"])
        self.assertEqual(metadata["unresolved_signal_ranges"], [{
            "begin": 0, "end": 3, "failed_attempt": 0, "signal_number": 11,
            "outcome": "reference_error_not_reproduced_by_subranges",
        }])

    def test_ordinary_exit_is_not_recursively_retried(self):
        for status in (2, 127):
            with self.subTest(status=status):
                self.calls.write_text("")
                with self.assertRaises(ReferenceExecutionError) as raised:
                    self.run_oracle(f"exit_{status}")
                self.assertEqual(raised.exception.kind, "nonzero_exit")
                self.assertEqual(self.recorded_calls(), [["before", "boom", "after"]])
                metadata = json.loads(self.output.with_suffix(".reference-process.json").read_text())
                self.assertEqual(metadata["status"], "execution_error")
                self.assertEqual(metadata["subprocess_runs"], 1)
                self.assertEqual(metadata["signal_failures"], 0)
                self.assertFalse(metadata["isolation_used"])
                self.assertEqual(metadata["attempts"][0]["returncode"], status)
                self.assertTrue(Path(metadata["attempts"][0]["stdout"]).is_file())

    def test_success_exit_with_missing_rows_is_a_protocol_error_without_retry(self):
        with self.assertRaises(ReferenceExecutionError) as raised:
            self.run_oracle("protocol_error")
        self.assertEqual(raised.exception.kind, "protocol_error")
        self.assertEqual(self.recorded_calls(), [["before", "boom", "after"]])
        metadata = json.loads(self.output.with_suffix(".reference-process.json").read_text())
        self.assertEqual(metadata["status"], "execution_error")
        self.assertEqual(metadata["subprocess_runs"], 1)
        self.assertEqual(metadata["attempts"][0]["returncode"], 0)
        self.assertFalse(metadata["isolation_used"])


if __name__ == "__main__":
    unittest.main()
