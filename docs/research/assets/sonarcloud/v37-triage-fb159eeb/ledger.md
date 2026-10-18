# V37 issue-by-issue source review

This is a review of the **91-issue / 20-security-issue observation** in
`../actions-39066906674/raw.zip`, member `sonar-issues.json`, collected at
2026-10-17 20:29:28 UTC. Every row below corresponds to one original issue key.
The raw flows remain in that ZIP; they are not copied into another response tree.
GitHub issue #18 owns the work. This document is a dated evidence ledger, not a
second task tracker or a record of service-side issue transitions.

The reviewed published source is
`fb159eeb4583727cc70db4b9e53f8329fd25d8b8`. Sonar's responses are
`live_pr_unpinned`; their analyzed commit is **not established**. The locations
below are the server's reported locations, with source symbols used where later
changes moved lines. Local source review does not prove that Sonar analyzed this
commit. Native reproduction and subsequent analysis still have separate gates.

## Security flows

All 20 recorded security issues were read with all their flow locations. Their
reported sources are CLI argument parsing or forwarding, although the server
flow text describes an HTTP request. These programs expose no HTTP/agent job
endpoint. The authority column records the actual invoking boundary; it does
not excuse a lower-trust data value selecting an unrelated operation.

**FP proposal** below means a source-supported recommendation for an individual
false-positive review. No authenticated Sonar disposition has been submitted.
The four saved rule responses provide rule identities, names and CWE mappings;
they do not contain full explanatory rule text. That detail limitation remains.

