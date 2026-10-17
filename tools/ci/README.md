# Native platform evidence

`native-rust.yml` runs the committed pure Rust collation crate on all six
ADR-0002 baseline platforms. The initial matrix verifies root PRIMARY/IDENTICAL
research code and its full-key regression fixtures. As later committed collation
mechanisms add tests, the same workflow executes those tests. Its success does
not close the full library's six-platform acceptance rows.

Each job installs the current stable toolchain **for that native host**, compiles
and executes an architecture probe, and checks the runner architecture and glibc
requirement. It then runs formatting, Clippy with warnings denied, executable
tests, doctests and documentation generation. The source tree, actual Rust
version, runner image, original command output and data/source hashes accompany
the result. Every failing job remains failed; artifacts are uploaded even on
failure and must be retained in the repository before their 14-day expiry.

| Baseline system | Runner label | Rust host target |
| --- | --- | --- |
| Windows Server 2025 x64 | `windows-2025` | `x86_64-pc-windows-msvc` |
| Windows 11 ARM64 | `windows-11-arm` | `aarch64-pc-windows-msvc` |
| Ubuntu 24.04 x64 glibc | `ubuntu-24.04` | `x86_64-unknown-linux-gnu` |
| Ubuntu 24.04 ARM64 glibc | `ubuntu-24.04-arm` | `aarch64-unknown-linux-gnu` |
| macOS 15 Intel | `macos-15-intel` | `x86_64-apple-darwin` |
| macOS 15 Apple Silicon | `macos-15` | `aarch64-apple-darwin` |

The runner mapping was checked against the
[official GitHub runner reference](https://docs.github.com/en/actions/reference/runners/github-hosted-runners)
on 2026-10-17. Runtime evidence, not this configuration table, establishes which
jobs actually ran successfully. Hosted image and stable compiler revisions can
change; each run records their actual values.

On one of these native systems with rustup available, for example:

```sh
rustup toolchain install stable-x86_64-unknown-linux-gnu --profile minimal --component rustfmt --component clippy
python3 -B tools/ci/native_rust.py --target x86_64-unknown-linux-gnu \
  --output docs/research/assets/platforms/local-native-rust-NEW-RUN
```

Choose a new evidence directory for every observation. Build products stay under
`target/native-rust`; authored scripts and the architecture probe are tracked.
The complete native Boost/ICU differential and performance/memory matrices remain
separate work until their actual evidence is available on each platform.
