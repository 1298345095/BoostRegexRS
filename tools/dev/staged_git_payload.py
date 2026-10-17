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
    parser.add_argument("--offset", type=int, default=0, help="Byte offset for a transport chunk")
    parser.add_argument("--length", type=int, help="Maximum bytes in the transport chunk; zero returns metadata")
    args = parser.parse_args()
    if args.offset < 0 or (args.length is not None and args.length < 0):
        parser.error("Chunk offset and length must be non-negative")
    if not args.path and (args.offset or args.length is not None):
        parser.error("Chunk arguments require --path")
    if args.path:
        entry = git("ls-files", "--stage", "-z", "--", args.path).split(b"\0")[0]
        metadata, path = entry.split(b"\t", 1)
        mode, digest, stage = metadata.decode().split()
        if stage != "0":
            raise RuntimeError("Resolve the staged merge conflict before publishing")
        content = git("cat-file", "blob", digest)
        end = None if args.length is None else args.offset + args.length
        chunk = content[args.offset:end]
        print(json.dumps({"path": path.decode(), "mode": mode, "sha": digest,
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
