#!/usr/bin/env python3
"""Replay the retained six-target evidence; do not run builds, tests or network requests."""

import hashlib
import io
import json
from pathlib import Path
import re
import subprocess
from zipfile import ZipFile


BASE = Path(__file__).resolve().parent
REPO = BASE.parents[4]
COMMIT = "c4a161c0650b4b5433f5c437692cde3f5cb42a4d"
TREE = "26265ca903614a2b32fe5e928d1a543b7dd036d1"
RUN_ID = 39086563173
TARGETS = {
    "x86_64-pc-windows-msvc": ("windows-2025", "windows"),
    "aarch64-pc-windows-msvc": ("windows-11-arm", "windows"),
    "x86_64-unknown-linux-gnu": ("ubuntu-24.04", "linux"),
    "aarch64-unknown-linux-gnu": ("ubuntu-24.04-arm", "linux"),
    "x86_64-apple-darwin": ("macos-15-intel", "macos"),
    "aarch64-apple-darwin": ("macos-15", "macos"),
}
COMMANDS = (
    "git-commit", "git-tree", "rustc-version", "cargo-version",
    "compile-host-probe", "run-host-probe", "format", "clippy", "tests",
    "doctests", "documentation",
)
INPUT_SCOPE = (
    "tools/icu-probe/primary/rust/Cargo.toml",
    "tools/icu-probe/primary/rust/Cargo.lock",
    "tools/ci/native_rust.py", "tools/ci/host_probe.rs",
    "tools/icu-probe/primary/rust/src",
    "tools/icu-probe/primary/rust/tests", "tools/icu-probe/primary/data",
)
TEST_RESULT = re.compile(
    r"^test result: (ok|FAILED)\. (\d+) passed; (\d+) failed; (\d+) ignored; "
    r"(\d+) measured; (\d+) filtered out;.*$", re.MULTILINE)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def verify_bytes(body, record, label):
    require(len(body) == record["bytes"], f"Byte count differs: {label}")
    require(hashlib.sha256(body).hexdigest() == record["sha256"],
            f"SHA-256 differs: {label}")


def git(*arguments, input_bytes=None):
    return subprocess.run(
        ["git", *arguments], cwd=REPO, input=input_bytes,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        check=True, timeout=20).stdout


def source_blobs():
    require(git("rev-parse", COMMIT + "^{tree}").decode().strip() == TREE,
            "The fixed commit does not identify the recorded tree")
    names = git("ls-tree", "-r", "--name-only", "-z", COMMIT, "--", *INPUT_SCOPE)
    paths = [name.decode("utf-8") for name in names.split(b"\0") if name]
    require(len(paths) == len(set(paths)) == 601, "The recorded input scope is not 601 files")
    request = "".join(f"{COMMIT}:{path}\n" for path in paths).encode("utf-8")
    response = io.BytesIO(git("cat-file", "--batch", input_bytes=request))
    result = {}
    for path in paths:
        header = response.readline().split()
        require(len(header) == 3 and header[1] == b"blob", f"Missing Git blob: {path}")
        size = int(header[2])
        result[path] = response.read(size)
        require(len(result[path]) == size and response.read(1) == b"\n",
                f"Incomplete Git blob response: {path}")
    require(response.read() == b"", "Unexpected trailing Git batch output")
    return result


def archive_members(record):
    target = record["target"]
    path = BASE / record["archive"]
    require(record["archive"] == target + ".zip", f"Unexpected archive name: {target}")
    verify_bytes(path.read_bytes(), record, path.name)
    metadata = record["github_artifact"]
    require(metadata["digest"] == "sha256:" + record["sha256"]
            and metadata["size_in_bytes"] == record["bytes"],
            f"GitHub artifact identity differs: {target}")
    require(metadata["workflow_run"]["id"] == RUN_ID
            and metadata["workflow_run"]["head_sha"] == COMMIT,
            f"GitHub artifact belongs to another run: {target}")
    expected = {f"{target}/summary.json"} | {
        f"{target}/{name}.{suffix}" for name in COMMANDS for suffix in ("json", "stdout", "stderr")}
    members = record["members"]
    require(len(members) == 34 and {item["path"] for item in members} == expected,
            f"The member manifest differs: {target}")
    with ZipFile(path) as archive:
        require(len(archive.namelist()) == 34 and set(archive.namelist()) == expected,
                f"The archive members differ: {target}")
        require(archive.testzip() is None, f"ZIP CRC failure: {target}")
        result = {}
        for item in members:
            body = archive.read(item["path"])
            verify_bytes(body, item, item["path"])
            result[item["path"].removeprefix(target + "/")] = body
    return result


def test_counts(body, expected, label):
    results = TEST_RESULT.findall(body.decode("utf-8"))
    require(len(results) == len(expected), f"Test harness count differs: {label}")
    for row, passed in zip(results, expected):
        require(row[0] == "ok" and tuple(map(int, row[1:])) == (passed, 0, 0, 0, 0),
                f"Test result differs: {label}: {row}")


