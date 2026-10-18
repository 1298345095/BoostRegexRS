#!/usr/bin/env python3
"""Archive a commit's GitHub Sonar check and optional live PR API responses.

Collection success does not mean quality-gate success: summary.json retains the
server's conclusion. Optional GITHUB_TOKEN and SONAR_TOKEN environment variables
are sent only to their respective API hosts and are never written to evidence.
"""

import argparse
import datetime as dt
import json
import math
import os
from pathlib import Path
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request


REPO = "1298345095/BoostRegexRS"
PROJECT = "1298345095_BoostRegexRS"
ORGANIZATION = "1298345095"
ROOT = Path(__file__).resolve().parents[2]
GITHUB_API = f"https://api.github.com/repos/{REPO}"
SONAR_API = "https://sonarcloud.io/api"
ISSUES_FILE = "sonar-issues.json"


def origin(url):
    """Include the effective port when comparing an HTTP request's authority."""
    parsed = urllib.parse.urlsplit(url)
    port = parsed.port
    if port is None:
        port = {"http": 80, "https": 443}.get(parsed.scheme)
    return parsed.scheme, parsed.hostname, port


class ScopedRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Keep bearer credentials only when a redirect preserves the origin."""

    def redirect_request(self, request, response, code, message, headers, new_url):
        redirected = super().redirect_request(request, response, code, message, headers, new_url)
        if redirected is not None and origin(request.full_url) != origin(new_url):
            redirected.remove_header("Authorization")
        return redirected


def fetch(url, token=None, *, timeout=30):
    headers = {"Accept": "application/json", "User-Agent": "BoostRegexRS-quality-evidence"}
    if token:
        headers["Authorization"] = "Bearer " + token
    request = urllib.request.Request(url, headers=headers)
    opener = urllib.request.build_opener(ScopedRedirectHandler())
    try:
        with opener.open(request, timeout=timeout) as response:
            body = response.read().decode("utf-8")
            status = response.status
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")
        status = error.code
    except urllib.error.URLError as error:
        return {"url": url, "status": None, "error": str(error.reason)}
    except TimeoutError as error:
        return {"url": url, "status": None, "error": str(error)}
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return {"url": url, "status": status, "body": body}
    return {"url": url, "status": status, "payload": payload}


def save(directory, name, value):
    (directory / name).write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def annotations(check_id, count, token):
    pages = []
    for page in range(1, (count + 99) // 100 + 1):
        url = f"{GITHUB_API}/check-runs/{check_id}/annotations?per_page=100&page={page}"
        pages.append(fetch(url, token))
    return pages


def observe_check(commit, token, output, trace, remaining):
    """Preserve one response before selecting the newest check for this SHA."""
    response = fetch(f"{GITHUB_API}/commits/{commit}/check-runs?per_page=100", token,
                     timeout=min(30, remaining))
    index = len(trace["observations"]) + 1
    filename = "github-check-runs.json" if index == 1 else f"github-check-runs-{index:03d}.json"
    save(output, filename, response)
    trace["observations"].append({"file": filename,
                                  "received_utc": dt.datetime.now(dt.timezone.utc).isoformat()})
    if response["status"] != 200:
        raise RuntimeError("GitHub checks could not be read; response was preserved")
    matching = [check for check in response["payload"]["check_runs"]
                if check["name"] == "SonarCloud Code Analysis" and check["head_sha"] == commit]
    check = max(matching, key=lambda item: item["id"], default=None)
    trace["selected_check"] = ({key: check.get(key) for key in
                                ("id", "head_sha", "status", "conclusion", "started_at", "completed_at")}
                               if check is not None else None)
    return check, filename


def completed_check(commit, token, output, timeout):
    """Wait for the newest check for this SHA, preserving every observation."""
    started = time.monotonic()
    deadline = started + timeout
    trace = {"commit": commit, "timeout_seconds": timeout, "poll_interval_seconds": 5,
             "started_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
             "status": "waiting", "observations": []}
    try:
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError("Sonar check did not complete within the declared wait deadline")
            check, filename = observe_check(commit, token, output, trace, remaining)
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError("Sonar check did not complete within the declared wait deadline")
            if check is not None and check["status"] == "completed":
                trace["status"] = "completed"
                return check, trace
            save(output, "github-check-wait.json", trace)
            status = check["status"] if check is not None else "not created"
            print(f"Sonar check {status}; {remaining:.1f}s left; preserved {filename}",
                  file=sys.stderr, flush=True)
            time.sleep(min(5, remaining))
    except Exception as error:
        trace["status"] = "timeout" if isinstance(error, TimeoutError) else "error"
        trace["error"] = f"{type(error).__name__}: {error}"
        raise
    finally:
        trace["finished_utc"] = dt.datetime.now(dt.timezone.utc).isoformat()
        trace["elapsed_seconds"] = time.monotonic() - started
        save(output, "github-check-wait.json", trace)


def sonar_response(output, filename, endpoint, parameters, token, pull_request, scope="live_pr_unpinned"):
    started = dt.datetime.now(dt.timezone.utc).isoformat()
    response = fetch(f"{SONAR_API}/{endpoint}?{urllib.parse.urlencode(parameters)}", token)
    response.update({"scope": scope, "associated_commit_verified": False, "pull_request": pull_request,
                     "request_started_utc": started,
                     "received_utc": dt.datetime.now(dt.timezone.utc).isoformat()})
    save(output, filename, response)
    return response["status"]


def analysis_metadata(output, token, pull_request, phase, github_only):
    """Observe documented Browse-level APIs; neither query pins an issue read."""
    queries = (("pull-requests", "project_pull_requests/list", {"project": PROJECT}),
               ("ce-component", "ce/component", {"component": PROJECT}))
    statuses = {}
    for name, endpoint, parameters in queries:
        filename = f"sonar-{name}-{phase}.json"
        statuses[filename] = ("not_requested" if github_only else
                              sonar_response(output, filename, endpoint, parameters, token,
                                             pull_request, scope="live_project_metadata"))
    return statuses


def collect(commit, pull_request, output, github_only=False, inspect_access=False, check_timeout=150):
    if check_timeout <= 0 or not math.isfinite(check_timeout):
        raise ValueError("The check wait deadline must be finite and positive")
    output.mkdir(parents=True, exist_ok=False)
    github_token = os.environ.get("GITHUB_TOKEN")
    sonar_token = os.environ.get("SONAR_TOKEN")
    check, wait = completed_check(commit, github_token, output, check_timeout)
    pages = annotations(check["id"], check["output"]["annotations_count"], github_token)
    save(output, "github-annotations.json", pages)
    queries = {
        ISSUES_FILE: ("issues/search", {"componentKeys": PROJECT, "pullRequest": pull_request,
                                                "ps": 500, "resolved": "false"}),
        "sonar-quality-gate.json": ("qualitygates/project_status", {"projectKey": PROJECT,
                                                                     "pullRequest": pull_request}),
    }
    if inspect_access:
        # This endpoint returns a validity boolean, not a token or user profile.
        # Read access to a public project does not imply issue-management access.
        queries["sonar-authentication.json"] = ("authentication/validate", {})
        queries["sonar-web-api.json"] = ("webservices/list", {})
        for rule in ("S2083", "S8701", "S8705", "S8707"):
            queries[f"sonar-rule-{rule}.json"] = (
                "rules/show", {"key": "pythonsecurity:" + rule, "organization": ORGANIZATION}
            )
    sonar_statuses = {}
    for filename, (endpoint, parameters) in queries.items():
        if filename == ISSUES_FILE:
            sonar_statuses.update(analysis_metadata(output, sonar_token, pull_request, "before", github_only))
        if github_only:
            sonar_statuses[filename] = "not_requested"
        else:
            sonar_statuses[filename] = sonar_response(output, filename, endpoint, parameters, sonar_token, pull_request)
        if filename == ISSUES_FILE:
            sonar_statuses.update(analysis_metadata(output, sonar_token, pull_request, "after", github_only))
    summary = {
        "collected_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "repository": REPO, "commit": commit, "pull_request": pull_request,
        "check_id": check["id"], "check_status": check["status"],
        "check_completed_utc": check.get("completed_at"),
        "check_wait": wait,
        "quality_gate_conclusion": check["conclusion"], "check_output": check["output"],
        "annotation_count": check["output"]["annotations_count"],
        "annotations_complete": (all(page["status"] == 200 for page in pages)
                                 and sum(len(page["payload"]) for page in pages)
                                 == check["output"]["annotations_count"]),
        "sonar_api_statuses": sonar_statuses,
        "sonar_token_supplied": bool(sonar_token),
        "sonar_access_inspection_requested": inspect_access,
        "sonar_evidence_scope": "live_pr_unpinned",
        "sonar_associated_commit_verified": False,
        "sonar_analysis_binding": ("not_requested" if github_only else "not_established"),
        "sonar_analysis_binding_note": "Live PR reads are bracketed by raw PR and project task metadata; "
                                       "check timing and per-issue lastChangeAnalysisUuid do not bind an immutable analysis.",
        "meaning": "Archived server evidence; collecting a failed check never changes its conclusion.",
    }
    save(output, "summary.json", summary)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--pull-request", type=int, default=1)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--check-timeout", type=int, default=150,
                        help="Positive seconds to wait for this commit's newest Sonar check to complete")
    parser.add_argument("--github-only", action="store_true", help="preserve GitHub evidence while SonarCloud is inaccessible")
    parser.add_argument("--inspect-access", action="store_true",
                        help="archive authentication validity, issue API metadata and reported rule definitions")
    args = parser.parse_args()
    if not re.fullmatch(r"[0-9a-f]{40}", args.commit) or args.pull_request < 1:
        parser.error("use a full lowercase commit SHA and a positive pull-request number")
    if args.check_timeout <= 0:
        parser.error("--check-timeout must be positive")
    output = args.output or ROOT / "docs/research/assets/sonarcloud" / args.commit
    result = collect(args.commit, args.pull_request, output, args.github_only, args.inspect_access, args.check_timeout)
    print(json.dumps({"commit": result["commit"], "quality_gate_conclusion": result["quality_gate_conclusion"],
                      "annotations_complete": result["annotations_complete"], "output": str(output)}))


if __name__ == "__main__":
    main()
