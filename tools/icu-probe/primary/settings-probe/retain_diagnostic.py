#!/usr/bin/env python3
"""Archive an actual diagnostic executable, original run and matching sources."""

import argparse
import datetime as dt
import gzip
import json
import os
from pathlib import Path
import shutil
import sys
import tarfile

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from archive_evidence import verify
from run_locales import REPO, bounded, identity, run_logged, save, sha256


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    summary = json.loads((args.run / "summary.json").read_text())
    records = [summary["binary"], *summary["sources"]]
    if any(sha256(Path(record["path"])) != record["sha256"] for record in records):
        raise ValueError("Diagnostic executable or source differs from the actual recorded run")
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    environment = os.environ.copy()
    environment.pop("ICU_DATA", None)
    environment["LC_ALL"] = "C"
    for command, name in ((["c++", "--version"], "compiler.log"),
                          (["ldd", summary["binary"]["path"]], "linkage.log")):
        run_logged(bounded(command, 20), cwd=REPO, log=output / name, env=environment, timeout=30)
    save(output / "execution-environment.json", {
        "schema": "boostregexrs.diagnostic-execution-environment.v1",
        "recorded_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "recorded_after_original_execution": True,
        "original_environment_basis": "LC_ALL=C and ICU_DATA unset are explicit in the retained diagnostic driver; other original ambient variables were not captured",
        "original_explicit_environment": {"set": {"LC_ALL": "C"}, "unset": ["ICU_DATA"]},
        "compiler_observed_at_retention": identity(Path(shutil.which("c++")).resolve()),
        "linkage_observed_at_retention": "The same executable SHA256 was checked before this inspection",
    })
    selected = {f"original-run/{path.relative_to(args.run).as_posix()}": path
                for path in args.run.rglob("*") if path.is_file()}
    selected.update({f"retention-observations/{path.name}": path for path in output.iterdir() if path.is_file()})
    selected["binaries/native-diagnostic"] = Path(summary["binary"]["path"])
    for index, record in enumerate(summary["sources"]):
        path = Path(record["path"])
        selected[f"source/{index:02d}-{path.name}"] = path
    selected["retention-source/retain_diagnostic.py"] = Path(__file__)
    files = [{"path": name, "source_path": str(path.resolve()), "bytes": path.stat().st_size,
              "sha256": sha256(path), "mode": 0o755 if name.startswith("binaries/") else 0o644}
             for name, path in sorted(selected.items())]
    archive = output / "raw.tar.gz"
    with archive.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as compressed:
            with tarfile.open(fileobj=compressed, mode="w|", format=tarfile.PAX_FORMAT) as target:
                for record in files:
                    info = tarfile.TarInfo(record["path"])
                    info.size, info.mode, info.mtime = record["bytes"], record["mode"], 0
                    with selected[record["path"]].open("rb") as source:
                        target.addfile(info, source)
    save(output / "manifest.json", {"schema": "boostregexrs.probe-evidence-archive.v1",
         "archive": {"path": archive.name, "bytes": archive.stat().st_size, "sha256": sha256(archive), "compression": "gz"},
         "files": files, "archiver": identity(Path(__file__))})
    save(output / "summary.json", {"schema": "boostregexrs.native-diagnostic-retention.v1",
         "status": "retained_actual_diagnostic", "original_status": summary["status"],
         "original_summary": identity(args.run / "summary.json"), "binary": summary["binary"],
         "command": [sys.executable, *sys.argv], "cwd": str(REPO), "archive": identity(archive)})
    result = verify(output)
    save(output / "verification.json", result)
    print(json.dumps(result))


if __name__ == "__main__":
    main()
