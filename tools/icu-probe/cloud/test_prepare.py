"""Regression tests for bounded native build commands and preserved evidence."""

import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest

from prepare import REPO, run_logged


class CommandDeadlineTests(unittest.TestCase):
    def setUp(self):
        temporary_root = REPO / "target" / "test-command-deadlines"
        temporary_root.mkdir(parents=True, exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(dir=temporary_root)
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.log = self.directory / "command.log"

    def record(self):
        return json.loads(self.log.with_suffix(".process.json").read_text())

    def test_deadline_and_grace_must_be_finite_and_positive_before_launch(self):
        for parameter in ("timeout", "terminate_grace"):
            for value in (float("nan"), float("inf"), float("-inf"), 0, -0.5):
                with self.subTest(parameter=parameter, value=value):
                    with self.assertRaisesRegex(ValueError, "finite and positive"):
                        run_logged([str(self.directory / "missing-program")], cwd=self.directory,
                                   log=self.log, **{parameter: value})
                    self.assertEqual(list(self.directory.iterdir()), [])

    def test_success_preserves_both_streams_and_exit_status(self):
        input_path = self.directory / "input.txt"
        input_path.write_text("output\n")
        command = [sys.executable, "-c", "import sys; sys.stdout.write(sys.stdin.read()); print('error', file=sys.stderr)"]
        run_logged(command, cwd=self.directory, log=self.log, timeout=5, input_path=input_path)
        self.assertEqual(self.log.read_text(), "output\n")
        self.assertEqual(self.log.with_suffix(".stderr.log").read_text(), "error\n")
        record = self.record()
        self.assertEqual(record["command"], command)
        self.assertEqual(record["stdin"], str(input_path))
        self.assertEqual(record["returncode"], 0)
        self.assertFalse(record["timed_out"])

    def test_failure_is_preserved_and_raised(self):
        command = [sys.executable, "-c", "import sys; print('failed', file=sys.stderr); sys.exit(7)"]
        with self.assertRaisesRegex(RuntimeError, "7"):
            run_logged(command, cwd=self.directory, log=self.log, timeout=5)
        self.assertEqual(self.record()["returncode"], 7)
        self.assertEqual(self.log.with_suffix(".stderr.log").read_text(), "failed\n")

    @unittest.skipUnless(sys.platform.startswith("linux"), "Linux /proc verifies descendant termination")
    def test_timeout_kills_descendants_that_ignore_term(self):
        child = "import signal,time; signal.signal(signal.SIGTERM, signal.SIG_IGN); time.sleep(60)"
        parent = (
            "import subprocess,sys,time; "
            f"child=subprocess.Popen([sys.executable,'-c',{child!r}]); "
            "print(child.pid,flush=True); time.sleep(60)"
        )
        with self.assertRaisesRegex(RuntimeError, "timed out"):
            run_logged([sys.executable, "-c", parent], cwd=self.directory, log=self.log,
                       timeout=0.5, terminate_grace=0.2)
        record = self.record()
        self.assertTrue(record["timed_out"])
        self.assertEqual(record["exit_status"], 124)
        child_pid = int(self.log.read_text().strip())
        state = Path(f"/proc/{child_pid}/stat")
        deadline = time.monotonic() + 2
        while state.exists() and state.read_text().split()[2] != "Z" and time.monotonic() < deadline:
            time.sleep(0.01)
        self.assertTrue(not state.exists() or state.read_text().split()[2] == "Z")

    @unittest.skipUnless(sys.platform.startswith("linux"), "Linux /proc verifies descendant termination")
    def test_external_term_stops_controller_and_descendants(self):
        pid_path = self.directory / "descendant.pid"
        child = ("import os,signal,time; from pathlib import Path; "
                 "signal.signal(signal.SIGTERM,signal.SIG_IGN); "
                 f"Path({str(pid_path)!r}).write_text(str(os.getpid())); time.sleep(60)")
        parent = f"import subprocess,sys,time; subprocess.Popen([sys.executable,'-c',{child!r}]); time.sleep(60)"
        controller = ("import sys; from pathlib import Path; "
                      f"sys.path.insert(0,{str(Path(__file__).parent)!r}); from prepare import run_logged; "
                      f"run_logged([sys.executable,'-c',{parent!r}],cwd=Path({str(self.directory)!r}),"
                      f"log=Path({str(self.log)!r}),timeout=60)")
        process = subprocess.Popen([sys.executable, "-B", "-c", controller],
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
        try:
            deadline = time.monotonic() + 3
            while not pid_path.exists() and time.monotonic() < deadline:
                time.sleep(0.01)
            self.assertTrue(pid_path.exists(), "The descendant must actually start before cancellation")
            process.send_signal(signal.SIGTERM)
            process.communicate(timeout=5)
            self.assertEqual(process.returncode, 143)
            record = self.record()
            self.assertEqual(record["interrupted_by_signal"], signal.SIGTERM)
            self.assertEqual(record["exit_status"], 143)
            self.assertFalse(record["timed_out"])
            state = Path(f"/proc/{pid_path.read_text()}/stat")
            deadline = time.monotonic() + 2
            while state.exists() and state.read_text().split()[2] != "Z" and time.monotonic() < deadline:
                time.sleep(0.01)
            self.assertTrue(not state.exists() or state.read_text().split()[2] == "Z")
        finally:
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGKILL)
                process.communicate(timeout=5)
            if pid_path.exists():
                try:
                    os.kill(int(pid_path.read_text()), signal.SIGKILL)
                except ProcessLookupError:
                    pass

    @unittest.skipUnless(sys.platform.startswith("linux"), "Linux /proc verifies worker termination")
    def test_external_term_stops_parallel_download_workers(self):
        controller = f"""
import concurrent.futures
from pathlib import Path
import sys
sys.path.insert(0, {str(Path(__file__).parent)!r})
from prepare import install_cancellation_handler, run_logged
directory = Path({str(self.directory)!r})
install_cancellation_handler()
def worker(index):
    child = "import os,signal,time; from pathlib import Path; signal.signal(signal.SIGTERM,signal.SIG_IGN); Path(" + repr(str(directory / (str(index) + '.pid'))) + ").write_text(str(os.getpid())); time.sleep(60)"
    run_logged([sys.executable, '-c', child], cwd=directory, log=directory / (str(index) + '.log'), timeout=60)
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
    list(pool.map(worker, (0, 1)))
"""
        process = subprocess.Popen([sys.executable, "-B", "-c", controller],
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
        pid_paths = [self.directory / f"{index}.pid" for index in range(2)]
        try:
            deadline = time.monotonic() + 3
            while not all(path.exists() for path in pid_paths) and time.monotonic() < deadline:
                time.sleep(0.01)
            self.assertTrue(all(path.exists() for path in pid_paths))
            process.send_signal(signal.SIGTERM)
            process.communicate(timeout=5)
            self.assertEqual(process.returncode, 143)
            for index, pid_path in enumerate(pid_paths):
                record = json.loads((self.directory / f"{index}.process.json").read_text())
                self.assertEqual(record["exit_status"], 143)
                self.assertEqual(record["interrupted_by_signal"], signal.SIGTERM)
                self.assertFalse(Path(f"/proc/{pid_path.read_text()}").exists())
        finally:
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGKILL)
                process.communicate(timeout=5)
            for pid_path in pid_paths:
                if pid_path.exists():
                    try:
                        os.kill(int(pid_path.read_text()), signal.SIGKILL)
                    except ProcessLookupError:
                        pass

    @unittest.skipUnless(sys.platform.startswith("linux"), "POSIX launch-boundary cancellation")
    def test_cancellation_during_launch_reaches_registration_and_cleanup(self):
        child_pid = self.directory / "launch-child.pid"
        grandchild_pid = self.directory / "launch-grandchild.pid"
        child = ("import os,signal,time; from pathlib import Path; "
                 "signal.signal(signal.SIGTERM,signal.SIG_IGN); "
                 f"Path({str(grandchild_pid)!r}).write_text(str(os.getpid())); time.sleep(60)")
        parent = f"import subprocess,sys,time; subprocess.Popen([sys.executable,'-c',{child!r}]); time.sleep(60)"
        controller = f"""
import os, signal, sys, time
from pathlib import Path
sys.path.insert(0, {str(Path(__file__).parent)!r})
import prepare
real_popen = prepare.subprocess.Popen
def interrupted_launch(*args, **kwargs):
    process = real_popen(*args, **kwargs)
    Path({str(child_pid)!r}).write_text(str(process.pid))
    deadline = time.monotonic() + 3
    while not Path({str(grandchild_pid)!r}).exists() and time.monotonic() < deadline:
        time.sleep(0.01)
    os.kill(os.getpid(), signal.SIGTERM)
    return process
prepare.subprocess.Popen = interrupted_launch
prepare.run_logged([sys.executable, '-c', {parent!r}], cwd=Path({str(self.directory)!r}),
                   log=Path({str(self.log)!r}), timeout=60)
"""
        process = subprocess.Popen([sys.executable, "-B", "-c", controller],
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
        try:
            process.communicate(timeout=6)
            self.assertEqual(process.returncode, 143)
            self.assertTrue(grandchild_pid.exists())
            self.assertEqual(self.record()["exit_status"], 143)
            for pid_path in (child_pid, grandchild_pid):
                state = Path(f"/proc/{pid_path.read_text()}/stat")
                deadline = time.monotonic() + 2
                while state.exists() and state.read_text().split()[2] != "Z" and time.monotonic() < deadline:
                    time.sleep(0.01)
                self.assertTrue(not state.exists() or state.read_text().split()[2] == "Z")
        finally:
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGKILL)
                process.communicate(timeout=5)
            if child_pid.exists():
                try:
                    os.killpg(int(child_pid.read_text()), signal.SIGKILL)
                except ProcessLookupError:
                    pass


if __name__ == "__main__":
    unittest.main()
