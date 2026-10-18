#!/usr/bin/env python3
"""Build the pinned native Linux reference in a new cache and preserve its smoke run.

See README.md for the same verified-source recipe on the other five native
targets. Those targets require their own execution evidence in V21-V26.
"""

import argparse
import datetime as dt
import json
import os
from pathlib import Path
import platform
import re
import shutil
import sys
import tarfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools/icu-probe/cloud"))
import prepare
from source_identity import verify_source_tree


def command(command_args, cache, name, *, timeout=20, env=None, input_path=None, check=True):
    log = cache / "logs" / (name + ".log")
    record = prepare.run_logged(command_args, cwd=ROOT, log=log, timeout=timeout,
                                env=env, input_path=input_path, check=check)
    return record, log


def runtime_environment(cache):
    env = dict(os.environ)
    env["LD_LIBRARY_PATH"] = str(cache / "install/icu/lib")
    env["TMPDIR"] = str(cache / "build/tmp")
    for name in ("ICU_DATA", "ICU_DATA_FILTER_FILE"):
        env.pop(name, None)
    return env


def runtime_library_paths(value):
    """Read ldd's path field without treating spaces inside it as separators."""
    paths = set()
    for line in value.splitlines():
        entry = line.strip()
        if not entry.startswith("/"):
            _, arrow, entry = entry.partition(" => ")
            if not arrow:
                continue
        path, separator, address = entry.rpartition(" (")
        if separator and path.startswith("/") and re.fullmatch(r"0x[0-9a-fA-F]+\)", address):
            paths.add(Path(path))
    return sorted(paths)


def runtime_libraries(executable, cache, env):
    _, log = command(["ldd", str(executable)], cache, executable.name + "-ldd", env=env)
    value = log.read_text(encoding="utf-8")
    if "not found" in value:
        raise RuntimeError(f"A reference runtime library is missing: {log}")
    paths = runtime_library_paths(value)
    if not paths:
        raise RuntimeError("No runtime libraries were identified")
    libraries = [prepare.file_identity(path.resolve()) for path in paths]
    for name in ("libicui18n.so.77", "libicuuc.so.77", "libicudata.so.77"):
        if name in value and f"{name} => {cache / 'install/icu/lib' / name} " not in value:
            raise RuntimeError(f"Reference loaded a different ICU library: {name}")
    if executable.name == "sortkey-reference" and any(name not in value for name in
                                                     ("libicui18n.so.77", "libicuuc.so.77", "libicudata.so.77")):
        raise RuntimeError("The sort-key reference did not identify all ICU libraries")
    return libraries


def build_oracles(cache, cxx):
    binaries = cache / "bin"
    binaries.mkdir(parents=True, exist_ok=True)
    prefix = cache / "install/icu"
    boost = cache / "deps/boost_1_89_0"
    env = runtime_environment(cache)
    sources = {"byte-reference": ROOT / "tools/regex-oracle/oracle.cpp",
               "sortkey-reference": ROOT / "tools/icu-probe/primary/oracle.cpp"}
    result = {}
    for name, source in sources.items():
        executable = binaries / name
        args = [cxx, "-std=c++17", "-O2", "-Wall", "-Wextra", "-pedantic",
                "-I" + str(boost)]
        if name == "sortkey-reference":
            args.extend(["-I" + str(prefix / "include"), str(source), "-L" + str(prefix / "lib"),
                         "-Wl,-rpath," + str(prefix / "lib"), "-licui18n", "-licuuc", "-licudata"])
        else:
            args.extend(["-DBOOST_REGEX_NO_LIB", str(source)])
        args.extend(["-o", str(executable)])
        command(args, cache, name + "-build", timeout=300, env=env)
        result[name] = {"executable": prepare.file_identity(executable),
                        "source": prepare.file_identity(source), "compile_command": args,
                        "runtime_libraries": runtime_libraries(executable, cache, env)}
    return result


def write_verified_environment(cache, environment, smoke, output):
    """Bind the environment report to the metadata that passed the native smoke."""
    paths = {}
    for strength in ("primary", "identical"):
        relative = Path("smoke") / (strength + "-metadata.json")
        observed = json.loads((cache / relative).read_text(encoding="utf-8"))
        if observed != smoke["keys"][strength]["metadata"]:
            raise ValueError(f"Runtime metadata differs from the verified {strength} smoke")
        paths[strength] = relative.as_posix()
    corrected = dict(environment)
    corrected["data"] = {**environment["data"], "runtime_versions_verified_by": paths}
    prepare.write_json(output, corrected)
    return corrected


def snapshot(cache, output, manifest):
    raw = output / "raw-run.tar.xz"
    with tarfile.open(raw, "w:xz") as archive:
        for relative in ("logs", "downloads/logs", "source-manifests", "smoke"):
            path = cache / relative
            if path.exists():
                archive.add(path, arcname=relative)
        for relative in ("environment-manifest.json", "reference-manifest.json"):
            path = cache / relative
            if path.exists():
                archive.add(path, arcname=relative)
        for relative in ("build/icu/config.log", "build/icu/icudefs.mk",
                         "downloads/boost_1_89_0.tar.bz2.json", "downloads/SHASUM512.txt"):
            path = cache / relative
            if path.exists():
                archive.add(path, arcname=relative)
    manifest["raw_evidence_archive"] = prepare.file_identity(raw)
    prepare.write_json(output / "summary.json", manifest)


