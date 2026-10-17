#!/usr/bin/env python3
"""Preserve a complete probe run in a deterministic archive with file digests."""

import argparse
import datetime as dt
import gzip
import hashlib
import json
import lzma
from pathlib import Path
import shutil
import tarfile

from compare import sha256


def verify(directory, archive_override=None):
    document = json.loads((directory / "manifest.json").read_text())
    archive = archive_override or directory / document["archive"]["path"]
    if sha256(archive) != document["archive"]["sha256"]:
        raise ValueError("Archive digest differs from the recorded identity")
    expected = {item["path"]: item for item in document["files"]}
    seen = set()
    with tarfile.open(archive, "r|*") as source:
        for member in source:
            if not member.isfile() or member.name in seen or member.name not in expected:
                raise ValueError(f"Unexpected archive member: {member.name}")
            seen.add(member.name)
            digest = hashlib.sha256()
            stream = source.extractfile(member)
            for block in iter(lambda: stream.read(1 << 20), b""):
                digest.update(block)
            record = expected[member.name]
            if member.size != record["bytes"] or digest.hexdigest() != record["sha256"]:
                raise ValueError(f"Archived bytes differ: {member.name}")
    if seen != set(expected):
        raise ValueError("The archive omits recorded evidence files")
    return {"verified_files": len(seen), "archive_bytes": archive.stat().st_size,
            "archive_sha256": document["archive"]["sha256"]}


def archive(source, output, compression="xz"):
    source, output = source.resolve(), output.resolve()
    paths = sorted(path for path in source.rglob("*") if path.is_file())
    if not paths or not (source / "summary.json").is_file():
        raise ValueError("The source must contain a completed probe summary and evidence")
    # Historical evidence is immutable: choose a new destination for each run.
    output.mkdir(parents=True, exist_ok=False)
    records = [{"path": path.relative_to(source).as_posix(), "bytes": path.stat().st_size,
                "sha256": sha256(path)} for path in paths]
    destination = output / f"raw.tar.{compression}"
    if compression == "gz":
        compressed = gzip.GzipFile(filename=destination, mode="wb", mtime=0)
    else:
        compressed = lzma.LZMAFile(destination, mode="wb", preset=6)
    with compressed:
        with tarfile.open(fileobj=compressed, mode="w|", format=tarfile.PAX_FORMAT) as target:
            for path, record in zip(paths, records):
                info = tarfile.TarInfo(record["path"])
                info.size, info.mode, info.mtime = record["bytes"], 0o644, 0
                with path.open("rb") as content:
                    target.addfile(info, content)
    shutil.copyfile(source / "summary.json", output / "summary.json")
    document = {
        "schema": "boostregexrs.probe-evidence-archive.v1",
        "created_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "source_directory": str(source),
        "source_summary_sha256": sha256(source / "summary.json"),
        "archive": {"path": destination.name, "bytes": destination.stat().st_size,
                    "sha256": sha256(destination), "compression": compression},
        "uncompressed_file_bytes": sum(record["bytes"] for record in records),
        "files": records,
        "archiver": {"path": str(Path(__file__).resolve()), "sha256": sha256(Path(__file__))},
        "preservation": "All source files retained byte-for-byte; source directory was not changed",
    }
    (output / "manifest.json").write_text(json.dumps(document, indent=2) + "\n")
    result = verify(output)
    (output / "verification.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--compression", choices=("xz", "gz"), default="xz")
    parser.add_argument("--verify", type=Path, metavar="DIRECTORY")
    parser.add_argument("--archive", type=Path, help="Reassembled archive to verify against --verify DIRECTORY")
    args = parser.parse_args()
    if args.verify:
        if args.source or args.output:
            parser.error("--verify is used without --source or --output")
        result = verify(args.verify, args.archive)
    else:
        if args.archive:
            parser.error("--archive requires --verify")
        if not args.source or not args.output:
            parser.error("archive creation requires --source and --output")
        result = archive(args.source, args.output, args.compression)
    print(json.dumps(result))


if __name__ == "__main__":
    main()