| Issue | Rule | Actual source → sink | Caller authority and source reasoning | Recommendation |
| --- | --- | --- | --- | --- |
| `AaFJ8Iqp-frh1mu1rilB` | S8705 | `tools/ci/native_rust.py`: `--target` → `native_checks` → `execute` / `subprocess.run` | The existing parser accepts the six ADR targets; CI selects a fixed matrix entry. Executable names and command structure are internal, and subprocess receives an argv list. | FP proposal for command injection; preserve the six-target selector and literal argv. |
| `AaFJ8Iqp-frh1mu1rilC` | S8707 | `native_rust.py`: `--output` → `Path.mkdir` | The developer explicitly chooses the report destination. It is created exclusively; case data does not select it. | FP proposal; retain external destination support and existing-output rejection. |
| `AaFJydFaKb2a573Ba8zs` | S8707 | `tools/dev/split_artifact.py`: `--directory` → `split` / `mkdir` | The CLI explicitly selects the transport directory. Part filenames are generated internally as `part-NNNN.bin`; this reported flow concerns directory creation. | FP proposal for this flow. It is not an assessment of every possible manifest-content path. |
| `AaFJwLqg5zVgo8XdQl5Z` | S8707 | `primary/archive_evidence.py`: `--output`, source metadata → `manifest.json` write | The destination is explicitly selected and created exclusively. Serialized source metadata is JSON content; it does not choose the fixed output filename. | FP proposal; retain exclusive output creation and archive-byte verification. |
| `AaFJwL585zVgo8XdQl5k` | S8707 | `primary/generate_review_contexts.py`: `--output` → `mkdir` | The developer selects the destination. Generated filenames are fixed; generated text and case IDs remain TSV values. | FP proposal; no repository-only path restriction. |
| `AaFJwL6H5zVgo8XdQl5m` | S8707 | `primary/historical_identical.py`: `--output` → `relate` / `mkdir` | This argument explicitly authorizes the output directory. Historical keys and current key rows do not determine it. | FP proposal for traversal; historical-evidence overwrite policy is a separate behavior obligation. |
| `AaFJufvkdzrnai1Efwls` | S8701 | `cloud/reference.py`: `--cxx` → `build_reference` → `prepare.run_logged` / `Popen` | Choosing the compiler is an intentional development capability. Arguments are a list and the current helper explicitly uses `shell=False`; no corpus value selects the executable. | FP proposal. Preserve custom compiler paths; use the existing literal-argument regression. |
| `AaFJr_A0BynKBKHRtWSv` | S8705 | `tools/dev/cargo.py`: remaining CLI arguments → verified Cargo executable | This is deliberately a Cargo argument-forwarding wrapper. The invoking developer is authorized to choose Cargo operations and flags; no shell evaluates them. | FP proposal; an arbitrary Cargo-option allowlist would break the wrapper's purpose. |
| `AaFJr_BBBynKBKHRtWSw` | S8705 | `tools/dev/staged_git_payload.py`: `--path` → `git ls-files`, then indexed object digest → `git cat-file` | `--` prevents option injection and the caller may read staged blobs. However, Git pathspec expansion breaks the helper's separate promise of one exact filename: requesting literal `item?.txt` returned `item1.txt` in an isolated reproduction. | **Source fix required first:** use literal pathspec semantics and deliberate exact-entry handling. Then review the injection allegation separately; no remote disposition is claimed. |
| `AaFJr-5bBynKBKHRtWSs` | S8705 | `cloud/rust_loader.py`: Cargo/compiler argv → `os.execve` | The verified toolchain setup supplies the prefix; the versioned rustc/rustdoc launcher supplies the tool name. Forwarding compiler argv and the caller's complete environment is this wrapper's purpose. | FP proposal; retain literal argv and compiler environment semantics. |
| `AaFJiPGXCiUwZk3hyg9O` | S2083 | `cloud/prepare.py`: `--cache` → internal metadata paths → `write_json` | The developer selects the cache. Internal code appends metadata filenames; downloaded archive content does not choose this write path. Archive extraction has its own data filter and identity checks. | FP proposal for this metadata-write flow; retain external cache paths. |
| `AaFJiPGXCiUwZk3hyg9Q` | S8701 | `prepare.py` and `cloud/reference.py`: `--cc` / `--cxx` → `command_output([compiler, '--version'])` | Both recorded flows intentionally invoke the selected compiler. The argv list is not a shell command string. | FP proposal for both flows; retain custom compiler selection and finite child deadlines. |
| `AaFJwLow5zVgo8XdQl5W` | S8707 | `generate_review_contexts.py`: `--contexts` → `compare.sha256` / `open` | The developer explicitly selects the context file to read and identify. Context contents are not used to select this filename. | FP proposal; hashing a selected external input file is supported. |
| `AaFJiPBVCiUwZk3hyg8N` | S8707 | `primary/compare.py`: input/reference/candidate CLI paths → `rows` / `open` | The comparator reads files chosen by the invoking developer or test harness. TSV fields do not create additional read paths. | FP proposal; keep independent inputs and external temporary fixtures supported. |
| `AaFJiPBVCiUwZk3hyg8O` | S8707 | `primary/compare.py`: `--output` → report write | This flag explicitly selects the report file. Decoded keys, IDs and error markers are serialized values, not path components. | FP proposal; keep caller-selected destinations. |
| `AaFJiPCJCiUwZk3hyg8p` | S8707 | `primary/export/data_format.py`: positional `data` → `read_data` / `read_bytes` | The CLI explicitly selects the binary input. The reader validates the fixed data format; decoded values do not select other input filenames. | FP proposal for this file-open flow. |
| `AaFJiPCJCiUwZk3hyg8o` | S8707 | `data_format.py`: `--contexts-output` → parent creation and JSON write | The developer explicitly selects the diagnostic report. Decoded context tables remain JSON values. | FP proposal; retain external output-file support. |
| `AaFJiPB2CiUwZk3hyg8Z` | S2083 | `primary/export/generate.py`: output directory → fixed `root-icu77.json` / `save_json` | The output-directory capability is explicit. Source-data values populate a provenance document; internal names choose the files. | FP proposal; preserve source/data identity checks and `--check` behavior. |
| `AaFJiPBdCiUwZk3hyg8R` | S8707 | `generate_cases.py` and `generate_review_contexts.py`: `--contexts` → `contexts` / `read_text` | Both recorded flows read the developer-selected context report. Parsed entries become Unicode test data and case IDs, not additional paths. | FP proposal for both flows; retain deterministic generation and input-file identity. |
| `AaFJiPBdCiUwZk3hyg8Q` | S8707 | `primary/generate_cases.py`: `--output` → `mkdir` | The explicit destination contains internally named TSV/JSON files. Generated values do not choose destination filenames. | FP proposal; no arbitrary checkout jail. |

