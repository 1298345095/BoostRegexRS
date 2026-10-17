# Paused implementation checkpoint

The user paused implementation on 2026-10-17 and requested tickets for the
remaining work. These archives preserve existing sources and evidence. Archiving,
compression and transport checks did not compile, run, fix or accept the
implementation. Original working-tree files remain in place.

Base commit: `1b0149efb649bcec7b5d6c4c0be2f7e403189cea` on
`work/root-primary-cloud`.

## Archive inventory

| Archive | Preserved content | Integrity record |
| --- | --- | --- |
| `paused-sources.tar.xz` | 629 changed/untracked source, test, tool and locale-data files, with repository-relative paths; build/cache and raw-result directories excluded | `manifest.json` |
| `selected-evidence.tar.xz` | 433 evidence files: the retained byte-reference run, six native CI ZIPs and metadata, second Sonar observation, ICU resource export, locale diagnostics, first failing locale configuration, its input and full-run summary | `evidence-manifest.json` |
| `locale-failed-run/raw.tar.xz` (transported in parts) | All 21,677 files retained from locale run `2026-10-17T124321.329888Z`, including its successful groups and the failing group; 2,482,952,994 uncompressed file bytes | `locale-failed-run/manifest.json.xz` and `verification.json` |

The complete retained locale run is now archived; its successful groups no
longer require a separate archival pass. The earlier 433-file selection remains
useful and is not the complete raw-run archive. Preserving all files from that
run does not make the run complete or passing: its original summary retains
`differences_or_incomplete`, two mismatches, and 451 completed configurations
out of 538. No experiment was rerun.

## Transport files

The raw locale archive is **12,901,312 bytes**, SHA-256
`420e9a99cd2f08aa0920a77cc4c796f484099ca5466fd85d0e60584fd68e4d97`.
`locale-failed-run/raw.tar.xz.parts/` contains its transport manifest and seven
ordered parts: six of 2,097,152 bytes and one of 318,400 bytes. The tracked
`tools/dev/split_artifact.py` helper verified every part and the combined
archive identity when splitting it.

| Metadata transport file | Compressed bytes | Reconstructed bytes |
| --- | ---: | ---: |
| `locale-failed-run/manifest.json.xz` | 311,652 | 4,396,029 |
| `locale-failed-run/summary.json.xz` | 38,120 | 3,054,391 |

Both metadata files were compressed losslessly and checked against their
readable originals. The original `raw.tar.xz`, `manifest.json` and
`summary.json` remain locally available and **must remain unstaged**; use their
parts/compressed forms for transport. Every intended tracked checkpoint blob
is at most 2 MiB. `verification.json` records the earlier 21,677-file archive
verification; splitting did not rerun implementation validation.

## Validation state

- The root byte engine has 35 passing tests reported in the original execution
  records. `cargo check` and direct `rustfmt`/`clippy-driver` checks ran; their raw
  output was not archived. Ordinary `cargo fmt`/`cargo clippy` failed at their
  launcher because this execution environment lacks `/proc/self/exe`. The
  checkpoint supplies no missing validation evidence.
- The locale FCD correction in `data77.rs`, `cursor77.rs` and `ce77.rs` was written
  but has **not been formatted, built or tested**. Its older candidate produced
  the two retained full-key differences. The archived correction is unverified.
- The byte reference protocol, generator and adapter contain changes made after
  the retained native-reference run. A fresh run is required before using those
  changes as acceptance evidence. The Rust adapter is not synchronized with the
  final byte checkpoint API.
- Published root PRIMARY and IDENTICAL evidence remains unchanged. The six
  native CI jobs for commit `1b0149ef` passed 19 research-crate tests per target;
  this is not whole-library acceptance.

## Reassemble and verify

Run these commands from the repository containing the checkpoint, using
Python 3.12 or newer. Reassembly uses a new `locale-failed-run/reassembled/`
directory and exclusive file creation, leaving the readable originals intact.
Choose another new directory if that destination already exists.

First verify the parts:

```sh
python3 -B tools/dev/split_artifact.py verify --manifest docs/development/tickets/checkpoint/locale-failed-run/raw.tar.xz.parts/manifest.json
```

Verify and decompress the metadata, checking both compressed and original bytes:

