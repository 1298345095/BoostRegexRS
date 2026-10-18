#!/usr/bin/env python3
"""Expose exact staged Git objects to an authenticated GitHub API client.

Used when the workspace has no authenticated git/gh transport. This script does
not authenticate or send anything. The caller uploads blobs, creates a tree and
commit, then advances the work branch with the observed parent SHA as its lease.
"""

import argparse
import base64
import json
import os
import subprocess


def git(*arguments):
    return subprocess.check_output(["git", *arguments])


def staged_entry(requested_path):
    """Select one exact index entry without consulting working-tree contents."""
    if not requested_path:
        raise ValueError("--path must name one exact staged file")
    records = git("--literal-pathspecs", "ls-files", "--stage", "-z", "--", requested_path)
    entries = []
    for record in records.split(b"\0"):
        if not record:
            continue
        metadata, path = record.split(b"\t", 1)
        mode, digest, stage = metadata.decode("ascii").split()
        if stage != "0":
            raise ValueError("Resolve the staged merge conflict before publishing")
        entries.append((mode, digest, path.decode()))
    if not entries:
        raise ValueError("No staged entry matches --path")
    if len(entries) != 1:
        raise ValueError("--path selects multiple staged entries; choose one exact file")
    mode, digest, path = entries[0]
    # ls-files reports paths relative to its working directory. Normalize only
    # the spelling: the staged file may be deleted or a symlink in the worktree.
    if os.path.abspath(requested_path) != os.path.abspath(path):
        raise ValueError("--path selects a directory; choose one exact staged file")
    if mode not in ("100644", "100755", "120000"):
        raise ValueError("--path must name a staged blob, not a submodule or directory")
    return mode, digest, path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--path", help="Return one exact staged blob and its mode")
    parser.add_argument("--offset", type=int, default=0, help="Byte offset for a transport chunk")
    parser.add_argument("--length", type=int, help="Maximum bytes in the transport chunk; zero returns metadata")
    args = parser.parse_args()
    if args.offset < 0 or (args.length is not None and args.length < 0):
        parser.error("Chunk offset and length must be non-negative")
    if args.path is None and (args.offset or args.length is not None):
        parser.error("Chunk arguments require --path")
    if args.path is not None:
        try:
            mode, digest, path = staged_entry(args.path)
        except ValueError as error:
            parser.error(str(error))
        content = git("cat-file", "blob", digest)
        end = None if args.length is None else args.offset + args.length
        chunk = content[args.offset:end]
        print(json.dumps({"path": path, "mode": mode, "sha": digest,
                          "total_bytes": len(content), "offset": args.offset,
                          "chunk_bytes": len(chunk),
                          "content": base64.b64encode(chunk).decode(), "encoding": "base64"}))
    else:
        changes = git("diff", "--cached", "--name-only", "-z").split(b"\0")
        print(json.dumps({"parent": git("rev-parse", "HEAD").decode().strip(),
                          "tree": git("write-tree").decode().strip(),
                          "paths": [path.decode() for path in changes if path]}))


if __name__ == "__main__":
    main()
