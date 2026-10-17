#!/usr/bin/env python3
"""Split or reconstruct a binary artifact without changing any artifact bytes.

Transport-sized files allow evidence to be published through clients with small
request limits. The manifest retains the original and each part's SHA256.
"""

import argparse
import hashlib
import json
from pathlib import Path


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def split(source, directory, part_bytes):
    if part_bytes <= 0:
        raise ValueError("Part size must be positive")
    directory.mkdir(parents=True, exist_ok=False)
    records = []
    with source.open("rb") as stream:
        while block := stream.read(part_bytes):
            path = directory / f"part-{len(records):04d}.bin"
            path.write_bytes(block)
            records.append({"path": path.name, "bytes": len(block),
                            "sha256": hashlib.sha256(block).hexdigest()})
    document = {"schema": "boostregexrs.binary-parts.v1", "filename": source.name,
                "bytes": source.stat().st_size, "sha256": digest(source), "parts": records}
    (directory / "manifest.json").write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
    verify_or_join(directory / "manifest.json", None)
    return document


def verify_or_join(manifest, output):
    document = json.loads(manifest.read_text(encoding="utf-8"))
    combined = hashlib.sha256()
    count = 0
    # The explicitly selected output is opened exclusively so a historical
    # artifact cannot be silently replaced during reassembly.
    destination = output.open("xb") if output else None
    try:
        for record in document["parts"]:
            block = (manifest.parent / record["path"]).read_bytes()
            if len(block) != record["bytes"] or hashlib.sha256(block).hexdigest() != record["sha256"]:
                raise ValueError(f"Invalid artifact part: {record['path']}")
            combined.update(block)
            count += len(block)
            if destination:
                destination.write(block)
        if count != document["bytes"] or combined.hexdigest() != document["sha256"]:
            raise ValueError("Combined artifact identity differs")
    finally:
        if destination:
            destination.close()
    return {"bytes": count, "sha256": combined.hexdigest(), "parts": len(document["parts"])}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    create = commands.add_parser("split")
    create.add_argument("--source", type=Path, required=True)
    create.add_argument("--directory", type=Path, required=True)
    create.add_argument("--part-bytes", type=int, default=2 << 20)
    for operation in ("join", "verify"):
        command = commands.add_parser(operation)
        command.add_argument("--manifest", type=Path, required=True)
        if operation == "join":
            command.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "split":
        result = split(args.source, args.directory, args.part_bytes)
    else:
        result = verify_or_join(args.manifest, args.output if args.command == "join" else None)
    print(json.dumps({key: value for key, value in result.items() if key != "parts" or isinstance(value, int)}))


if __name__ == "__main__":
    main()