def verify_execution(target, members):
    summary = json.loads(members["summary.json"])
    require(summary["commit"] == COMMIT and summary["tree"] == TREE
            and summary["target"] == target and summary["status"] == "passed",
            f"Run identity or status differs: {target}")
    require(summary["full_library_platform_acceptance"] == "not_established_by_this_workflow",
            f"The acceptance scope changed: {target}")
    records = [json.loads(members[name + ".json"]) for name in COMMANDS]
    require(records == summary["commands"]
            and all(item["returncode"] == 0 and item["error"] is None for item in records),
            f"A recorded command did not succeed: {target}")
    for name, expected in (("git-commit", COMMIT), ("git-tree", TREE)):
        require(members[name + ".stdout"].decode().strip() == expected,
                f"Recorded Git output differs: {target}/{name}")
    compiler = members["rustc-version.stdout"].decode().splitlines()
    require(compiler == summary["compiler"].splitlines()
            and f"host: {target}" in compiler and "release: 1.99.1" in compiler
            and "commit-hash: 58cf8f9c35b355199727627d07ae34a4e2846d67" in compiler
            and "LLVM version: 23.1.1" in compiler,
            f"Recorded compiler differs: {target}")
    host = {"architecture": target.split("-")[0], "os": TARGETS[target][1], "pointer_bits": 64}
    require(json.loads(members["run-host-probe.stdout"]) == summary["executed_host_probe"] == host,
            f"The executed native host differs: {target}")
    github = summary["environment"]["github"]
    require(github["GITHUB_RUN_ID"] == str(RUN_ID) and github["GITHUB_SHA"] == COMMIT
            and github["GITHUB_RUN_ATTEMPT"] == "1",
            f"The recorded GitHub environment differs: {target}")
    if TARGETS[target][1] == "linux":
        require(summary["environment"]["libc"] == ["glibc", "2.39"], f"The libc differs: {target}")
    require(summary["versions"] == {"icu": "77.1", "unicode": "16.0.0", "cldr": "47"},
            f"The recorded data versions differ: {target}")
    test_counts(members["tests.stdout"], [5, 0, 3, 1, 6, 7, 9], target)
    test_counts(members["doctests.stdout"], [0], target + "/doctests")
    return summary


def verify_inputs(summary, recorded, blobs):
    target = summary["target"]
    inputs = summary["inputs"]
    require(len(inputs) == 601 and {item["path"] for item in inputs} == set(blobs),
            f"Source/data input coverage differs: {target}")
    crlf = set(recorded["crlf_checkout_files"])
    expected_count = 36 if TARGETS[target][1] == "windows" else 0
    require(len(crlf) == len(recorded["crlf_checkout_files"]) == expected_count,
            f"The retained CRLF path count differs: {target}")
    require(crlf <= set(blobs), f"Unknown CRLF input paths: {target}")
    for item in inputs:
        body = blobs[item["path"]]
        if item["path"] in crlf:
            body.decode("utf-8")
            require(b"\0" not in body and b"\r\n" not in body and b"\n" in body,
                    f"The recorded CRLF source is not LF text: {item['path']}")
            body = body.replace(b"\n", b"\r\n")
        verify_bytes(body, item, target + "/" + item["path"])
    expected = {"exact_git_blob_files": 601 - len(crlf), "tests_passed": 31,
                "tests_failed": 0, "tests_ignored": 0, "commands_passed": 11}
    require(all(recorded[key] == value for key, value in expected.items()),
            f"Prior input-verification counts differ: {target}")
    print(f"{target}: 34 members; 31 tests; 0 doctests; 11 commands; "
          f"{601 - len(crlf)} exact inputs; {len(crlf)} listed LF-to-CRLF inputs")


def main():
    artifacts = read_json(BASE / "artifact-source.json")
    retained = read_json(BASE / "input-verification.json")
    jobs = read_json(BASE / "github-jobs.json")
    require(artifacts["run_id"] == RUN_ID and artifacts["commit"] == retained["commit"] == COMMIT,
            "The retained metadata identifies another run")
    require(retained["full_library_platform_acceptance"] == "not_established_by_this_workflow",
            "The retained acceptance scope changed")
    records = {item["target"]: item for item in artifacts["artifacts"]}
    platforms = {item["target"]: item for item in retained["platforms"]}
    require(len(artifacts["artifacts"]) == len(retained["platforms"]) == 6
            and set(records) == set(platforms) == set(TARGETS), "The six-target set differs")
    require(jobs["total_count"] == len(jobs["jobs"]) == 6, "The native job count differs")
    require({job["name"] for job in jobs["jobs"]}
            == {f"{target} on {runner}" for target, (runner, _) in TARGETS.items()},
            "The recorded native jobs differ")
    for job in jobs["jobs"]:
        require(job["run_id"] == RUN_ID and job["head_sha"] == COMMIT
                and job["status"] == "completed" and job["conclusion"] == "success",
                f"A native job did not succeed: {job['name']}")
    blobs = source_blobs()
    print(f"Git commit {COMMIT}; tree {TREE}; 601 scoped source/data blobs")
    for target in sorted(TARGETS):
        summary = verify_execution(target, archive_members(records[target]))
        verify_inputs(summary, platforms[target], blobs)
    print("Six retained native research-crate observations verified; no builds or tests were rerun.")


if __name__ == "__main__":
    main()
