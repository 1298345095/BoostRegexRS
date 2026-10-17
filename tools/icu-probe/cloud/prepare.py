#!/usr/bin/env python3
"""Prepare the official, full-data Boost 1.89.0 / ICU4C 77.1 oracle locally.

Only development tools use these native dependencies. No system installation,
locale override, ICU data filter, or production Rust linkage is performed.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tarfile


REPO = Path(__file__).resolve().parents[3]
DEFAULT_CACHE = REPO / "target/research/icu77-cloud"
BOOST_ARCHIVE = "boost_1_89_0.tar.bz2"
BOOST_BASE = "https://archives.boost.io/release/1.89.0/source/"
BOOST_SHA256 = "85a33fa22621b4f314f8e85e1a5e2a9363d22e4f4992925d4bb3bc631b5a0c7a"
ICU_ARCHIVE = "icu4c-77_1-src.tgz"
ICU_BASE = "https://github.com/unicode-org/icu/releases/download/release-77-1/"
ICU_SHA512 = (
    "a47d6d9c327d037a05ea43d1d1a06b2fd757cc02a94f7c1a238f35cfc3dfd4ab78d0612"
    "790f3a3cca0292c77412a9c2c15c8f24b718f79a857e007e66f07e7cd"
)


def digest(path: Path, algorithm: str = "sha256") -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, algorithm).hexdigest()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temporary.replace(path)


def file_identity(path: Path, relative_to: Path = REPO) -> dict:
    return {
        "path": os.path.relpath(path, relative_to),
        "bytes": path.stat().st_size,
        "sha256": digest(path),
    }


def command_output(command: list[str]) -> str:
    result = subprocess.run(command, text=True, capture_output=True, check=True)
    return result.stdout.strip()


def download(url: str, target: Path) -> None:
    if target.is_file():
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(target.name + ".part")
    subprocess.run(
        ["curl", "--fail", "--location", "--retry", "3", "--silent", "--show-error",
         "--output", str(temporary), url],
        check=True,
    )
    temporary.replace(target)


def fetch_and_verify(cache: Path) -> list[dict]:
    downloads = cache / "downloads"
    files = [
        (BOOST_BASE + BOOST_ARCHIVE, downloads / BOOST_ARCHIVE),
        (BOOST_BASE + BOOST_ARCHIVE + ".json", downloads / (BOOST_ARCHIVE + ".json")),
        (ICU_BASE + ICU_ARCHIVE, downloads / ICU_ARCHIVE),
        (ICU_BASE + "SHASUM512.txt", downloads / "SHASUM512.txt"),
    ]
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        futures = [pool.submit(download, url, path) for url, path in files]
        for future in futures:
            future.result()

    boost_published = json.loads((downloads / (BOOST_ARCHIVE + ".json")).read_text())
    if boost_published.get("file") != BOOST_ARCHIVE or boost_published.get("sha256") != BOOST_SHA256:
        raise RuntimeError("Official Boost checksum metadata differs from the pinned release identity")
    icu_lines = (downloads / "SHASUM512.txt").read_text().splitlines()
    matching = [line.split() for line in icu_lines if line.split()[-1].lstrip("*") == ICU_ARCHIVE]
    if len(matching) != 1 or matching[0][0].lower() != ICU_SHA512:
        raise RuntimeError("Official ICU checksum metadata differs from the pinned release identity")

    provenance = []
    for name, algorithm, expected, base, checksum_name in [
        (BOOST_ARCHIVE, "sha256", BOOST_SHA256, BOOST_BASE, BOOST_ARCHIVE + ".json"),
        (ICU_ARCHIVE, "sha512", ICU_SHA512, ICU_BASE, "SHASUM512.txt"),
    ]:
        actual = digest(downloads / name, algorithm)
        if actual != expected:
            raise RuntimeError(f"{name}: {algorithm} mismatch; remove the damaged archive and rerun")
        provenance.append({
            "archive_url": base + name,
            "checksum_manifest_url": base + checksum_name,
            "algorithm": algorithm,
            "published_digest": expected,
            "actual_digest": actual,
            "published_digest_matches": True,
            "archive": file_identity(downloads / name),
            "checksum_manifest": file_identity(downloads / checksum_name),
            "detached_signature_verified": False,
        })
    return provenance


def extract_archive(cache: Path, name: str, directory: str, expected: str) -> Path:
    destination = cache / "deps" / directory
    marker = destination / ".boostregexrs-source-archive.json"
    expected_marker = {"archive": name, "pinned_digest": expected}
    if marker.is_file() and json.loads(marker.read_text()) == expected_marker:
        return destination
    if destination.exists():
        raise RuntimeError(f"Unidentified source tree already exists: {destination}; use a fresh --cache")
    staging = cache / "deps" / ("extract-" + directory)
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True)
    with tarfile.open(cache / "downloads" / name) as archive:
        # Python's data filter rejects path traversal and escaping links.
        archive.extractall(staging, filter="data")
    source = staging / directory
    if not source.is_dir():
        raise RuntimeError(f"Unexpected top-level source directory in {name}")
    write_json(source / marker.name, expected_marker)
    source.replace(destination)
    staging.rmdir()
    return destination


def run_logged(command: list[str], *, cwd: Path, log: Path, env: dict | None = None) -> None:
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("w", encoding="utf-8") as stream:
        stream.write(json.dumps({"command": command, "cwd": str(cwd)}) + "\n")
        stream.flush()
        result = subprocess.run(command, cwd=cwd, env=env, stdout=stream, stderr=subprocess.STDOUT)
    if result.returncode:
        raise RuntimeError(f"Command failed ({result.returncode}); see {log}")


def source_identities(boost: Path, icu: Path) -> list[dict]:
    names = [
        boost / "boost/version.hpp", boost / "boost/regex/v5/icu.hpp", boost / "LICENSE_1_0.txt",
        icu / "LICENSE", icu / "source/configure", icu / "source/common/unicode/uvernum.h",
        icu / "source/data/in/icudt77l.dat",
    ]
    names.extend(icu / ("source/i18n/" + name) for name in [
        "collation.cpp", "collation.h", "collationdata.h", "collationdatareader.cpp",
        "collationiterator.cpp", "collationkeys.cpp", "collationsettings.h",
        "rulebasedcollator.cpp", "utf16collationiterator.cpp",
    ])
    return [file_identity(path) for path in names]


def prepare(cache: Path, jobs: int, cc: str = "cc", cxx: str = "c++") -> dict:
    cache = cache.resolve()
    if platform.system() != "Linux":
        raise RuntimeError("This cloud preparation entry point is validated for Linux; Windows uses run.ps1")
    for command in ["curl", "make", cc, cxx]:
        if shutil.which(command) is None:
            raise RuntimeError(f"Required tool is missing: {command}")
    provenance = fetch_and_verify(cache)
    print("Verified official Boost SHA256 and ICU SHA512", flush=True)
    boost = extract_archive(cache, BOOST_ARCHIVE, "boost_1_89_0", BOOST_SHA256)
    icu = extract_archive(cache, ICU_ARCHIVE, "icu", ICU_SHA512)
    source_files = source_identities(boost, icu)
    build = cache / "build/icu"
    prefix = cache / "install/icu"
    logs = cache / "logs"
    build.mkdir(parents=True, exist_ok=True)
    prefix.mkdir(parents=True, exist_ok=True)
    temporary = cache / "build/tmp"
    temporary.mkdir(parents=True, exist_ok=True)
    configure = [str(icu / "source/configure"), "--prefix=" + str(prefix),
                 "--enable-shared", "--enable-static", "--disable-tests", "--disable-samples",
                 "--with-data-packaging=library"]
    compiler = {"cc": command_output([cc, "--version"]), "cxx": command_output([cxx, "--version"])}
    recipe = {
        "configure": configure,
        "compiler": compiler,
        "source_files": source_files,
        "environment": {"CC": cc, "CXX": cxx, "CFLAGS": "-O2 -fPIC", "CXXFLAGS": "-O2 -fPIC",
                        "TMPDIR": str(temporary)},
    }
    state_path = build / "boostregexrs-build.json"
    state = json.loads(state_path.read_text()) if state_path.is_file() else None
    installed = [prefix / "lib" / ("lib" + library + ".so.77.1")
                 for library in ["icuuc", "icui18n", "icudata"]]
    reusable = (state is not None and state.get("recipe") == recipe and
                all(path.is_file() for path in installed) and
                state.get("installed") == [file_identity(path) for path in installed])
    if not reusable:
        env = dict(os.environ)
        # A caller's ICU_DATA/filter or compiler flags must not silently change
        # the full release data or the reference build recipe.
        for variable in ["ICU_DATA", "ICU_DATA_FILTER_FILE", "LDFLAGS", "CPPFLAGS"]:
            env.pop(variable, None)
        env.update(recipe["environment"])
        print(f"Building ICU 77.1 with full release data ({jobs} jobs); logs: {logs}", flush=True)
        if (build / "Makefile").is_file():
            # make cannot infer changes to the compiler/flags from timestamps.
            # A rejected build cache must not relabel old objects as a new build.
            run_logged(["make", "clean"], cwd=build, log=logs / "icu-clean.log", env=env)
        run_logged(configure, cwd=build, log=logs / "icu-configure.log", env=env)
        run_logged(["make", "-j", str(jobs)], cwd=build, log=logs / "icu-build.log", env=env)
        run_logged(["make", "install"], cwd=build, log=logs / "icu-install.log", env=env)
        write_json(state_path, {"recipe": recipe, "installed": [file_identity(path) for path in installed]})

    os_release = Path("/etc/os-release")
    manifest = {
        "schema": "boostregexrs.icu77-cloud-environment.v1",
        "generated_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "os": platform.platform(), "uname": list(platform.uname()),
        "os_release": os_release.read_text() if os_release.is_file() else None,
        "architecture": platform.machine(), "libc": list(platform.libc_ver()),
        "python": sys.version, "make": command_output(["make", "--version"]),
        "compiler": compiler, "versions": {"boost": "1.89.0", "icu": "77.1", "unicode": "16.0.0", "cldr": "47"},
        "compiler_executables": [
            {"command": command, "resolved_path": str(Path(shutil.which(command)).resolve()),
             "bytes": Path(shutil.which(command)).stat().st_size,
             "sha256": digest(Path(shutil.which(command)))} for command in [cc, cxx]
        ],
        "data": {"packaging": "library", "source": "unfiltered source-release icudt77l.dat",
                 "source_filters": [], "runtime_versions_verified_by": "reference/metadata.json"},
        "sources": provenance, "source_files": source_files,
        "build_recipe": recipe,
        "installed_libraries": [file_identity(path) for path in installed],
        "scripts": [file_identity(Path(__file__))],
        "paths": {"cache": str(cache), "boost": str(boost), "icu_source": str(icu), "icu_prefix": str(prefix)},
    }
    write_json(cache / "environment-manifest.json", manifest)
    print(f"Reference dependencies ready: {cache}", flush=True)
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, default=DEFAULT_CACHE)
    parser.add_argument("--jobs", type=int, default=min(os.cpu_count() or 1, 8))
    parser.add_argument("--cc", default="cc")
    parser.add_argument("--cxx", default="c++")
    args = parser.parse_args()
    if args.jobs < 1:
        parser.error("--jobs must be positive")
    prepare(args.cache, args.jobs, args.cc, args.cxx)


if __name__ == "__main__":
    main()
