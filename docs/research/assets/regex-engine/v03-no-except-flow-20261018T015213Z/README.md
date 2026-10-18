# Preserve returned compilation outcomes across native operations

This follow-up closes a concrete false-pass path in the development reference.
It records new native executions and comparison evidence. V03 and complete
library acceptance remain open.

## Source mechanism and result lifetime

The reference uses the official Boost 1.89.0 sources verified by the
[fresh V01 environment](../v01-20261017T233138Z/README.md). In
`boost/regex/v5/basic_regex_parser.hpp::fail`, the parser stores its first error
status even when `no_except` suppresses the exception. Its nesting guard stores
`error_complexity` (18) after 400 nested groups. `basic_regex::status()` exposes
the returned object's status; `mark_count()` exposes its actual capture count.

`perl_matcher_common.hpp::construct_init` subsequently rejects an invalid regex
object with `std::invalid_argument`. Search and full match use that matcher;
iteration initializes through search, replacement initializes an iterator, and
the standalone formatter first searches. Thus the later exception alone cannot
distinguish an ordinary syntax failure from a resource rejection during the
preceding `no_except` compilation.

The reference now follows one shared lifetime:

1. Snapshot `mark_count` and `status` immediately after `assign` returns.
2. Execute the requested operation with that same object and preserve its actual
   result or exception.
3. For noncompile operations following a returned nonzero status, append exactly
   `preceding_compile: {mark_count, compile_status}` in the common row writer.

This does not turn the earlier return into an exception or invent a compilation
position. Ordinary compilation exceptions retain their own code and position.
The later invalid-object exception keeps its `operation_error` category, null
position and complete native message bytes. A successful compilation adds no
preceding-failure field.

The strict validator checks the nested fields, integer types, nonzero status,
compatible result lifetime and `no_except` input flag. The comparator examines
the preceding resource status before comparing the later operation. For ordinary
syntax statuses, both preceding fields participate in the operation-error
comparison. Resource observations remain separate under
[ADR-0003](../../../../adr/0003-resource-contract-and-release-acceptance.md).

## Actual execution and comparisons

`resource_cases.py --no-except-flow-only` defines 18 inputs independently of any
candidate output. The two direct compile probes record resource status 18 and
ordinary syntax status 8. Each resulting invalid object is then exercised
through `search`, `match`, `iterate`, `format` and `replace`. Five valid
`no_except` operations and one independent invalid-match-policy case complete
the control set.

The [flow verification](retained/summary.json) passed for all 18 before/after
records. All ten later invalid-object errors were preserved byte-for-byte and
gained the exact compiled-object outcome observed by their separate native
compile probe. Both compiled objects reported `mark_count` 18446744073709551615
on this x86-64 build; that native value was retained. Eight controls were unchanged.

The collector returned 0 with 7 `ok` and 11 `operation_error` records: that is
complete protocol collection, not a compatibility verdict. The independent
comparison of deliberately identical files still returned 1:

| Classification | Corrected 18 rows | Earlier 18 rows |
| --- | ---: | ---: |
| Reference resource observation | 6 | 1 |
| Incomplete reference observation | 0 | 10 |
| Ordinary complete-field pass | 6 | 6 |
| Matched ordinary operation rejection | 6 | 1 |

The corrected resource total includes one returned compile status and the five
operations following that same status. The ordinary syntax object remains
distinct from the resource object. These deliberate self-comparisons exercise
the classifier; no Rust candidate was executed in this follow-up.

Historical incomplete rows remain readable. The unverified condition is limited
to a noncompile operation with `no_except`, `operation_error` category
`invalid_argument`, and no preceding compile outcome. The comparator does not
infer a missing error code. Ordinary match-policy rejections and rows without
`no_except` are unaffected by that condition.

Additional native regression checks passed:

| Corpus | Result |
| --- | --- |
| Earlier 12 resource/ordinary cases | Six native phase/code corrections remain valid; five other records unchanged; one ordinary no-except error gains its preceding status 8 |
| Earlier one-case stack probe | Actual code 19, position 0, phase `match` remains correctly classified |
| Earlier 13 normal cases | 12 complete-field passes and one matched compile rejection between earlier and current native outputs |
| Unit tests | 13 reference-failure tests and nine complete-result comparison tests passed |

The unit tests deliberately alter or omit preceding outcomes, change their
status/count, add invented fields or positions, use invalid types, attach them
to impossible lifetimes, and mismatch input flags. Identical resource failures
are tested for all five later operations and all four declared resource codes.
The native preceding-compilation probe actually exercises code 18; the other
three preceding resource codes have protocol tests rather than equivalent native
compile-failure execution evidence.

