#!/usr/bin/env python3
"""Build finite public-settings differential drivers with recorded tool identities."""

import argparse
import json
import os
from pathlib import Path
import shutil
import sys

HERE = Path(__file__).resolve().parent
PRIMARY = HERE.parent
sys.path.insert(0, str(PRIMARY))
from run_locales import REPO, bounded, identity, run_logged, save, sha256  # noqa: E402


def build(cache, rust_cache, output, check_library=False):
    output.mkdir(parents=True, exist_ok=False)
    directory = rust_cache / "build/settings-probe" / output.name
    directory.mkdir(parents=True, exist_ok=False)
    prefix = rust_cache / "toolchain/install"
    toolchain_path = rust_cache / "rust-toolchain-manifest.json"
    toolchain = json.loads(toolchain_path.read_text())
    for name in ("rustc", "cargo"):
        if sha256(prefix / "bin" / name) != toolchain[f"{name if name == 'cargo' else 'compiler'}_sha256"]:
            raise ValueError("Installed Rust tool differs from its verified stable manifest")
    if "nightly" in toolchain["actual"]["rustc"] or "beta" in toolchain["actual"]["rustc"]:
        raise ValueError("Settings probe requires Rust stable")
    shutil.copyfile(toolchain_path, output / "rust-toolchain-manifest.json")
    environment = dict(os.environ)
    environment.update({
        "RUSTC": str(PRIMARY.parent / "cloud/rustc-local.py"),
        "RUSTDOC": str(PRIMARY.parent / "cloud/rustdoc-local.py"),
        "BOOSTREGEXRS_RUST_PREFIX": str(prefix), "CARGO_HOME": str(rust_cache / "cargo-home"),
        "CARGO_TARGET_DIR": str(directory), "CARGO_INCREMENTAL": "0",
        "LD_LIBRARY_PATH": str(prefix / "lib"), "RUSTFLAGS": "-C link-arg=-fuse-ld=bfd",
    })
    manifest = HERE / "Cargo.toml"
    cargo = prefix / "bin/cargo"

    def execute(command, name, env, seconds=180):
        return run_logged(bounded(command, seconds), cwd=REPO, log=output / name,
                          env=env, timeout=seconds + 10)

    execute([prefix / "bin/rustfmt", "--edition", "2024", "--check", HERE / "src/main.rs"],
            "fmt.log", environment, 30)
    if not (HERE / "Cargo.lock").exists():
        execute([cargo, "generate-lockfile", "--offline", "--manifest-path", manifest], "lock.log", environment, 30)
    lint_environment = {**environment, "RUSTC": str(prefix / "bin/clippy-driver"), "SYSROOT": str(prefix),
                        "RUSTFLAGS": f"-C link-arg=-fuse-ld=bfd --sysroot {prefix} -D warnings",
                        "CARGO_TARGET_DIR": str(directory / "lint")}
    execute([cargo, "check", "--locked", "--offline", "--all-targets", "--manifest-path", manifest],
            "clippy.log", lint_environment)
    library_checks = None
    if check_library:
        library = PRIMARY / "rust"
        rust_sources = sorted((library / "src").glob("*.rs")) + sorted((library / "tests").glob("*.rs"))
        library_checks = {
            "fmt": execute([prefix / "bin/rustfmt", "--edition", "2024", "--check", *rust_sources],
                           "library-fmt.log", environment, 30),
            "clippy": execute([cargo, "check", "--locked", "--offline", "--all-targets", "--manifest-path", library / "Cargo.toml"],
                              "library-clippy.log", lint_environment),
            "tests": execute([cargo, "test", "--locked", "--offline", "--all-targets", "--manifest-path", library / "Cargo.toml"],
                             "library-tests.log", environment),
            "sources": [identity(path) for path in rust_sources],
            "fixtures": [identity(path) for path in sorted((library / "tests/data").rglob("*"))
                         if path.is_file() and path.suffix in (".bin", ".tsv", ".json")],
        }
    execute([cargo, "build", "--release", "--locked", "--offline", "--manifest-path", manifest],
            "rust-build.log", environment)
    native_prefix = cache / "install/icu"
    reference = directory / "settings-reference"
    command = ["c++", "-std=c++17", "-O2", "-Wall", "-Wextra", "-Werror", "-DU_STATIC_IMPLEMENTATION",
               "-I", native_prefix / "include", HERE / "reference.cpp",
               *[native_prefix / "lib" / name for name in ("libicui18n.a", "libicuuc.a", "libicudata.a")],
               "-lpthread", "-ldl", "-lm", "-o", reference]
    execute(command, "native-build.log", dict(os.environ))
    candidate = directory / "release/icu77-settings-probe"
    execute(["ldd", candidate], "rust-linkage.log", dict(os.environ), 20)
    linkage = (output / "rust-linkage.log").read_text()
    if any(name in linkage for name in ("libicu", "libboost", "libstdc++")):
        raise ValueError("Pure Rust settings driver acquired a native reference dependency")
    source_paths = [HERE / name for name in ("build.py", "Cargo.toml", "Cargo.lock", "reference.cpp", "src/main.rs")]
    sources = [identity(path) for path in source_paths]
    runtime_sources = [identity(path) for path in sorted((PRIMARY / "rust/src").glob("*.rs"))]
    summary = {"schema": "boostregexrs.icu77-settings-probe-build.v1", "status": "passed",
               "scope": "development drivers built and linted; input compatibility is a separate run",
               "candidate": identity(candidate), "reference": identity(reference), "sources": sources,
               "rust_runtime_sources": runtime_sources, "rust_toolchain": toolchain,
               "library_checks": library_checks,
               "checked_tools": [identity(prefix / "bin" / name) for name in ("rustc", "cargo", "rustfmt", "clippy-driver")],
               "build_environment": {key: environment.get(key) for key in
                                     ("RUSTC", "RUSTDOC", "RUSTFLAGS", "CARGO_TARGET_DIR", "CARGO_INCREMENTAL",
                                      "LD_LIBRARY_PATH", "BOOSTREGEXRS_RUST_PREFIX")},
               "lint_environment": {key: lint_environment.get(key) for key in
                                    ("RUSTC", "SYSROOT", "RUSTFLAGS", "CARGO_TARGET_DIR", "LD_LIBRARY_PATH")},
               "native_libraries": [identity(native_prefix / "lib" / name) for name in
                                    ("libicui18n.a", "libicuuc.a", "libicudata.a")],
               "native_source_manifests": [identity(cache / "source-manifests" / name)
                                           for name in ("boost_1_89_0.tsv.xz", "icu.tsv.xz")]}
    save(output / "summary.json", summary)
    print(json.dumps({"status": "passed", "candidate": summary["candidate"], "reference": summary["reference"]}))
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--rust-cache", type=Path, default=REPO / "target/research/icu77-cloud")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--check-library", action="store_true", help="Check all prototype Rust sources, tests and native regression fixtures")
    args = parser.parse_args()
    build(args.cache.resolve(), args.rust_cache.resolve(), args.output.resolve(), args.check_library)


if __name__ == "__main__":
    main()
