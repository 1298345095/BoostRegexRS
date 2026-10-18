"""Check every extracted source file against the verified official archive."""

import hashlib
import lzma
import os
from pathlib import Path, PurePosixPath
import tarfile


def sha256(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def verify_source_tree(archive_path, source, output):
    """Return a content identity only after every archive member was checked."""
    records = []
    paths = set()
    with tarfile.open(archive_path) as archive:
        for member in archive:
            relative = PurePosixPath(member.name).relative_to(source.name)
            if member.isdir():
                continue
            path = source / Path(relative)
            name = relative.as_posix()
            if name in paths:
                raise ValueError(f"Duplicate source archive member: {name}")
            paths.add(name)
            if member.issym():
                if not path.is_symlink() or os.readlink(path) != member.linkname:
                    raise ValueError(f"Extracted source link differs: {name}")
                content = member.linkname.encode("utf-8")
                digest = hashlib.sha256(content).hexdigest()
                size, kind = len(content), "symlink-target"
            elif member.isfile() or member.islnk():
                with archive.extractfile(member) as stream:
                    expected = hashlib.file_digest(stream, "sha256").hexdigest()
                if path.is_symlink() or not path.is_file() or sha256(path) != expected:
                    raise ValueError(f"Extracted source content differs: {name}")
                digest, size, kind = expected, path.stat().st_size, "file"
            else:
                raise ValueError(f"Unexpected source archive member kind: {name}")
            records.append(f"{name}\t{kind}\t{size}\t{digest}\n")
    actual = {path.relative_to(source).as_posix() for path in source.rglob("*")
              if path.is_file() or path.is_symlink()}
    # The extractor's marker is metadata, never an upstream source patch.
    actual.discard(".boostregexrs-source-archive.json")
    if actual != paths:
        raise ValueError(f"Unexpected extracted source paths: {sorted(actual ^ paths)[:10]}")
    manifest = ("path\tkind\tbytes\tsha256\n" + "".join(sorted(records))).encode("utf-8")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(lzma.compress(manifest))
    return {"archive": str(archive_path), "root": str(source), "entries": len(records),
            "manifest": str(output), "manifest_sha256": sha256(output),
            "uncompressed_manifest_sha256": hashlib.sha256(manifest).hexdigest(),
            "all_extracted_contents_match_archive": True, "patch_set": []}
