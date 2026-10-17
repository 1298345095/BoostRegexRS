#!/usr/bin/env python3
"""Expose exact staged Git objects to an authenticated GitHub API client.

Used when the workspace has no authenticated git/gh transport. This script does
not authenticate or send anything. The caller uploads blobs, creates a tree and
commit, then advances the work branch with the observed parent SHA as its lease.
"""

import argparse
import base64
import json
import subprocess


def git(*arguments):
    return subprocess.check_output(["git", *arguments])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--path", help="Return one exact staged blob and its mode")
    args = parser.parse_args()
    if args.path:
        entry = git("ls-files", "--stage", "-z", "--", args.path).split(b"\0")[0]
        metadata, path = entry.split(b"\t", 1)
        mode, digest, stage = metadata.decode().split()
        if stage != "0":
            raise RuntimeError("Resolve the staged merge conflict before publishing")
        content = git("cat-file", "blob", digest)
        print(json.dumps({"path": path.decode(), "mode": mode, "sha": digest,
                          "content": base64.b64encode(content).decode(), "encoding": "base64"}))
    else:
        changes = git("diff", "--cached", "--name-only", "-z").split(b"\0")
        print(json.dumps({"parent": git("rev-parse", "HEAD").decode().strip(),
                          "tree": git("write-tree").decode().strip(),
                          "paths": [path.decode() for path in changes if path]}))


if __name__ == "__main__":
    main()
