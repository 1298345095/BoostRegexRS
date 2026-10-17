#!/usr/bin/env python3
"""Install the recorded official stable toolchain entirely inside the project.

The dated stable channel reproduces this measurement; it is not an MSRV promise.
Every component is verified against the pinned official channel manifest.
"""

import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tarfile
import tomllib

from prepare import DEFAULT_CACHE, REPO, download, write_json


DATE = "2026-10-15"
MANIFEST_SHA256 = "fb152be80975c194aa5fc684b2aec3a6e14e2b855efe2faa4e5f8ae6e590f463"
TARGET = "x86_64-unknown-linux-gnu"
COMPONENTS = ("rustc", "cargo", "rust-std", "rustfmt-preview", "clippy-preview")


def sha256(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def prepare_rust(cache):
    cache = cache.resolve()
    if platform.system() != "Linux" or platform.machine() != "x86_64":
        raise RuntimeError("The recorded local toolchain package targets Linux x86-64; use --system-rust elsewhere")
    directory = cache / "toolchain"
    directory.mkdir(parents=True, exist_ok=True)
    manifest = directory / "channel-rust-stable.toml"
    checksum = directory / "channel-rust-stable.toml.sha256"
    base = f"https://static.rust-lang.org/dist/{DATE}/"
    for name in (manifest, checksum):
        download(base + name.name, name)
    if sha256(manifest) != MANIFEST_SHA256 or checksum.read_text().split()[0] != MANIFEST_SHA256:
        raise RuntimeError("Official stable channel manifest checksum does not match the recorded toolchain")
    channel = tomllib.loads(manifest.read_text(encoding="utf-8"))
    if channel["date"] != DATE:
        raise RuntimeError("Stable channel date changed")
    components = {name: {**channel["pkg"][name]["target"][TARGET], "version": channel["pkg"][name]["version"]} for name in COMPONENTS}

    def fetch(item):
        name, component = item
        if not component["available"]:
            raise RuntimeError(f"Toolchain component unavailable: {name}")
        archive = directory / component["xz_url"].rsplit("/", 1)[1]
        download(component["xz_url"], archive)
        if sha256(archive) != component["xz_hash"]:
            raise RuntimeError(f"Official toolchain component checksum mismatch: {archive.name}")
        return archive

    with ThreadPoolExecutor(max_workers=len(components)) as pool:
        archives = list(pool.map(fetch, components.items()))
    prefix = directory / "install"
    marker = directory / "installed.json"
    identity = {"manifest_sha256": MANIFEST_SHA256, "target": TARGET, "components": {name: part["xz_hash"] for name, part in components.items()}}
    reused = marker.is_file() and json.loads(marker.read_text()) == identity
    if not reused:
        for archive in archives:
            with tarfile.open(archive) as stream:
                stream.extractall(directory, filter="data")
            source = directory / archive.name.removesuffix(".tar.xz")
            subprocess.run(["sh", str(source / "install.sh"), f"--prefix={prefix}", "--disable-ldconfig"], check=True, stdout=subprocess.DEVNULL)
        write_json(marker, identity)
    # Explicit local loader paths also work in restricted cloud process
    # environments whose Cargo children cannot resolve the tarball's $ORIGIN.
    # The verified compiler binaries themselves are not patched.
    for name in ("rustc", "rustdoc"):
        wrapper = directory / f"{name}-local.py"
        # Shell wrappers can discard Cargo's CARGO_BIN_EXE_<hyphenated-name>
        # entries. execve preserves the entire original process environment.
        arguments = ["/lib64/ld-linux-x86-64.so.2", "--library-path", str(prefix / "lib"), str(prefix / "bin" / name)]
        wrapper.write_text(f"#!{sys.executable}\nimport os, sys\nargs = {arguments!r}\nos.execve(args[0], args + sys.argv[1:], os.environ)\n", encoding="utf-8")
        wrapper.chmod(0o755)
    env = dict(os.environ)
    temporary = cache / "build/tmp"
    temporary.mkdir(parents=True, exist_ok=True)
    env.update({"PATH": str(prefix / "bin") + os.pathsep + env["PATH"],
                "CARGO_HOME": str(cache / "cargo-home"), "RUSTC": str(directory / "rustc-local.py"),
                "RUSTDOC": str(directory / "rustdoc-local.py"),
                "TMPDIR": str(temporary),
                "RUSTFLAGS": "-C link-arg=-fuse-ld=bfd"})
    versions = {}
    for name, command in (("rustc", [env["RUSTC"], "--version", "--verbose"]), ("cargo", [str(prefix / "bin/cargo"), "--version"])):
        versions[name] = subprocess.run(command, env=env, capture_output=True, text=True, check=True).stdout.strip()
    if "nightly" in versions["rustc"] or "beta" in versions["rustc"]:
        raise RuntimeError("Expected Rust stable")
    report = {"channel_date": DATE, "channel_manifest_url": base + manifest.name, "channel_manifest_sha256": MANIFEST_SHA256,
              "components": components, "actual": versions, "build_flags": {"RUSTFLAGS": env["RUSTFLAGS"], "compiler_loader": "explicit project-local lib directory"},
              "compiler_sha256": sha256(prefix / "bin/rustc"), "cargo_sha256": sha256(prefix / "bin/cargo")}
    write_json(cache / "rust-toolchain-manifest.json", report)
    print(versions["rustc"].splitlines()[0], flush=True)
    return env


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, default=DEFAULT_CACHE)
    args = parser.parse_args()
    prepare_rust(args.cache)
    print(f"Toolchain installed below {os.path.relpath(args.cache / 'toolchain', REPO)}")


if __name__ == "__main__":
    main()
