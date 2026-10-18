"""Check completion and live-analysis evidence remain separate observations."""

import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from urllib.parse import urlsplit

import collect_sonar_evidence as collector


COMMIT = "a" * 40


def check(identifier, status, *, commit=COMMIT, name="SonarCloud Code Analysis"):
    return {"id": identifier, "head_sha": commit, "name": name, "status": status,
            "conclusion": "failure" if status == "completed" else None,
            "started_at": "2026-10-18T00:00:00Z",
            "completed_at": "2026-10-18T00:01:00Z" if status == "completed" else None,
            "output": {"annotations_count": 0}}


def check_response(*checks):
    return {"url": "https://api.github.com/synthetic", "status": 200,
            "payload": {"check_runs": list(checks)}}


class Clock:
    def __init__(self):
        self.elapsed = 0
        self.sleeps = []

    def monotonic(self):
        return self.elapsed

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.elapsed += seconds


class SonarCollectionTests(unittest.TestCase):
    def setUp(self):
        temporary = TemporaryDirectory(dir=collector.ROOT.parent)
        self.addCleanup(temporary.cleanup)
        self.output = Path(temporary.name) / "observation"
        self.clock = Clock()
        for patcher in (patch.object(collector.time, "monotonic", self.clock.monotonic),
                        patch.object(collector.time, "sleep", self.clock.sleep),
                        patch.object(collector.sys, "stderr", io.StringIO()),
                        patch.dict(collector.os.environ, {}, clear=True)):
            patcher.start()
            self.addCleanup(patcher.stop)

    def read(self, name):
        return json.loads((self.output / name).read_text(encoding="utf-8"))

    def test_waits_for_newest_matching_check_and_preserves_failed_conclusion(self):
        observations = [check_response(check(999, "completed", commit="b" * 40),
                                       check(1000, "completed", name="Other check")),
                        check_response(check(42, "in_progress"), check(40, "completed")),
                        check_response(check(42, "completed"), check(40, "completed"))]
        with patch.object(collector, "fetch", side_effect=observations) as fetch:
            result = collector.collect(COMMIT, 1, self.output, github_only=True)
        self.assertEqual(fetch.call_count, 3)
        self.assertTrue(all(call.args[0].startswith(collector.GITHUB_API) for call in fetch.call_args_list))
        self.assertEqual(self.clock.sleeps, [5, 5])
        self.assertEqual(result["check_id"], 42)
        self.assertEqual(result["quality_gate_conclusion"], "failure")
        self.assertEqual(result["check_completed_utc"], "2026-10-18T00:01:00Z")
        self.assertEqual(result["sonar_analysis_binding"], "not_requested")
        self.assertEqual(set(result["sonar_api_statuses"].values()), {"not_requested"})
        wait = self.read("github-check-wait.json")
        self.assertEqual(wait["status"], "completed")
        self.assertEqual(wait["elapsed_seconds"], 10)
        self.assertEqual(result["check_wait"], wait)
        expected_files = ["github-check-runs.json", "github-check-runs-002.json", "github-check-runs-003.json"]
        self.assertEqual([item["file"] for item in wait["observations"]], expected_files)
        for filename, original in zip(expected_files, observations):
            self.assertEqual(self.read(filename), original)

    def test_deadline_retains_pending_checks_and_prevents_sonar_reads(self):
        pending = check_response(check(42, "in_progress"))
        with patch.object(collector, "fetch", return_value=pending) as fetch:
            with self.assertRaisesRegex(TimeoutError, "declared wait deadline"):
                collector.collect(COMMIT, 1, self.output, check_timeout=7)
        self.assertEqual([call.kwargs["timeout"] for call in fetch.call_args_list], [7, 2])
        self.assertTrue(all(call.args[0].startswith(collector.GITHUB_API) for call in fetch.call_args_list))
        self.assertEqual(self.clock.sleeps, [5, 2])
        self.assertEqual(self.read("github-check-wait.json")["status"], "timeout")
        self.assertEqual(self.read("github-check-runs-002.json"), pending)
        self.assertFalse((self.output / "summary.json").exists())

    def test_completed_response_after_deadline_is_evidence_but_not_acceptance(self):
        completed = check_response(check(42, "completed"))

        def late_response(*args, **kwargs):
            self.clock.elapsed += 8
            return completed

        with patch.object(collector, "fetch", side_effect=late_response) as fetch:
            with self.assertRaises(TimeoutError):
                collector.collect(COMMIT, 1, self.output, check_timeout=7)
        self.assertEqual(fetch.call_args.kwargs["timeout"], 7)
        self.assertEqual(self.read("github-check-runs.json"), completed)
        self.assertEqual(self.read("github-check-wait.json")["status"], "timeout")
        self.assertFalse((self.output / "summary.json").exists())

    def test_unusable_wait_deadlines_do_not_create_evidence_or_contact_servers(self):
        with patch.object(collector, "fetch") as fetch:
            for deadline in (0, -1, float("nan"), float("inf"), -float("inf")):
                with self.subTest(deadline=deadline), self.assertRaises(ValueError):
                    collector.collect(COMMIT, 1, self.output, check_timeout=deadline)
                self.assertFalse(self.output.exists())
        fetch.assert_not_called()

    def test_issue_read_is_bracketed_without_inventing_analysis_identity(self):
        endpoints = []
        responses = iter([
            {"status": 200, "payload": {"pullRequests": [{"key": "1", "commit": {"sha": COMMIT}}]}},
            {"status": 200, "payload": {"current": {"id": "task-before", "analysisId": "analysis-before"}}},
            {"status": 200, "payload": {"issues": [{"key": "synthetic", "lastChangeAnalysisUuid": "analysis-before"}]}},
            {"status": 403, "body": "Synthetic metadata denial"},
            {"status": 200, "payload": {"current": {"id": "task-after", "analysisId": "analysis-after"}}},
            {"status": 200, "payload": {"projectStatus": {"status": "ERROR"}}},
        ])

        def respond(url, token=None, **kwargs):
            if url.startswith(collector.GITHUB_API):
                return check_response(check(42, "completed"))
            endpoints.append(urlsplit(url).path)
            return {"url": url, **next(responses)}

        with patch.object(collector, "fetch", side_effect=respond):
            result = collector.collect(COMMIT, 1, self.output)
        self.assertEqual(endpoints, ["/api/project_pull_requests/list", "/api/ce/component", "/api/issues/search",
                                     "/api/project_pull_requests/list", "/api/ce/component", "/api/qualitygates/project_status"])
        self.assertEqual(result["sonar_api_statuses"]["sonar-pull-requests-after.json"], 403)
        self.assertEqual(self.read("sonar-pull-requests-after.json")["body"], "Synthetic metadata denial")
        self.assertEqual(self.read("sonar-ce-component-before.json")["payload"]["current"]["analysisId"], "analysis-before")
        self.assertEqual(self.read("sonar-ce-component-after.json")["payload"]["current"]["analysisId"], "analysis-after")
        self.assertEqual(self.read("sonar-quality-gate.json")["payload"]["projectStatus"]["status"], "ERROR")
        self.assertFalse(result["sonar_associated_commit_verified"])
        self.assertEqual(result["sonar_analysis_binding"], "not_established")
        self.assertEqual(result["quality_gate_conclusion"], "failure")
        for filename in result["sonar_api_statuses"]:
            response = self.read(filename)
            self.assertFalse(response["associated_commit_verified"])
            self.assertIn("request_started_utc", response)
            self.assertIn("received_utc", response)

    def test_socket_deadline_is_preserved_as_unavailable_evidence(self):
        with patch.object(collector.urllib.request, "build_opener") as build_opener:
            build_opener.return_value.open.side_effect = TimeoutError("Synthetic socket deadline")
            result = collector.fetch("https://api.github.com/synthetic", timeout=2)
        self.assertIsNone(result["status"])
        self.assertEqual(result["error"], "Synthetic socket deadline")
        self.assertEqual(build_opener.return_value.open.call_args.kwargs["timeout"], 2)


if __name__ == "__main__":
    unittest.main()