```sh
python3 -B - <<'PY'
import hashlib, lzma, pathlib

base = pathlib.Path('docs/development/tickets/checkpoint/locale-failed-run')
destination = base / 'reassembled'
destination.mkdir(exist_ok=False)
expected = {
    'manifest.json': (
        311652, '3027c717e0c52dd5e1618aa342dec6da4a27a3d3ba3455e124ab2287a8b5e7c9',
        4396029, '43fd8957e2f3dcc1bf54e994640ffa311258d3013e01ff93288999987174b2b4'),
    'summary.json': (
        38120, '8c9b33b32752cbb3b325cd2a8f3fe2c34dec68521d425d12e0aa4c2cd6f65874',
        3054391, '9b2fcc06a4293982493f44cbfade7782db9df782caee0e50942e32ea97d464eb'),
}
for name, (packed_size, packed_sha, plain_size, plain_sha) in expected.items():
    packed = (base / (name + '.xz')).read_bytes()
    assert len(packed) == packed_size
    assert hashlib.sha256(packed).hexdigest() == packed_sha
    plain = lzma.decompress(packed)
    assert len(plain) == plain_size
    assert hashlib.sha256(plain).hexdigest() == plain_sha
    with (destination / name).open('xb') as output:
        output.write(plain)
    print('Reconstructed', name, plain_size, plain_sha)
PY

python3 -B tools/dev/split_artifact.py join --manifest docs/development/tickets/checkpoint/locale-failed-run/raw.tar.xz.parts/manifest.json --output docs/development/tickets/checkpoint/locale-failed-run/reassembled/raw.tar.xz
```

Verify archive identities and every file's recorded size and SHA-256 before
restoration. This reads the full raw archive but performs no implementation test:

```sh
python3 -B - <<'PY'
import hashlib, json, pathlib, tarfile

base = pathlib.Path('docs/development/tickets/checkpoint')
for folder, name in (
    (base, 'manifest.json'),
    (base, 'evidence-manifest.json'),
    (base / 'locale-failed-run/reassembled', 'manifest.json'),
):
    manifest = json.loads((folder / name).read_text())
    spec = manifest['archive']
    archive = folder / (spec['path'] if isinstance(spec, dict) else spec)
    expected_sha = spec['sha256'] if isinstance(spec, dict) else manifest['archive_sha256']
    expected_size = spec['bytes'] if isinstance(spec, dict) else manifest['archive_bytes']
    assert archive.stat().st_size == expected_size
    with archive.open('rb') as stream:
        assert hashlib.file_digest(stream, 'sha256').hexdigest() == expected_sha
    records = {record['path']: record for record in manifest['files']}
    seen = set()
    with tarfile.open(archive, 'r|xz') as source:
        for member in source:
            assert member.isfile() and member.name in records and member.name not in seen
            record = records[member.name]
            assert member.size == record.get('size', record.get('bytes'))
            with source.extractfile(member) as stream:
                assert hashlib.file_digest(stream, 'sha256').hexdigest() == record['sha256']
            seen.add(member.name)
    assert seen == set(records)
    print('Verified', len(records), 'files in', archive)
PY
```

## Restore into a separate checkout

After verification, create a new checkout at the recorded base. The following
commands restore source changes and evidence there, leaving the current working
tree alone. Raw-run members have run-relative paths, unlike the other two
archives' repository-relative paths.

```sh
git worktree add --detach ../BoostRegexRS-checkpoint-restore 1b0149efb649bcec7b5d6c4c0be2f7e403189cea

python3 -B - <<'PY'
import pathlib, tarfile

base = pathlib.Path('docs/development/tickets/checkpoint').resolve()
checkout = pathlib.Path('../BoostRegexRS-checkpoint-restore').resolve()
for name in ('paused-sources.tar.xz', 'selected-evidence.tar.xz'):
    with tarfile.open(base / name, 'r:xz') as source:
        source.extractall(checkout, filter='data')
run = checkout / 'docs/research/assets/icu77-locales/runs/2026-10-17T124321.329888Z'
run.mkdir(parents=True, exist_ok=True)
with tarfile.open(base / 'locale-failed-run/reassembled/raw.tar.xz', 'r:xz') as source:
    source.extractall(run, filter='data')
print('Restored checkpoint into', checkout)
PY
```

Review the restored manifests and source diff before building. The backlog owns
follow-up implementation validation. Implementation remains paused until the
user resumes it.

## Files to track

Track the five top-level checkpoint files (`README.md`, `manifest.json`,
`evidence-manifest.json`, `paused-sources.tar.xz`, `selected-evidence.tar.xz`) and
these locale files:

- `locale-failed-run/raw.tar.xz.parts/manifest.json` and its seven `part-*.bin` files
- `locale-failed-run/manifest.json.xz`
- `locale-failed-run/summary.json.xz`
- `locale-failed-run/verification.json`

Leave the three oversized locale originals and any `reassembled/` directory
unstaged. Use these explicit paths when staging rather than the whole checkpoint
directory.