## Identities and dependency repair

The compiler was GCC 13.3.0 (`Ubuntu 13.3.0-6ubuntu2~24.04`) on Linux x86-64.
The build used C++17, `-O2 -g0 -Wall -Wextra -Werror -pthread` and the unchanged
verified Boost include directory. No Boost resource macros were overridden.
Compiler, ELF, linked-library paths, literal command argv, deadlines, separate
streams, native metadata and process statuses are retained with this run.

| Binary | SHA-256 |
| --- | --- |
| Earlier phase-aware reference | `6d765d61e1bd6441b8b75510bfdadb2a1233cc53382c631a1222f250cdc26ca7` |
| Current reference with preceding outcome | `05301742f19863fa8bd7ee328983e2df5924de1da0aa37e99fce1ffb8e45a97e` |

The earlier binary remains in the original 105-member archive. The current
binary, current source and the new raw executions are in `retained/raw.tar.xz`;
the adjacent manifest and verification record identify every member.

`run.py` now imports `HEADER` directly from `protocol.py`. An actual isolated
collector run used only these two Python source files with no `generate_cases.py`
present. Python ignored environment configuration and user site packages. It
successfully collected all 18 corrected native rows. The exact two source
identities are recorded in the archive's `run/collector-closure.json`.

The [legacy collector supplement](legacy-collector-supplement/manifest.json)
retains the old collector's original `generate_cases.py` dependency. Its bytes
match the generator digest recorded in the original native run. The original
collector is already a member of the unchanged older archive; it is not
silently replaced by the updated collector. The supplement supplies the missing
dependency without rewriting that archive or its original observations.

## Reproduce

From the repository root, select a new evidence directory and a verified V01
cache. `NEW_EVIDENCE` and `VERIFIED_CACHE` below are caller-selected paths.
Create the chosen binary output directory before compiling.

```sh
timeout --signal=TERM --kill-after=5s 20s python3 -B tools/regex-oracle/resource_cases.py --no-except-flow-only --output NEW_EVIDENCE/cases.tsv
timeout --signal=TERM --kill-after=10s 120s c++ -std=c++17 -O2 -g0 -Wall -Wextra -Werror -IVERIFIED_CACHE/deps/boost_1_89_0 tools/regex-oracle/oracle.cpp -pthread -o target/research/byte-reference
timeout --signal=TERM --kill-after=5s 45s python3 -B tools/regex-oracle/run.py --program target/research/byte-reference --role reference --cases NEW_EVIDENCE/cases.tsv --output NEW_EVIDENCE/after --batch-size 32 --timeout 5 --source tools/regex-oracle/oracle.cpp
timeout --signal=TERM --kill-after=5s 20s python3 -B tools/regex-oracle/verify_resource_errors.py --no-except-flow-only --cases NEW_EVIDENCE/cases.tsv --before ORIGINAL_FLOW_EVIDENCE/before/results.tsv --after NEW_EVIDENCE/after/results.tsv --output NEW_EVIDENCE/flow-verification.json
timeout --signal=TERM --kill-after=5s 20s python3 -B tools/regex-oracle/compare.py --cases NEW_EVIDENCE/cases.tsv --reference NEW_EVIDENCE/after/results.tsv --candidate NEW_EVIDENCE/after/results.tsv --output NEW_EVIDENCE/non-pass
timeout --signal=TERM --kill-after=5s 20s python3 -B -m unittest discover -s tools/regex-oracle -p test_reference_failures.py -v
timeout --signal=TERM --kill-after=5s 20s python3 -B -m unittest discover -s tools/regex-oracle -p test_comparison.py -v
timeout --signal=TERM --kill-after=5s 30s python3 -B tools/icu-probe/primary/archive_evidence.py --verify docs/research/assets/regex-engine/v03-no-except-flow-20261018T015213Z/retained
```

The comparison's exit 1 is required for the six reference resource observations.
Run it as a separate command and retain its nonzero status. Extract
`ORIGINAL_FLOW_EVIDENCE/before/results.tsv` from this archive's
`run/before/results.tsv`, or re-execute the earlier retained binary with the same
inputs in a new directory. Exact commands used for all executions, including
the base/stack/normal regressions, are retained in their process records.

## Remaining scope

The collector remains a process/protocol diagnostic tool. V03 still needs its
complete immutable run contracts, independent artifact attribution, named
queries, observations retained before iteration errors, and integrated byte and
collation comparison. No Rust adapter, root engine, ICU data, resource budget,
platform acceptance or performance result was changed by this repair.