def run(cache, output, jobs, cc, cxx, sources_only=False):
    if not sources_only and (platform.system() != "Linux" or platform.machine() not in ("x86_64", "aarch64")):
        raise RuntimeError("Use the native platform recipe in README.md; this runner executes Linux only")
    cache.mkdir(parents=True, exist_ok=False)
    output.mkdir(parents=True, exist_ok=False)
    if platform.system() == "Linux":
        import resource
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    manifest = {"schema": "boostregexrs.native-reference.v1", "status": "running",
                "started_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
                "entry_command": [sys.executable, *sys.argv], "cache": str(cache),
                "platform": platform.platform(), "architecture": platform.machine(),
                "libc": list(platform.libc_ver()), "python": sys.version,
                "full_library_compatibility_verified": False, "other_platforms_verified": False,
                "scripts": [prepare.file_identity(ROOT / path) for path in
                            ("tools/regex-oracle/build_reference.py", "tools/regex-oracle/source_identity.py",
                             "tools/regex-oracle/smoke.py", "tools/regex-oracle/protocol.py",
                             "tools/icu-probe/cloud/prepare.py")]}
    try:
        # Evidence under the new output directory is an expected new untracked path.
        _, head = command(["git", "rev-parse", "HEAD"], cache, "checkout-head")
        status_args = ["git", "status", "--porcelain=v1", "--untracked-files=all", "--", "."]
        if output.is_relative_to(ROOT):
            status_args.append(":(exclude)" + output.relative_to(ROOT).as_posix())
        _, status = command(status_args, cache, "checkout-status")
        if status.read_text().strip():
            raise RuntimeError("A clean checkout is required; inspect checkout-status.log")
        manifest["checkout"] = {"commit": head.read_text().strip(), "clean_at_start": True}
        manifest["official_archives"] = prepare.fetch_and_verify(cache)
        boost = prepare.extract_archive(cache, prepare.BOOST_ARCHIVE, "boost_1_89_0", prepare.BOOST_SHA256)
        icu = prepare.extract_archive(cache, prepare.ICU_ARCHIVE, "icu", prepare.ICU_SHA512)
        manifest["extracted_sources"] = []
        for archive_name, source in ((prepare.BOOST_ARCHIVE, boost), (prepare.ICU_ARCHIVE, icu)):
            print(f"Checking every extracted file in {source}", flush=True)
            manifest["extracted_sources"].append(verify_source_tree(
                cache / "downloads" / archive_name, source,
                cache / "source-manifests" / (source.name + ".tsv.xz")))
        if sources_only:
            manifest["status"] = "verified_official_sources_only"
            return
        manifest["environment"] = prepare.prepare(cache, jobs, cc, cxx)
        _, linker = command([cxx, "-print-prog-name=ld"], cache, "linker-path")
        linker_name = linker.read_text().strip()
        linker_path = Path(shutil.which(linker_name) or linker_name).resolve(strict=True)
        command([str(linker_path), "--version"], cache, "linker-version")
        manifest["linker"] = prepare.file_identity(linker_path)
        manifest["references"] = build_oracles(cache, cxx)
        prepare.write_json(cache / "reference-manifest.json", manifest)
        from smoke import run_smoke
        manifest["smoke"] = run_smoke(cache, command, runtime_environment(cache))
        manifest["environment"] = write_verified_environment(
            cache, manifest["environment"], manifest["smoke"], cache / "environment-manifest.json")
        manifest["status"] = "passed_reference_reproduction"
    except BaseException as error:
        manifest["status"] = "failed"
        manifest["failure"] = f"{type(error).__name__}: {error}"
        raise
    finally:
        manifest["finished_utc"] = dt.datetime.now(dt.timezone.utc).isoformat()
        prepare.write_json(cache / "reference-manifest.json", manifest)
        snapshot(cache, output, manifest)
    print(json.dumps({key: manifest[key] for key in ("status", "checkout", "smoke")}, indent=2), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, required=True, help="A new, empty reference-cache path")
    parser.add_argument("--output", type=Path, required=True, help="A new durable evidence directory")
    parser.add_argument("--jobs", type=int, default=4)
    parser.add_argument("--cc", default="cc")
    parser.add_argument("--cxx", default="c++")
    parser.add_argument("--sources-only", action="store_true",
                        help="Verify/extract the same sources for the native macOS/MSVC recipe")
    args = parser.parse_args()
    if args.jobs < 1:
        parser.error("--jobs must be positive")
    run(args.cache.resolve(), args.output.resolve(), args.jobs, args.cc, args.cxx, args.sources_only)


if __name__ == "__main__":
    main()