The existing `tools/quality/test_cli_trust_boundaries.py` exercises literal
metacharacter forwarding, an output outside the checkout, and failed-child
reporting for the common cloud helper. These three checks support that helper;
they are not claimed to test every program in this table.

## Other 71 issues

These are source-level code-quality recommendations. **None is marked remotely
resolved.** The table records the concrete work and the behavior it must preserve.
Rule descriptions for these other rule keys were not retrieved by the archived
four-rule access probe. The recorded issue message and source are the available
basis; missing full rule detail is not presented as a completed service review.

Paths in this table are relative to `tools/icu-probe/`, except explicit
`tools/dev/` paths. Line numbers are the reported analysis locations.

| Issue | Rule | Source location / concrete work |
| --- | --- | --- |
| `AaFJwLqg5zVgo8XdQl5X` | python:S1192 | `primary/archive_evidence.py:45`: name the repeated `summary.json` filename without changing archive members. |
| `AaFJwLqg5zVgo8XdQl5Y` | python:S9154 | `primary/archive_evidence.py:56`: combine the compression/tar contexts, preserving their entry and reverse close order and identical archive bytes. |
| `AaFJwLow5zVgo8XdQl5V` | python:S3776 | `primary/compare.py:98`, `compare`: separate input alignment, per-row classification and ordering aggregation; preserve full keys, counters and failure outcomes. |
| `AaFJwLt85zVgo8XdQl5b` | cpp:S112 | `primary/export/export-nfd.cpp:18`: use a probe-specific failure type while preserving the requirement message and process exit behavior. |
| `AaFJwLt85zVgo8XdQl5c` | cpp:S1659 | `primary/export/export-nfd.cpp:44`: give each version array its own declaration, retaining zero initialization. |
| `AaFJwLsK5zVgo8XdQl5a` | python:S3776 | `primary/generate_cases.py:177`, `identical_directed`: separate common-run, BOCSU and NFD case families without changing yield order or generated values. |
| `AaFJwL6H5zVgo8XdQl5l` | python:S3776 | `primary/historical_identical.py:25`, `relate`: separate full-key and pair comparisons; preserve all 13 root keys, 78 pairs and historical cross-locale difference accounting. |
| `AaFJwL5y5zVgo8XdQl5g` | cpp:S3628 | `primary/oracle.cpp:112`: convert metadata text to raw literals with byte-identical JSON output. |
| `AaFJwL5y5zVgo8XdQl5h` | cpp:S5945 | `primary/oracle.cpp:114`: use `std::array` for the fixed attribute list, preserving its order and values. |
| `AaFJwL5y5zVgo8XdQl5i` | cpp:S6005 | `primary/oracle.cpp:121`: use a const-reference structured binding for each attribute pair; keep C++17 and metadata fields unchanged. |
| `AaFJwL5y5zVgo8XdQl5j` | cpp:S112 | `primary/oracle.cpp:128`: keep metadata write failures distinct and preserve their message/exit behavior when introducing the probe error type. |
| `AaFJwL4F5zVgo8XdQl5f` | python:S3776 | `primary/run_identical.py:28`, `run`: separate environment/build setup from corpus replay and summary assembly; retain failure evidence and separate empty exceptions. |
| `AaFJwL4F5zVgo8XdQl5d` | python:S1192 | `primary/run_identical.py:39`: name `install/icu/lib`, retaining the local runtime-library selection. |
| `AaFJwL4F5zVgo8XdQl5e` | python:S1192 | `primary/run_identical.py:128`: name `summary.json`, retaining every group's output path. |
| `AaFJr_AmBynKBKHRtWSu` | python:S3776 | `tools/dev/update_capabilities.py:56`, `inventory`: split collection by upstream capability family; compare the complete emitted ID set and ownership. |
| `AaFJr_AmBynKBKHRtWSt` | python:S1192 | `tools/dev/update_capabilities.py:106`: name the upstream `libs/regex/test` directory; preserve every discovered test ID. |
| `AaFJiPGXCiUwZk3hyg9N` | python:S1192 | `cloud/prepare.py`, `fetch_and_verify` (reported line 80 moved): name the repeated `.json` suffix without changing checksum/report filenames. |
| `AaFJiPGXCiUwZk3hyg9M` | python:S1192 | `cloud/prepare.py`, `fetch_and_verify` (reported line 82 moved): name `SHASUM512.txt`; preserve the official URL, filename and digest checks. |
| `AaFJiPGHCiUwZk3hyg9K` | python:S1192 | `cloud/reference.py:35`: name `environment-manifest.json`; retain the preparation prerequisite and evidence identities. |
| `AaFJiPF_CiUwZk3hyg9E` | python:S1192 | `cloud/replay.py:68`: name `sortkeys.tsv`; preserve historical/cloud source separation. |
| `AaFJiPF_CiUwZk3hyg9G` | python:S1192 | `cloud/replay.py:169`: name `cross-platform-summary.json`; preserve destination filenames and summary semantics. |
| `AaFJiPGfCiUwZk3hyg9R` | python:S3776 | `cloud/rust_toolchain.py:33`, `prepare_rust`: separate manifest verification, acquisition and installation/reporting; retain the dated stable identity and caller environment. |
| `AaFJiPBVCiUwZk3hyg8G` | python:S6353 | `primary/compare.py:16`: replace the first `[0-9]` suffix class with `\d` only with `re.ASCII`; preserve rejection of non-ASCII error digits. |
| `AaFJiPBVCiUwZk3hyg8H` | python:S6353 | `primary/compare.py:16`: apply the same ASCII-preserving change to the second suffix class and test both marker families. |
| `AaFJiPBVCiUwZk3hyg8I` | python:S3776 | `primary/compare.py:51`, `decode`: separate marker classification from raw-key/wrapper validation; never relabel an invalid oracle as a pass. |
| `AaFJiPBVCiUwZk3hyg8J` | python:S3776 | `primary/compare.py:72`, `input_error`: separate UTF-8/UTF-16/UTF-32 validation, preserving all rejection labels and original unit semantics. |
| `AaFJiPBVCiUwZk3hyg8L` | python:S5713 | `primary/compare.py:204`: remove redundant `UnicodeError` from the tuple because `ValueError` already catches it; retain malformed-input output and exit 2. |
| `AaFJiPBlCiUwZk3hyg8V` | python:S3776 | `primary/export/compare_ce_traces.py:25`, `main`: separate input preparation, process execution and complete CE comparison; preserve long fields and failure propagation. |
| `AaFJiPBlCiUwZk3hyg8U` | python:S1192 | `primary/export/compare_ce_traces.py:46`: name `inputs-u16.tsv`; preserve exact corpus transport. |
| `AaFJiPBlCiUwZk3hyg8S` | python:S1192 | `primary/export/compare_ce_traces.py:64`: name `reference-ces.tsv`; preserve full reference CE output. |
| `AaFJiPBlCiUwZk3hyg8T` | python:S1192 | `primary/export/compare_ce_traces.py:71`: name `candidate-traces.jsonl`; preserve its stderr trace destination. |
| `AaFJiPBuCiUwZk3hyg8W` | cpp:S112 | `primary/export/export-root.cpp:41`: introduce a precise exporter failure type without altering failed requirement messages or native exit status. |
| `AaFJiPBuCiUwZk3hyg8Y` | cpp:S1659 | `primary/export/export-root.cpp:185`: separate version-array declarations, preserving initialization and runtime reads. |
| `AaFJiPCBCiUwZk3hyg8a` | cpp:S112 | `primary/export/trace-root.cpp:36`: preserve invalid UTF-16 field-width rejection while using a trace-input error type. |
| `AaFJiPCBCiUwZk3hyg8b` | cpp:S112 | `primary/export/trace-root.cpp:40`: preserve nonhex UTF-16 rejection and message. |
| `AaFJiPCBCiUwZk3hyg8c` | cpp:S112 | `primary/export/trace-root.cpp:46`: preserve trailing-comma rejection and message. |
| `AaFJiPCBCiUwZk3hyg8d` | cpp:S112 | `primary/export/trace-root.cpp:55`: preserve wrong-runtime-version failure and process status. |
| `AaFJiPCBCiUwZk3hyg8e` | cpp:S112 | `primary/export/trace-root.cpp:62`: preserve root data/settings validation and failure output. |
| `AaFJiPCBCiUwZk3hyg8g` | cpp:S3628 | `primary/export/trace-root.cpp:81`: use a raw literal for CE32 metadata with byte-identical JSON. |
| `AaFJiPCBCiUwZk3hyg8f` | cpp:S3628 | `primary/export/trace-root.cpp:82`: use a raw literal for FCD16 metadata with byte-identical JSON. |
| `AaFJiPCBCiUwZk3hyg8h` | cpp:S112 | `primary/export/trace-root.cpp:91`: preserve ICU iterator error text and nonzero exit. |
| `AaFJiPCBCiUwZk3hyg8i` | cpp:S3776 | `primary/export/trace-root.cpp:107`, `traceBatch`: extract batch-line parsing and CE emission; compare complete traces, including failures. |
| `AaFJiPCBCiUwZk3hyg8j` | cpp:S112 | `primary/export/trace-root.cpp:111`: preserve the batch runtime-version failure. |
| `AaFJiPCBCiUwZk3hyg8k` | cpp:S112 | `primary/export/trace-root.cpp:118`: preserve the batch root-settings failure. |
| `AaFJiPCBCiUwZk3hyg8l` | cpp:S112 | `primary/export/trace-root.cpp:134`: preserve malformed TSV schema rejection and message. |
| `AaFJiPCBCiUwZk3hyg8m` | cpp:S112 | `primary/export/trace-root.cpp:147`: preserve batch iterator error handling. |
| `AaFJiPCBCiUwZk3hyg8n` | cpp:S112 | `primary/export/trace-root.cpp:159`: preserve failed batch-input I/O handling. |
| `AaFJiPBdCiUwZk3hyg8P` | python:S3776 | `primary/generate_cases.py:117`, `contexts`: separate trie traversal and emitted case families without changing order, cycle rejection or context coverage. |
| `AaFJiPCZCiUwZk3hyg8u` | cpp:S6009 | `primary/oracle.cpp:38`, `units`: use a view through the coupled parser helpers only while caller storage remains alive; retain embedded NUL and malformed-width behavior. |
| `AaFJiPCZCiUwZk3hyg8v` | cpp:S6009 | `primary/oracle.cpp:52`, `decode`: retain input ownership at the caller and exact unit decoding when adopting a view. |
| `AaFJiPCZCiUwZk3hyg8w` | cpp:S5271 | `primary/oracle.cpp:69`, `check_versions`: **FP proposal, not `noreturn`**. The supported matching-version path returns normally; adding the attribute would contradict that behavior. Confirm it in the fresh native smoke. |
| `AaFJiPCZCiUwZk3hyg8x` | cpp:S1659 | `primary/oracle.cpp:71`: separate all four version-array declarations and retain zero initialization. |
| `AaFJiPCZCiUwZk3hyg8y` | cpp:S112 | `primary/oracle.cpp:78`: retain mismatch-only version failure when introducing a probe error type. |
| `AaFJiPCZCiUwZk3hyg8z` | cpp:S3776 | `primary/oracle.cpp:82`, `main`: separate option parsing, metadata and record handling; preserve real Boost calls, complete keys and the original empty-input process outcome. |
| `AaFJiPCZCiUwZk3hyg82` | cpp:S886 | `primary/oracle.cpp:88`: make option/value cursor advancement explicit; retain every option, missing-value rejection and literal argument. |
| `AaFJiPCZCiUwZk3hyg83` | cpp:S112 | `primary/oracle.cpp:103`: preserve collator-creation failure text and status. |
| `AaFJiPCZCiUwZk3hyg84` | cpp:S112 | `primary/oracle.cpp:106`: preserve root normalization-setting validation. |
| `AaFJiPCZCiUwZk3hyg81` | cpp:S1141 | `primary/oracle.cpp:143`: move per-record processing into a function while retaining each invalid-input row and process-level reference failures. |
| `AaFJiPCZCiUwZk3hyg80` | cpp:S134 | `primary/oracle.cpp:157`: extract adjacent-pair comparison, preserving the ICU error check and exact three-valued ordering output. |
| `AaFJiPCZCiUwZk3hyg85` | cpp:S112 | `primary/oracle.cpp:157`: preserve adjacent-comparison ICU failure text and status. |
| `AaFJiPCZCiUwZk3hyg86` | cpp:S872 | `primary/oracle.cpp:158`: use a named integer sign conversion with explicit negative/zero/positive results; preserve all three emitted values. |
| `AaFJiPCZCiUwZk3hyg87` | cpp:S112 | `primary/oracle.cpp:165`: preserve invalid ICU key-length rejection. |
| `AaFJiPCZCiUwZk3hyg88` | cpp:S112 | `primary/oracle.cpp:168`: preserve changed key-preflight rejection. |
| `AaFJiPCZCiUwZk3hyg89` | cpp:S3358 | `primary/oracle.cpp:186`: extract the input-format error-label selection and preserve all three exact labels. |
| `AaFJiPCZCiUwZk3hyg8-` | cpp:S112 | `primary/oracle.cpp:190`: preserve final stream I/O failure and nonzero process status. |
| `AaFJiO_ZCiUwZk3hyg8F` | python:S3776 | `primary/reference_process.py:100`, `run_reference`: separate batch process lifecycle, failure isolation and evidence aggregation; retain every failed/signal range and original input order. |
| `AaFJiPCSCiUwZk3hyg8r` | python:S1192 | `primary/run.py:45`: name `install/icu/lib`; retain native/candidate environment separation. |
| `AaFJiPCSCiUwZk3hyg8s` | python:S1192 | `primary/run.py:98`: name `summary.json`; preserve all corpus summaries and their output locations. |
| `AaFJiPEKCiUwZk3hyg9A` | cpp:S3628 | `reference/empty-keys.cpp:67`: convert compiler metadata to a raw literal with identical output, keeping ADR-0005 expectation labeling. |
| `AaFJiPF2CiUwZk3hyg9C` | cpp:S112 | `reference/probe.cpp:126`: preserve actual Boost/ICU/Unicode/CLDR/data version validation. |
| `AaFJiPF2CiUwZk3hyg9D` | cpp:S112 | `reference/probe.cpp:146`: preserve failed output-stream detection and nonzero status. |

## Recheck the ledger's coverage

This verifies row identity and coverage, not the truth of a proposed disposition:

```sh
timeout --kill-after=2s 20s python3 -B - <<'PY'
from pathlib import Path
import json
import re
from zipfile import ZipFile

root = Path('docs/research/assets/sonarcloud')
with ZipFile(root / 'actions-39066906674/raw.zip') as archive:
    issues = json.loads(archive.read('sonar-issues.json'))['payload']['issues']
expected = {issue['key'] for issue in issues}
rows = re.findall(r'^\| `(Aa[^`]+)` \|',
                  (root / 'v37-triage-fb159eeb/ledger.md').read_text(), re.MULTILINE)
assert len(rows) == len(set(rows)) == len(expected) == 91
assert set(rows) == expected
assert sum(issue['rule'].startswith('pythonsecurity:') for issue in issues) == 20
print('91 unique issue rows; all 20 security issues included; no service disposition implied')
PY
```
