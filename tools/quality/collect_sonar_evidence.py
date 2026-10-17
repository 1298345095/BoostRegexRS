#!/usr/bin/env python3
"""Archive a commit's GitHub Sonar check and optional live PR API responses.

Collection success does not mean quality-gate success: summary.json retains the
server's conclusion. Optional GITHUB_TOKEN and SONAR_TOKEN environment variables
are sent only to their respective API hosts and are never written to evidence.
"""

import argparse
import datetime as dt
import json
import os
from pathlib import Path
import re
import urllib.error
import urllib.parse
import urllib.request


REPO = "1298345095/BoostRegexRS"
PROJECT = "1298345095_BoostRegexRS"
ORGANIZATION = "1298345095"
ROOT = Path(__file__).resolve().parents[2]
GITHUB_API = f"https://api.github.com/repos/{REPO}"
SONAR_API = "https://sonarcloud.io/api"


def fetch(url, token=None):
    headers = {"Accept": "application/json", "User-Agent": "BoostRegexRS-quality-evidence"}
    if token:
        headers["Authorization"] = "Bearer " + token
    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            body = response.read().decode("utf-8")
            status = response.status
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")
        status = error.code
    except urllib.error.URLError as error:
        return {"url": url, "status": None, "error": str(error.reason)}
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


def collect(commit, pull_request, output, github_only=False, inspect_access=False):
    output.mkdir(parents=True, exist_ok=True)
    github_token = os.environ.get("GITHUB_TOKEN")
    sonar_token = os.environ.get("SONAR_TOKEN")
    checks = fetch(f"{GITHUB_API}/commits/{commit}/check-runs?per_page=100", github_token)
    save(output, "github-check-runs.json", checks)
    if checks["status"] != 200:
        raise RuntimeError("GitHub checks could not be read; response was preserved")
    matching = [check for check in checks["payload"]["check_runs"]
                if check["name"] == "SonarCloud Code Analysis"]
    if not matching:
        raise RuntimeError("The commit has no SonarCloud Code Analysis check")
    check = max(matching, key=lambda item: item["id"])
    pages = annotations(check["id"], check["output"]["annotations_count"], github_token)
    save(output, "github-annotations.json", pages)
    queries = {
        "sonar-issues.json": ("issues/search", {"componentKeys": PROJECT, "pullRequest": pull_request,
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
        if github_only:
            sonar_statuses[filename] = "not_requested"
            continue
        response = fetch(f"{SONAR_API}/{endpoint}?{urllib.parse.urlencode(parameters)}", sonar_token)
        response["scope"] = "live_pr_unpinned"
        response["associated_commit_verified"] = False
        response["pull_request"] = pull_request
        save(output, filename, response)
        sonar_statuses[filename] = response["status"]
    summary = {
        "collected_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "repository": REPO, "commit": commit, "pull_request": pull_request,
        "check_id": check["id"], "check_status": check["status"],
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
        "meaning": "Archived server evidence; collecting a failed check never changes its conclusion.",
    }
    save(output, "summary.json", summary)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--pull-request", type=int, default=1)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--github-only", action="store_true", help="preserve GitHub evidence while SonarCloud is inaccessible")
    parser.add_argument("--inspect-access", action="store_true",
                        help="archive authentication validity, issue API metadata and reported rule definitions")
    args = parser.parse_args()
    if not re.fullmatch(r"[0-9a-f]{40}", args.commit) or args.pull_request < 1:
        parser.error("use a full lowercase commit SHA and a positive pull-request number")
    output = args.output or ROOT / "docs/research/assets/sonarcloud" / args.commit
    result = collect(args.commit, args.pull_request, output, args.github_only, args.inspect_access)
    print(json.dumps({"commit": result["commit"], "quality_gate_conclusion": result["quality_gate_conclusion"],
                      "annotations_complete": result["annotations_complete"], "output": str(output)}))


if __name__ == "__main__":
    main()
