#!/usr/bin/env python3
"""Retain exact failed settings binaries, source identities, and raw evidence."""

import argparse
import gzip
import json
from pathlib import Path
import sys
import tarfile

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from archive_evidence import verify
from run_locales import REPO, identity, save, sha256


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", type=Path, required=True)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--main-candidate", type=Path, required=True)
    parser.add_argument("--main-provenance", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    build = json.loads(args.build.read_text())
    run = json.loads((args.run / "summary.json").read_text())
    main_provenance = json.loads(args.main_provenance.read_text())
    if build["status"] != "passed" or run["status"] != "differences_or_incomplete":
        raise ValueError("Expected a built candidate and an actual failed acceptance run")
    binaries = {"failed-settings-probe": build["candidate"], "native-reference": build["reference"],
                "frozen-main-cli": {**main_provenance["candidate"], "path": str(args.main_candidate.resolve())}}
    if any(sha256(Path(record["path"])) != record["sha256"] for record in binaries.values()):
        raise ValueError("Binary differs from its original recorded run identity")
    selected = {}
    for label, directory in (("failed-run", args.run), ("build", args.build.parent)):
        for path in directory.rglob("*"):
            if path.is_file():
                selected[f"{label}/{path.relative_to(directory).as_posix()}"] = path
    for name, record in binaries.items():
        selected[f"binaries/{name}"] = Path(record["path"])
    selected["frozen-main-provenance.json"] = args.main_provenance
    for record in build["rust_runtime_sources"]:
        path = Path(record["path"])
        if sha256(path) != record["sha256"]:
            raise ValueError("Frozen runtime source changed before failure preservation")
        selected[f"runtime-source/{path.relative_to(REPO).as_posix()}"] = path
    selected["retention-source/retain_failure.py"] = Path(__file__)
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    records = [{"path": name, "source_path": str(path.resolve()), "bytes": path.stat().st_size,
                "sha256": sha256(path), "mode": 0o755 if name.startswith("binaries/") else 0o644}
               for name, path in sorted(selected.items())]
    archive = output / "raw.tar.gz"
    with archive.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as compressed:
            with tarfile.open(fileobj=compressed, mode="w|", format=tarfile.PAX_FORMAT) as target:
                for record in records:
                    info = tarfile.TarInfo(record["path"])
                    info.size, info.mode, info.mtime = record["bytes"], record["mode"], 0
                    with selected[record["path"]].open("rb") as source:
                        target.addfile(info, source)
    save(output / "manifest.json", {"schema": "boostregexrs.probe-evidence-archive.v1",
         "archive": {"path": archive.name, "bytes": archive.stat().st_size, "sha256": sha256(archive), "compression": "gz"},
         "files": records, "archiver": identity(Path(__file__)),
         "preservation": "Actual failed binary bytes retained before repair; original input/output/build files unchanged"})
    save(output / "summary.json", {"schema": "boostregexrs.icu77-reorder-failure-retention.v1",
         "status": "retained_failure_evidence", "build": identity(args.build), "failed_run": identity(args.run / "summary.json"),
         "binaries": binaries, "command": [sys.executable, *sys.argv], "archive": identity(archive)})
    result = verify(output)
    save(output / "verification.json", result)
    print(json.dumps(result))


if __name__ == "__main__":
    main()
